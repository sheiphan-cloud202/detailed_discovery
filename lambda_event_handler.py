import sys
sys.path.insert(0, "/mnt/efs/dynamic_usecase/myenv/lib/python3.11/site-packages")

import os
import json
import base64
from pathlib import Path
import boto3
from datetime import datetime
import uuid

from src.report_labs_executive import Cloud202ExecutiveReportGenerator


def handler(event, context):
    """
    AWS Lambda handler that accepts the assessment JSON as the event payload,
    generates the executive PDF report, uploads it to S3, and returns metadata
    plus S3 details and a presigned URL.

    Expected event: a dict matching the assessment JSON schema (e.g., contains
    a top-level "responses" object, etc.).
    Also expects a "job_id" field for tracking job status.
    """
    # Configure S3 settings from environment variables
    AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
    BUCKET_NAME = os.getenv("REPORT_BUCKET", "qubitz-detailed-discovery-bucket")
    S3_PREFIX = os.getenv("REPORT_PREFIX", "reports/")
    SSE_MODE = os.getenv("SSE_MODE", "AES256")  # "AES256" or "aws:kms"
    SSE_KMS_KEY_ID = os.getenv("SSE_KMS_KEY_ID")  # required if SSE_MODE="aws:kms"
    PRESIGN_EXPIRES_SECS = int(os.getenv("PRESIGN_TTL_SEC", "3600"))
    # Retained for backward compatibility; not required in multi-report mode
    # Keep environment reads but suppress unused warnings by referencing in local config dict
    BEDROCK_REGION = os.getenv("BEDROCK_REGION", AWS_REGION)
    MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-7-sonnet-20250219-v1:0")
    _legacy_cfg = {"bedrock_region": BEDROCK_REGION, "model_id": MODEL_ID}
    DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "qubitz-report-jobs")
    
    # Extract job_id from event (provided by coordinator Lambda)
    job_id = event.pop("job_id", str(uuid.uuid4()))
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    # Update job status to PROCESSING
    try:
        table.put_item(Item={
            'job_id': job_id,
            'status': 'PROCESSING',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"Warning: Failed to update DynamoDB status: {str(e)}")

    # Ensure we are operating in the writable /tmp directory for Lambda
    try:
        os.makedirs("/tmp", exist_ok=True)
        os.chdir("/tmp")
    except Exception:
        # If /tmp isn't available for some reason, continue in current dir
        pass

    # Persist the incoming event JSON to a temporary file
    input_json_path = "/tmp/event_payload.json"
    with open(input_json_path, "w", encoding="utf-8") as f:
        json.dump(event, f, ensure_ascii=False)

    # Generate all three reports
    combined_results = Cloud202ExecutiveReportGenerator.generate_all_reports(input_json_path, force_compliance=True)

    # Helper to upload and presign - organizes by job_id
    def upload_and_presign(local_path: str, company: str, report_type: str) -> dict:
        if not local_path or not Path(local_path).exists():
            return {}
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in (company or 'customer').lower())
        
        # Organize by company/job_id/report_type for better organization
        # This groups all reports from the same job together
        key = f"{S3_PREFIX}{safe_company_name}/{job_id}/{report_type}_report_{timestamp}.pdf"
        
        encryption_params = {'ServerSideEncryption': SSE_MODE}
        if SSE_MODE == 'aws:kms' and SSE_KMS_KEY_ID:
            encryption_params['SSEKMSKeyId'] = SSE_KMS_KEY_ID
        with open(local_path, 'rb') as f:
            s3_client.upload_fileobj(f, BUCKET_NAME, key, ExtraArgs=encryption_params)
        url = s3_client.generate_presigned_url('get_object', Params={'Bucket': BUCKET_NAME, 'Key': key}, ExpiresIn=PRESIGN_EXPIRES_SECS)
        return {"bucket": BUCKET_NAME, "key": key, "presigned_url": url, "expires_in_seconds": PRESIGN_EXPIRES_SECS}

    errors = []
    s3_reports = []

    # Upload each available report with job_id-based organization
    for rtype in ["executive", "technical", "compliance"]:
        res = combined_results.get(rtype) or {}
        try:
            upload_info = upload_and_presign(res.get('pdf_path'), res.get('company_name'), rtype) if res else {}
            if upload_info:
                s3_reports.append({"type": rtype, **upload_info})
            else:
                errors.append({"type": rtype, "error": "missing_or_invalid_pdf"})
        except Exception as e:
            errors.append({"type": rtype, "error": str(e)})

    # Legacy top-level s3 points to executive if present
    legacy_s3 = next((item for item in s3_reports if item.get('type') == 'executive'), None)

    # Update DynamoDB status
    status_value = 'COMPLETED' if legacy_s3 else ('PARTIAL' if s3_reports else 'FAILED')
    try:
        # Store native map/list types in DynamoDB instead of JSON strings
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, updated_at = :updated_at, #metadata = :metadata, s3_reports = :s3r',
            ExpressionAttributeNames={'#status': 'status', '#metadata': 'metadata'},
            ExpressionAttributeValues={
                ':status': status_value,
                ':updated_at': datetime.utcnow().isoformat(),
                ':metadata': combined_results,
                ':s3r': s3_reports,
            }
        )
    except Exception as db_error:
        print(f"Warning: Failed to update DynamoDB with combined results: {str(db_error)}")

    # If none uploaded, return failure with inline base64 of executive if available
    if not s3_reports:
        exec_res = combined_results.get('executive') or {}
        pdf_path = exec_res.get('pdf_path')
        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, 'rb') as f:
                pdf_b64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            pdf_b64 = None
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "No reports could be uploaded",
                "job_id": job_id,
                "metadata": combined_results,
                "errors": errors,
                **({"pdf_base64": pdf_b64} if pdf_b64 else {}),
            }),
        }

    # Extract company name for folder path info
    company_name = None
    for res in combined_results.values():
        if res and isinstance(res, dict) and res.get('company_name'):
            company_name = res['company_name']
            break
    safe_company_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in (company_name or 'customer').lower())
    s3_folder_path = f"{S3_PREFIX}{safe_company_name}/{job_id}/"
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": "Reports generated and uploaded successfully",
            "job_id": job_id,
            "s3_folder": {
                "bucket": BUCKET_NAME,
                "prefix": s3_folder_path,
                "description": f"All reports for job {job_id} are organized in: s3://{BUCKET_NAME}/{s3_folder_path}"
            },
            "metadata": combined_results,
            "s3": {k: legacy_s3[k] for k in ["bucket", "key", "presigned_url", "expires_in_seconds"]} if legacy_s3 else None,
            "s3_reports": s3_reports,
            "errors": errors
        }),
    }


