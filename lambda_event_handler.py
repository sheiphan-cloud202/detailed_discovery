import sys
sys.path.insert(0, "/mnt/efs/dynamic_usecase/myenv/lib/python3.11/site-packages")

import os
import json
import base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import boto3
from datetime import datetime
import uuid
from decimal import Decimal

# Ensure project root and src are importable
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def decimal_to_number(obj):
    """Convert DynamoDB Decimal objects to int/float for JSON serialization"""
    if isinstance(obj, list):
        return [decimal_to_number(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_number(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


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

    # Import runner lazily after sys.path setup to satisfy linter and path requirements
    from src.run_parallel import run_executive, run_technical, run_compliance

    # Generate all three reports in parallel using the shared runner
    def _normalize_result(res) -> dict:
        if not res or res.status != "success":
            return {}
        base = res.extra if isinstance(res.extra, dict) else {}
        pdf_path = base.get('pdf_path') or base.get('output_path') or res.output_path
        if pdf_path:
            base['pdf_path'] = pdf_path
        # Preserve company_name and other metadata from the report result
        if hasattr(res, 'extra') and isinstance(res.extra, dict):
            for key in ['company_name', 'industry', 'timestamp']:
                if key in res.extra:
                    base[key] = res.extra[key]
        return base

    futures = {}
    combined_results = {"executive": {}, "technical": {}, "compliance": {}}
    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures["executive"] = ex.submit(run_executive, input_json_path)
            futures["technical"] = ex.submit(run_technical, input_json_path)
            futures["compliance"] = ex.submit(lambda p: run_compliance(p, force=True), input_json_path)

            for name, fut in futures.items():
                try:
                    res = fut.result()
                    combined_results[name] = _normalize_result(res)
                except Exception:
                    # Preserve graceful degradation - leave empty dict for failures
                    combined_results[name] = {}
    except Exception:
        # If runner setup failed entirely, keep structure and proceed with empty results
        pass

    # Helper to extract company name consistently from all report types
    def extract_company_name(res: dict) -> str:
        """Extract company name from report result, handling different return structures"""
        if not res or not isinstance(res, dict):
            return 'customer'
        
        # Check direct company_name (compliance reports)
        if res.get('company_name'):
            return res['company_name']
        
        # Check nested in meta (executive and technical reports)
        meta = res.get('meta', {})
        if isinstance(meta, dict) and meta.get('company_name'):
            return meta['company_name']
        
        return 'customer'

    # Helper to upload and presign - organizes by job_id
    def upload_and_presign(local_path: str, company: str, report_type: str) -> dict:
        if not local_path:
            return {}
        # Resolve relative paths against current working directory (Lambda uses /tmp)
        p = Path(local_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        if not p.exists():
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
        with open(p, 'rb') as f:
            s3_client.upload_fileobj(f, BUCKET_NAME, key, ExtraArgs=encryption_params)
        url = s3_client.generate_presigned_url('get_object', Params={'Bucket': BUCKET_NAME, 'Key': key}, ExpiresIn=PRESIGN_EXPIRES_SECS)
        return {"bucket": BUCKET_NAME, "key": key, "presigned_url": url, "expires_in_seconds": PRESIGN_EXPIRES_SECS}

    errors = []
    s3_reports = []

    # Upload each available report with job_id-based organization
    for rtype in ["executive", "technical", "compliance"]:
        res = combined_results.get(rtype) or {}
        try:
            pdf_candidate = res.get('pdf_path') or res.get('output_path')
            company_name = extract_company_name(res)
            upload_info = upload_and_presign(pdf_candidate, company_name, rtype) if res else {}
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
            "body": json.dumps(decimal_to_number({
                "message": "No reports could be uploaded",
                "job_id": job_id,
                "metadata": combined_results,
                "errors": errors,
                **({"pdf_base64": pdf_b64} if pdf_b64 else {}),
            })),
        }

    # Extract company name for folder path info using consistent extraction
    company_name = None
    for res in combined_results.values():
        if res and isinstance(res, dict):
            extracted_name = extract_company_name(res)
            if extracted_name != 'customer':
                company_name = extracted_name
                break
    safe_company_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in (company_name or 'customer').lower())
    s3_folder_path = f"{S3_PREFIX}{safe_company_name}/{job_id}/"
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(decimal_to_number({
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
        })),
    }


