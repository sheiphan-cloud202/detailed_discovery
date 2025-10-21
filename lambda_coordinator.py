import os
import json
import uuid
import boto3
from datetime import datetime
from decimal import Decimal


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


def handler(event, context):
    """
    Coordinator Lambda with Function URL support.
    
    POST /: Submit a new report generation job
        - Invokes worker Lambda asynchronously
        - Returns job_id immediately
    
    GET /?job_id=xxx: Check job status
        - Queries DynamoDB for job status
        - Returns presigned URL when job is COMPLETED
    """
    # Configure AWS settings
    AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
    WORKER_LAMBDA_ARN = os.getenv("WORKER_LAMBDA_ARN", "arn:aws:lambda:eu-west-2:781364298443:function:qubitz-detailed-discovery")
    DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "qubitz-report-jobs")
    PRESIGN_EXPIRES_SECS = int(os.getenv("PRESIGN_TTL_SEC", "3600"))
    
    # Initialize clients
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    
    # Parse the incoming request
    http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    query_params = event.get('queryStringParameters') or {}
    
    # Handle GET request - Status check
    if http_method == 'GET':
        job_id = query_params.get('job_id')
        
        if not job_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(decimal_to_number({
                    "error": "Missing job_id parameter",
                    "usage": "GET /?job_id=xxx"
                }))
            }
        
        try:
            # Query DynamoDB for job status
            response = table.get_item(Key={'job_id': job_id})
            
            if 'Item' not in response:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(decimal_to_number({
                        "error": "Job not found",
                        "job_id": job_id
                    }))
                }
            
            job = response['Item']
            status = job.get('status')
            
            # Base response
            response_body = {
                "job_id": job_id,
                "status": status,
                "created_at": job.get('created_at'),
                "updated_at": job.get('updated_at')
            }
            
            if status == 'COMPLETED' or status == 'PARTIAL':
                # Job is complete - generate fresh presigned URLs for all reports
                s3_reports = job.get('s3_reports', [])
                
                # Regenerate fresh presigned URLs for all reports
                updated_reports = []
                for report in s3_reports:
                    if isinstance(report, dict) and report.get('bucket') and report.get('key'):
                        try:
                            fresh_url = s3_client.generate_presigned_url(
                                'get_object',
                                Params={'Bucket': report['bucket'], 'Key': report['key']},
                                ExpiresIn=PRESIGN_EXPIRES_SECS
                            )
                            updated_reports.append({
                                "type": report.get('type', 'unknown'),
                                "bucket": report['bucket'],
                                "key": report['key'],
                                "presigned_url": fresh_url,
                                "expires_in_seconds": PRESIGN_EXPIRES_SECS
                            })
                        except Exception as e:
                            print(f"Failed to generate presigned URL for {report.get('type')}: {e}")
                
                # Include metadata if present
                metadata = job.get('metadata')
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except Exception:
                        metadata = {}
                elif not isinstance(metadata, dict):
                    metadata = {}
                
                # Legacy s3 field for backward compatibility (executive report)
                legacy_s3 = next((r for r in updated_reports if r.get('type') == 'executive'), None)
                
                # Extract company name and job folder path using consistent extraction
                company_name = None
                for res in (metadata.values() if metadata else []):
                    if res and isinstance(res, dict):
                        extracted_name = extract_company_name(res)
                        if extracted_name != 'customer':
                            company_name = extracted_name
                            break
                
                safe_company = ''.join(c if c.isalnum() or c in '-_' else '_' for c in (company_name or 'customer').lower())
                s3_folder_path = f"reports/{safe_company}/{job_id}/"
                
                response_body.update({
                    "s3_reports": updated_reports,
                    "s3_folder": {
                        "bucket": updated_reports[0]['bucket'] if updated_reports else None,
                        "prefix": s3_folder_path,
                        "description": f"All reports for this job are in: s3://{updated_reports[0]['bucket'] if updated_reports else 'bucket'}/{s3_folder_path}"
                    },
                    "metadata": metadata,
                    "reports_count": len(updated_reports)
                })
                
                # Include legacy s3 field for backward compatibility
                if legacy_s3:
                    response_body['s3'] = {
                        "bucket": legacy_s3['bucket'],
                        "key": legacy_s3['key'],
                        "presigned_url": legacy_s3['presigned_url'],
                        "expires_in_seconds": legacy_s3['expires_in_seconds']
                    }
                
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(decimal_to_number(response_body))
                }
            
            elif status == 'FAILED':
                response_body['error_message'] = job.get('error_message', 'Unknown error')
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(decimal_to_number(response_body))
                }
            
            elif status in ['PENDING', 'PROCESSING']:
                response_body['message'] = 'Job is still processing. Please check again in a few moments.'
                return {
                    "statusCode": 202,  # HTTP 202 Accepted
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(decimal_to_number(response_body))
                }
            
            else:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(decimal_to_number(response_body))
                }
        
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(decimal_to_number({
                    "error": f"Failed to check job status: {str(e)}",
                    "job_id": job_id
                }))
            }
    
    # Handle POST request - Job submission
    elif http_method == 'POST':
        try:
            # Parse request body
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event.get('body', {})
            
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Add job_id to the payload
            payload = body.copy()
            payload['job_id'] = job_id
            
            # Create initial job record in DynamoDB
            table.put_item(Item={
                'job_id': job_id,
                'status': 'PENDING',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
            
            # Invoke worker Lambda asynchronously
            lambda_client.invoke(
                FunctionName=WORKER_LAMBDA_ARN,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(payload)
            )
            
            return {
                "statusCode": 202,  # HTTP 202 Accepted
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(decimal_to_number({
                    "message": "Job submitted successfully",
                    "job_id": job_id,
                    "status": "PENDING",
                    "check_status_url": f"?job_id={job_id}",
                    "estimated_completion_time": "~3 minutes"
                }))
            }
        
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(decimal_to_number({
                    "error": f"Failed to submit job: {str(e)}"
                }))
            }
    
    # Handle unsupported methods
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(decimal_to_number({
                "error": f"Method {http_method} not allowed",
                "allowed_methods": ["GET", "POST"]
            }))
        }
