# S3 Report Organization Structure

## Overview
Reports are now organized by **job_id** to keep all reports from the same generation together.

## Folder Structure

```
s3://qubitz-detailed-discovery-bucket/
└── reports/
    └── {company_name}/
        └── {job_id}/
            ├── executive_report_{timestamp}.pdf
            ├── technical_report_{timestamp}.pdf
            └── compliance_report_{timestamp}.pdf
```

## Example

For a company called "GlobalTech Financial Services" with job_id `abc123-def456`:

```
s3://qubitz-detailed-discovery-bucket/
└── reports/
    └── globaltech_financial_services/
        └── abc123-def456/
            ├── executive_report_20251015_120345.pdf
            ├── technical_report_20251015_120347.pdf
            └── compliance_report_20251015_120349.pdf
```

## Benefits

1. **Easy Organization**: All reports for a single job are grouped together
2. **Easy Retrieval**: Use job_id to find all related reports
3. **Company Segregation**: Reports are still organized by company name
4. **Unique Identification**: Each job has its own unique folder
5. **Clean Structure**: No more mixing reports from different jobs

## API Response

The Lambda function now returns additional S3 folder information:

```json
{
  "statusCode": 200,
  "body": {
    "message": "Reports generated and uploaded successfully",
    "job_id": "abc123-def456",
    "s3_folder": {
      "bucket": "qubitz-detailed-discovery-bucket",
      "prefix": "reports/globaltech_financial_services/abc123-def456/",
      "description": "All reports for job abc123-def456 are organized in: s3://qubitz-detailed-discovery-bucket/reports/globaltech_financial_services/abc123-def456/"
    },
    "s3_reports": [
      {
        "type": "executive",
        "bucket": "qubitz-detailed-discovery-bucket",
        "key": "reports/globaltech_financial_services/abc123-def456/executive_report_20251015_120345.pdf",
        "presigned_url": "https://...",
        "expires_in_seconds": 3600
      },
      {
        "type": "technical",
        "bucket": "qubitz-detailed-discovery-bucket",
        "key": "reports/globaltech_financial_services/abc123-def456/technical_report_20251015_120347.pdf",
        "presigned_url": "https://...",
        "expires_in_seconds": 3600
      },
      {
        "type": "compliance",
        "bucket": "qubitz-detailed-discovery-bucket",
        "key": "reports/globaltech_financial_services/abc123-def456/compliance_report_20251015_120349.pdf",
        "presigned_url": "https://...",
        "expires_in_seconds": 3600
      }
    ]
  }
}
```

## DynamoDB Integration

The job_id is also stored in DynamoDB with:
- `job_id`: Primary key
- `status`: Job status (PROCESSING, COMPLETED, PARTIAL, FAILED)
- `metadata`: Report metadata
- `s3_reports`: Array of S3 upload details
- `created_at`: Job creation timestamp
- `updated_at`: Last update timestamp

## Query Examples

### List all reports for a specific job
```bash
aws s3 ls s3://qubitz-detailed-discovery-bucket/reports/globaltech_financial_services/abc123-def456/
```

### Download all reports for a job
```bash
aws s3 sync s3://qubitz-detailed-discovery-bucket/reports/globaltech_financial_services/abc123-def456/ ./local-reports/
```

### Get job status from DynamoDB
```bash
aws dynamodb get-item \
  --table-name qubitz-report-jobs \
  --key '{"job_id": {"S": "abc123-def456"}}'
```

