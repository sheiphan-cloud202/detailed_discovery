# API Documentation - Multi-Report Generation Service

## 🔗 Base URL

```
https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/
```

---

## 📋 Overview

This API generates **three comprehensive PDF reports** from assessment data:
1. **Executive Report** - High-level strategic overview
2. **Technical Report** - Detailed technical implementation guide
3. **Compliance/Security Report** - Security and compliance analysis

All reports are:
- Generated asynchronously (no timeout!)
- Organized by company and job_id in S3
- Available via presigned URLs (1 hour validity)

---

## 🚀 API Endpoints

### 1. Submit Report Generation Job

**Endpoint:** `POST /`

**Description:** Submit assessment data to generate all three reports asynchronously.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:** JSON assessment data (see example below)

**Response:** Immediate job submission confirmation with `job_id`

---

#### cURL Example

```bash
curl -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d '{
    "customer_info": {
      "company_name": "GlobalTech Financial Services",
      "industry": "Financial Technology",
      "company_size": "Enterprise (1000+ employees)",
      "headquarters": "London, UK"
    },
    "use_case_discovery": {
      "business_problem": "Manual document processing",
      "primary_goal": "Automate document analysis",
      "urgency": "High"
    }
  }'
```

Or use a file:

```bash
curl -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d @test_json_comprehensive.json
```

---

#### Postman Configuration

**Method:** POST

**URL:** 
```
https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/
```

**Headers:**
| Key | Value |
|-----|-------|
| Content-Type | application/json |

**Body:** (Select "raw" and "JSON")
```json
{
  "customer_info": {
    "company_name": "GlobalTech Financial Services",
    "industry": "Financial Technology",
    "company_size": "Enterprise (1000+ employees)",
    "headquarters": "London, UK",
    "primary_contact": {
      "name": "Sarah Johnson",
      "title": "Chief Technology Officer",
      "email": "sarah.johnson@globaltech.com",
      "phone": "+44 20 1234 5678"
    }
  },
  "use_case_discovery": {
    "business_problem": "Manual financial document processing causing delays",
    "current_state": "Manual review of 10,000+ documents monthly",
    "primary_goal": "Automate document analysis and extraction",
    "urgency": "High"
  },
  "data_readiness": {
    "data_volume": "1TB+ financial documents",
    "data_quality": "High quality, structured"
  },
  "compliance_integration": {
    "regulatory_frameworks": ["GDPR", "PCI-DSS", "FCA"],
    "data_residency": "EU only"
  }
}
```

---

#### Success Response (202 Accepted)

```json
{
  "message": "Job submitted successfully",
  "job_id": "c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "status": "PENDING",
  "check_status_url": "?job_id=c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "estimated_completion_time": "~3 minutes"
}
```

**Status Code:** `202 Accepted`

**Important:** Save the `job_id` to check status later!

---

#### Error Response (500 Internal Server Error)

```json
{
  "error": "Failed to submit job: Invalid JSON payload"
}
```

**Status Code:** `500 Internal Server Error`

---

### 2. Check Job Status

**Endpoint:** `GET /?job_id={job_id}`

**Description:** Check the status of a submitted job and retrieve download URLs when complete.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| job_id | Yes | The job ID returned from POST request |

---

#### cURL Example

```bash
# Basic status check
curl 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=c354c80a-3dfe-4a31-bc5c-2c6bf30eb649'

# With pretty JSON output
curl 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=c354c80a-3dfe-4a31-bc5c-2c6bf30eb649' | python3 -m json.tool
```

---

#### Postman Configuration

**Method:** GET

**URL:**
```
https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/
```

**Params:**
| Key | Value | Description |
|-----|-------|-------------|
| job_id | c354c80a-3dfe-4a31-bc5c-2c6bf30eb649 | Your job ID |

**No Headers or Body Required**

---

#### Response - Status: PENDING

```json
{
  "job_id": "c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "status": "PENDING",
  "created_at": "2025-10-15T10:30:00.123456",
  "updated_at": "2025-10-15T10:30:00.123456",
  "message": "Job is still processing. Please check again in a few moments."
}
```

**Status Code:** `202 Accepted`

---

#### Response - Status: PROCESSING

```json
{
  "job_id": "c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "status": "PROCESSING",
  "created_at": "2025-10-15T10:30:00.123456",
  "updated_at": "2025-10-15T10:31:30.654321",
  "message": "Job is still processing. Please check again in a few moments."
}
```

**Status Code:** `202 Accepted`

---

#### Response - Status: COMPLETED (All 3 Reports)

```json
{
  "job_id": "c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "status": "COMPLETED",
  "created_at": "2025-10-15T10:30:00.123456",
  "updated_at": "2025-10-15T10:33:45.789012",
  "s3_reports": [
    {
      "type": "executive",
      "bucket": "qubitz-detailed-discovery-bucket",
      "key": "reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/executive_report_20251015_103345.pdf",
      "presigned_url": "https://qubitz-detailed-discovery-bucket.s3.amazonaws.com/reports/...",
      "expires_in_seconds": 3600
    },
    {
      "type": "technical",
      "bucket": "qubitz-detailed-discovery-bucket",
      "key": "reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/technical_report_20251015_103345.pdf",
      "presigned_url": "https://qubitz-detailed-discovery-bucket.s3.amazonaws.com/reports/...",
      "expires_in_seconds": 3600
    },
    {
      "type": "compliance",
      "bucket": "qubitz-detailed-discovery-bucket",
      "key": "reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/compliance_report_20251015_103345.pdf",
      "presigned_url": "https://qubitz-detailed-discovery-bucket.s3.amazonaws.com/reports/...",
      "expires_in_seconds": 3600
    }
  ],
  "s3_folder": {
    "bucket": "qubitz-detailed-discovery-bucket",
    "prefix": "reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/",
    "description": "All reports for this job are in: s3://qubitz-detailed-discovery-bucket/reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/"
  },
  "s3": {
    "bucket": "qubitz-detailed-discovery-bucket",
    "key": "reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/executive_report_20251015_103345.pdf",
    "presigned_url": "https://qubitz-detailed-discovery-bucket.s3.amazonaws.com/reports/...",
    "expires_in_seconds": 3600
  },
  "metadata": {
    "executive": {
      "pdf_path": "/tmp/reports/RAPID_Executive_Report_globaltech_financial_services_20251015_103345.pdf",
      "company_name": "GlobalTech Financial Services",
      "industry": "Financial Technology",
      "timestamp": "20251015_103345"
    },
    "technical": {
      "pdf_path": "/tmp/reports/Technical_Implementation_Report_globaltech_financial_services_20251015_103345.pdf",
      "company_name": "GlobalTech Financial Services",
      "timestamp": "20251015_103345"
    },
    "compliance": {
      "pdf_path": "/tmp/reports/Compliance_Security_Report_globaltech_financial_services_20251015_103345.pdf",
      "company_name": "GlobalTech Financial Services",
      "timestamp": "20251015_103345"
    }
  },
  "reports_count": 3
}
```

**Status Code:** `200 OK`

**Note:** The `s3` field contains the executive report for backward compatibility.

---

#### Response - Status: PARTIAL (Some Reports Failed)

```json
{
  "job_id": "c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "status": "PARTIAL",
  "created_at": "2025-10-15T10:30:00.123456",
  "updated_at": "2025-10-15T10:33:45.789012",
  "s3_reports": [
    {
      "type": "executive",
      "bucket": "qubitz-detailed-discovery-bucket",
      "key": "reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/executive_report_20251015_103345.pdf",
      "presigned_url": "https://...",
      "expires_in_seconds": 3600
    }
  ],
  "reports_count": 1,
  "metadata": {...},
  "s3_folder": {...}
}
```

**Status Code:** `200 OK`

---

#### Response - Status: FAILED

```json
{
  "job_id": "c354c80a-3dfe-4a31-bc5c-2c6bf30eb649",
  "status": "FAILED",
  "created_at": "2025-10-15T10:30:00.123456",
  "updated_at": "2025-10-15T10:30:45.789012",
  "error_message": "Failed to generate reports: Invalid assessment data format"
}
```

**Status Code:** `200 OK`

---

#### Response - Job Not Found

```json
{
  "error": "Job not found",
  "job_id": "invalid-job-id"
}
```

**Status Code:** `404 Not Found`

---

#### Response - Missing job_id Parameter

```json
{
  "error": "Missing job_id parameter",
  "usage": "GET /?job_id=xxx"
}
```

**Status Code:** `400 Bad Request`

---

## 📥 Downloading Reports

### Using cURL

```bash
# Download executive report
curl -o executive_report.pdf 'PRESIGNED_URL_HERE'

# Download all three reports
curl -o executive.pdf 'EXECUTIVE_PRESIGNED_URL'
curl -o technical.pdf 'TECHNICAL_PRESIGNED_URL'
curl -o compliance.pdf 'COMPLIANCE_PRESIGNED_URL'
```

### Using Browser

Simply paste the `presigned_url` into your browser to download.

### Presigned URL Expiration

- **Default expiration:** 1 hour (3600 seconds)
- **Renewal:** Call the GET status endpoint again to get fresh URLs
- **No download limits** within the expiration window

---

## 🔄 Complete Workflow Examples

### Example 1: Basic Workflow

```bash
# 1. Submit job
RESPONSE=$(curl -s -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d @test_json_comprehensive.json)

# 2. Extract job_id
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "Job ID: $JOB_ID"

# 3. Wait for completion (or poll every 10 seconds)
sleep 180

# 4. Check status and get download URLs
curl "https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=$JOB_ID" | python3 -m json.tool
```

---

### Example 2: Poll Until Complete (Bash)

```bash
#!/bin/bash

# Submit job
RESPONSE=$(curl -s -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d @test_json_comprehensive.json)

JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "Submitted job: $JOB_ID"

# Poll until complete
while true; do
  STATUS_RESPONSE=$(curl -s "https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=$JOB_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
  
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "COMPLETED" ] || [ "$STATUS" = "PARTIAL" ]; then
    echo "Job completed!"
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "Job failed!"
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    exit 1
  fi
  
  sleep 10
done
```

---

### Example 3: Download All Reports (Bash)

```bash
#!/bin/bash

JOB_ID="your-job-id-here"

# Get status with download URLs
RESPONSE=$(curl -s "https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=$JOB_ID")

# Extract and download each report
echo "$RESPONSE" | python3 << 'EOF'
import sys, json
data = json.load(sys.stdin)
for report in data.get('s3_reports', []):
    print(f"curl -o {report['type']}_report.pdf '{report['presigned_url']}'")
EOF
```

---

### Example 4: Python Client

```python
import requests
import time
import json

BASE_URL = "https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/"

# 1. Submit job
with open('test_json_comprehensive.json') as f:
    assessment_data = json.load(f)

response = requests.post(BASE_URL, json=assessment_data)
job_data = response.json()
job_id = job_data['job_id']
print(f"Job submitted: {job_id}")

# 2. Poll for completion
while True:
    response = requests.get(BASE_URL, params={'job_id': job_id})
    status_data = response.json()
    status = status_data['status']
    
    print(f"Status: {status}")
    
    if status in ['COMPLETED', 'PARTIAL']:
        print("Job completed!")
        print(json.dumps(status_data, indent=2))
        
        # 3. Download reports
        for report in status_data.get('s3_reports', []):
            report_type = report['type']
            url = report['presigned_url']
            
            print(f"Downloading {report_type} report...")
            pdf_response = requests.get(url)
            
            with open(f'{report_type}_report.pdf', 'wb') as f:
                f.write(pdf_response.content)
            print(f"✓ Saved {report_type}_report.pdf")
        
        break
    elif status == 'FAILED':
        print("Job failed!")
        print(json.dumps(status_data, indent=2))
        break
    
    time.sleep(10)
```

---

### Example 5: JavaScript/Node.js Client

```javascript
const axios = require('axios');
const fs = require('fs');

const BASE_URL = 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/';

async function generateReports() {
  // 1. Submit job
  const assessmentData = JSON.parse(fs.readFileSync('test_json_comprehensive.json'));
  const submitResponse = await axios.post(BASE_URL, assessmentData);
  const jobId = submitResponse.data.job_id;
  console.log(`Job submitted: ${jobId}`);
  
  // 2. Poll for completion
  while (true) {
    const statusResponse = await axios.get(BASE_URL, {
      params: { job_id: jobId }
    });
    const status = statusResponse.data.status;
    
    console.log(`Status: ${status}`);
    
    if (status === 'COMPLETED' || status === 'PARTIAL') {
      console.log('Job completed!');
      console.log(JSON.stringify(statusResponse.data, null, 2));
      
      // 3. Download reports
      for (const report of statusResponse.data.s3_reports || []) {
        console.log(`Downloading ${report.type} report...`);
        const pdfResponse = await axios.get(report.presigned_url, {
          responseType: 'arraybuffer'
        });
        
        fs.writeFileSync(`${report.type}_report.pdf`, pdfResponse.data);
        console.log(`✓ Saved ${report.type}_report.pdf`);
      }
      
      break;
    } else if (status === 'FAILED') {
      console.log('Job failed!');
      console.log(JSON.stringify(statusResponse.data, null, 2));
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 10000));
  }
}

generateReports().catch(console.error);
```

---

## 📊 S3 Organization Structure

Reports are organized in S3 as follows:

```
s3://qubitz-detailed-discovery-bucket/
└── reports/
    └── {company_name_sanitized}/
        └── {job_id}/
            ├── executive_report_{timestamp}.pdf
            ├── technical_report_{timestamp}.pdf
            └── compliance_report_{timestamp}.pdf
```

**Example:**
```
s3://qubitz-detailed-discovery-bucket/reports/globaltech_financial_services/c354c80a-3dfe-4a31-bc5c-2c6bf30eb649/
├── executive_report_20251015_103345.pdf
├── technical_report_20251015_103345.pdf
└── compliance_report_20251015_103345.pdf
```

---

## 🔐 Authentication & Security

### Current Setup (Development)
- **Auth Type:** NONE (public access)
- **CORS:** Enabled for all origins
- **Rate Limiting:** AWS Lambda default limits

### Production Recommendations

1. **Enable AWS IAM Authentication:**
```bash
aws lambda update-function-url-config \
  --function-name qubitz-discovery-coordinator \
  --auth-type AWS_IAM \
  --region eu-west-2
```

2. **Use AWS Signature V4** for authenticated requests:
```bash
curl -X POST 'https://...' \
  --aws-sigv4 'aws:amz:eu-west-2:lambda' \
  --user $AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY \
  -H "Content-Type: application/json" \
  -d @data.json
```

3. **Add API Key Validation** in coordinator Lambda

4. **Use AWS WAF** for rate limiting and DDoS protection

---

## ⚙️ Environment Variables

### Worker Lambda (qubitz-detailed-discovery)
| Variable | Value | Description |
|----------|-------|-------------|
| DYNAMODB_TABLE | qubitz-report-jobs | DynamoDB table for job tracking |
| REPORT_BUCKET | qubitz-detailed-discovery-bucket | S3 bucket for reports |
| REPORT_PREFIX | reports/ | S3 key prefix |
| SSE_MODE | AES256 | S3 encryption mode |
| PRESIGN_TTL_SEC | 3600 | Presigned URL expiry (seconds) |
| BEDROCK_REGION | eu-west-2 | AWS Bedrock region |
| BEDROCK_MODEL_ID | anthropic.claude-3-7-sonnet-20250219-v1:0 | Claude model ID |

### Coordinator Lambda (qubitz-discovery-coordinator)
| Variable | Value | Description |
|----------|-------|-------------|
| WORKER_LAMBDA_ARN | arn:aws:lambda:eu-west-2:781364298443:function:qubitz-detailed-discovery | Worker Lambda ARN |
| DYNAMODB_TABLE | qubitz-report-jobs | DynamoDB table |
| PRESIGN_TTL_SEC | 3600 | Presigned URL expiry |

---

## 📈 Performance & Limits

### Timing
- **Job submission:** <200ms
- **Report generation:** ~3-4 minutes
- **Status check:** <150ms

### Limits
- **Max request size:** 6 MB (Lambda limit)
- **Max execution time:** 15 minutes (Lambda limit)
- **Concurrent executions:** 1000 (AWS account default)
- **DynamoDB throughput:** On-demand (auto-scaling)

### Optimization Tips
1. Poll status every 10-15 seconds (not faster)
2. Cache job_id on client side
3. Reuse presigned URLs within expiry window
4. Batch multiple assessment submissions if needed

---

## 🐛 Error Handling

### Common Errors

| Error | Status Code | Solution |
|-------|-------------|----------|
| Missing job_id parameter | 400 | Include `?job_id=xxx` in GET request |
| Job not found | 404 | Check if job_id is correct |
| Invalid JSON payload | 500 | Validate JSON structure |
| S3 upload failed | 500 | Check S3 bucket permissions |
| Lambda timeout | 504 | Job runs async, won't timeout |

### Retry Strategy

```python
import time
import requests

def submit_with_retry(data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(BASE_URL, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

---

## 📞 Support & Troubleshooting

### Check Lambda Logs

```bash
# Worker Lambda logs
aws logs tail /aws/lambda/qubitz-detailed-discovery --follow --region eu-west-2

# Coordinator Lambda logs
aws logs tail /aws/lambda/qubitz-discovery-coordinator --follow --region eu-west-2
```

### Check DynamoDB Record

```bash
aws dynamodb get-item \
  --table-name qubitz-report-jobs \
  --key '{"job_id":{"S":"YOUR_JOB_ID"}}' \
  --region eu-west-2
```

### Verify S3 Upload

```bash
aws s3 ls s3://qubitz-detailed-discovery-bucket/reports/ --recursive --region eu-west-2
```

---

## 🎯 Quick Reference

### Submit Job
```bash
curl -X POST 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/' \
  -H "Content-Type: application/json" \
  -d @your_data.json
```

### Check Status
```bash
curl 'https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/?job_id=YOUR_JOB_ID'
```

### Download Report
```bash
curl -o report.pdf 'PRESIGNED_URL'
```

---

**Last Updated:** 2025-10-15  
**API Version:** 2.0 (Multi-Report Support)  
**Region:** eu-west-2

