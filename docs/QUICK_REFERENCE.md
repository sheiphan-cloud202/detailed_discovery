# Quick Reference - Async Report Generation

## 🔗 Function URL
```
https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/
```

## 📤 Submit Job (POST)
```bash
curl -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d @your_assessment.json
```

## 📥 Check Status (GET)
```bash
curl 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=YOUR_JOB_ID'
```

## 🧪 Run Test
```bash
./test_async_workflow.sh
```

## 📊 Status Values
- `PENDING` - Job submitted, waiting to start
- `PROCESSING` - Report being generated
- `COMPLETED` - Success! Download URL available
- `FAILED` - Error occurred (check error_message)

## ⏱️ Expected Timeline
- Job submission: <1 second
- Report generation: ~3 minutes
- Total: ~3-4 minutes

## 📋 DynamoDB Table
```
Table: qubitz-report-jobs
Region: eu-west-2
```

## 🔍 Check Logs
```bash
# Worker Lambda
aws logs tail /aws/lambda/qubitz-detailed-discovery --follow --region eu-west-2

# Coordinator Lambda
aws logs tail /aws/lambda/qubitz-discovery-coordinator --follow --region eu-west-2
```

## 🗄️ Check DynamoDB
```bash
aws dynamodb get-item \
  --table-name qubitz-report-jobs \
  --key '{"job_id":{"S":"YOUR_JOB_ID"}}' \
  --region eu-west-2
```

## 🔄 Redeploy Worker Lambda
```bash
zip -r lambda_worker_update.zip lambda_event_handler.py report_labs_executive.py
aws lambda update-function-code \
  --function-name qubitz-detailed-discovery \
  --zip-file fileb://lambda_worker_update.zip \
  --region eu-west-2
```

## 🔄 Redeploy Coordinator Lambda
```bash
zip lambda_coordinator.zip lambda_coordinator.py
aws lambda update-function-code \
  --function-name qubitz-discovery-coordinator \
  --zip-file fileb://lambda_coordinator.zip \
  --region eu-west-2
```

## 🛠️ Lambda Functions
- **Worker**: `qubitz-detailed-discovery`
- **Coordinator**: `qubitz-discovery-coordinator`

## 📦 S3 Bucket
```
qubitz-detailed-discovery-bucket
Prefix: reports/
```

## ⚙️ Key Environment Variables

### Worker Lambda:
- `DYNAMODB_TABLE=qubitz-report-jobs`
- `REPORT_BUCKET=qubitz-detailed-discovery-bucket`
- `BEDROCK_MODEL_ID=anthropic.claude-3-7-sonnet-20250219-v1:0`

### Coordinator Lambda:
- `WORKER_LAMBDA_ARN=arn:aws:lambda:eu-west-2:781364298443:function:qubitz-detailed-discovery`
- `DYNAMODB_TABLE=qubitz-report-jobs`

