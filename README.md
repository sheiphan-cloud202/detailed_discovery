# Cloud202 Detailed Discovery Report Generator

A serverless AWS Lambda-based system that generates comprehensive AI assessment reports for businesses. The system produces three types of professional PDF reports: Executive Summary, Technical Implementation Deep-Dive, and Compliance & Security Assessment.

## 🚀 Features

- **Multi-Report Generation**: Creates Executive, Technical, and Compliance reports in parallel
- **Serverless Architecture**: AWS Lambda-based with Function URL for easy API access
- **Async Processing**: Submit jobs and check status via REST API
- **Professional PDFs**: High-quality reports with consistent branding and formatting
- **S3 Integration**: Automatic upload with presigned URLs for secure access
- **DynamoDB Tracking**: Job status tracking and metadata storage
- **AWS Bedrock AI**: Powered by Claude 3.7 Sonnet for intelligent content generation

## 📋 Report Types

### Executive Report
- Strategic overview and business impact analysis
- ROI projections and implementation roadmap
- Executive summary with key recommendations

### Technical Report  
- Deep technical implementation details
- Architecture recommendations and best practices
- Technical specifications and integration guidance

### Compliance Report
- Regulatory compliance analysis (HIPAA, SOX, PCI-DSS, GDPR)
- Data governance framework and security architecture
- 12-month compliance roadmap with cost estimates

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │    │   Coordinator    │    │   Worker        │
│                 │───▶│   Lambda         │───▶│   Lambda        │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   DynamoDB       │    │   S3 Bucket     │
                       │   (Job Status)   │    │   (PDF Reports) │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Submit a Report Job
```bash
curl -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d @your_assessment.json
```

### 2. Check Job Status
```bash
curl 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=YOUR_JOB_ID'
```

### 3. Download Reports
When status is `COMPLETED`, download URLs will be provided in the response.

## 📊 API Reference

### Submit Job (POST)
**Endpoint**: `https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/`

**Request Body**: JSON assessment data
```json
{
  "responses": {
    "company-name": "Your Company",
    "business-owner": "John Doe, CEO",
    "business-problems": "Description of challenges...",
    // ... other assessment fields
  }
}
```

**Response**:
```json
{
  "message": "Job submitted successfully",
  "job_id": "uuid-here",
  "status": "PENDING",
  "check_status_url": "?job_id=uuid-here",
  "estimated_completion_time": "~3 minutes"
}
```

### Check Status (GET)
**Endpoint**: `https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=YOUR_JOB_ID`

**Response** (Completed):
```json
{
  "job_id": "uuid-here",
  "status": "COMPLETED",
  "s3_reports": [
    {
      "type": "executive",
      "bucket": "qubitz-detailed-discovery-bucket",
      "key": "reports/company_name/job_id/executive_report_timestamp.pdf",
      "presigned_url": "https://...",
      "expires_in_seconds": 3600
    }
    // ... other reports
  ],
  "reports_count": 3
}
```

## 🔧 Configuration

### Environment Variables

**Worker Lambda**:
- `DYNAMODB_TABLE`: DynamoDB table for job tracking
- `REPORT_BUCKET`: S3 bucket for PDF storage
- `BEDROCK_MODEL_ID`: AWS Bedrock model identifier
- `AWS_REGION`: AWS region (default: eu-west-2)

**Coordinator Lambda**:
- `WORKER_LAMBDA_ARN`: ARN of the worker Lambda function
- `DYNAMODB_TABLE`: DynamoDB table for job tracking
- `PRESIGN_TTL_SEC`: Presigned URL expiration time

## 📁 Project Structure

```
detailed_discovery/
├── lambda_coordinator.py      # API Gateway Lambda (job submission/status)
├── lambda_event_handler.py    # Worker Lambda (report generation)
├── src/
│   ├── executive_report.py    # Executive report generator
│   ├── technical_report.py    # Technical report generator
│   ├── compliance_report.py   # Compliance report generator
│   ├── bedrock_config.py      # AWS Bedrock configuration
│   ├── report_styles.py       # PDF styling and formatting
│   └── run_parallel.py        # Parallel report execution
├── reports/                   # Generated PDF outputs
├── docs/                      # Documentation
└── requirements.txt           # Python dependencies
```

## 🧪 Testing

Run the test script to verify the system:
```bash
./test_async_workflow.sh
```

## 📈 Monitoring

### CloudWatch Logs
```bash
# Worker Lambda logs
aws logs tail /aws/lambda/qubitz-detailed-discovery --follow --region eu-west-2

# Coordinator Lambda logs  
aws logs tail /aws/lambda/qubitz-discovery-coordinator --follow --region eu-west-2
```

### DynamoDB Status
```bash
aws dynamodb get-item \
  --table-name qubitz-report-jobs \
  --key '{"job_id":{"S":"YOUR_JOB_ID"}}' \
  --region eu-west-2
```

## 🔄 Deployment

### Update Worker Lambda
```bash
zip -r lambda_worker_update.zip lambda_event_handler.py src/
aws lambda update-function-code \
  --function-name qubitz-detailed-discovery \
  --zip-file fileb://lambda_worker_update.zip \
  --region eu-west-2
```

### Update Coordinator Lambda
```bash
zip lambda_coordinator.zip lambda_coordinator.py
aws lambda update-function-code \
  --function-name qubitz-discovery-coordinator \
  --zip-file fileb://lambda_coordinator.zip \
  --region eu-west-2
```

## 📋 Dependencies

- **boto3**: AWS SDK for Python
- **reportlab**: PDF generation
- **PyMuPDF**: PDF processing
- **strands**: Additional utilities

## 🎯 Use Cases

- **AI Strategy Consulting**: Generate comprehensive AI assessment reports
- **Compliance Audits**: Create regulatory compliance documentation
- **Technical Architecture**: Produce detailed implementation guides
- **Executive Briefings**: Generate high-level strategic summaries

## 📞 Support

For issues or questions, check the logs and DynamoDB status first. The system provides detailed error messages and status tracking for troubleshooting.

## 🔒 Security

- All data is encrypted in transit and at rest
- S3 presigned URLs provide secure, time-limited access
- DynamoDB access is controlled via IAM policies
- AWS Bedrock provides enterprise-grade AI security

---

**Function URL**: `https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/`
