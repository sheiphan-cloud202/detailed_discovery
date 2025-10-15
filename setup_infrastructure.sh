#!/bin/bash

# Setup script for Qubitz Detailed Discovery infrastructure
# This script creates DynamoDB table and configures Lambda Function URL

set -e  # Exit on error

# Configuration variables
AWS_REGION="${AWS_REGION:-eu-west-2}"
DYNAMODB_TABLE="${DYNAMODB_TABLE:-qubitz-report-jobs}"
WORKER_LAMBDA_NAME="qubitz-detailed-discovery"
COORDINATOR_LAMBDA_NAME="${COORDINATOR_LAMBDA_NAME:-qubitz-discovery-coordinator}"
ACCOUNT_ID="781364298443"

echo "================================================"
echo "Qubitz Infrastructure Setup"
echo "================================================"
echo "Region: $AWS_REGION"
echo "DynamoDB Table: $DYNAMODB_TABLE"
echo "Worker Lambda: $WORKER_LAMBDA_NAME"
echo "Coordinator Lambda: $COORDINATOR_LAMBDA_NAME"
echo "================================================"
echo ""

# Step 1: Create DynamoDB table for job tracking
echo "Step 1: Creating DynamoDB table '$DYNAMODB_TABLE'..."
aws dynamodb create-table \
    --table-name "$DYNAMODB_TABLE" \
    --attribute-definitions \
        AttributeName=job_id,AttributeType=S \
    --key-schema \
        AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION" \
    --tags Key=Project,Value=QubitzDetailedDiscovery \
    2>/dev/null || echo "Table already exists or creation failed - continuing..."

echo "Waiting for table to be active..."
aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE" --region "$AWS_REGION"
echo "✓ DynamoDB table ready"
echo ""

# Step 2: Add TTL attribute for automatic cleanup (optional but recommended)
echo "Step 2: Enabling TTL for automatic job cleanup (after 7 days)..."
aws dynamodb update-time-to-live \
    --table-name "$DYNAMODB_TABLE" \
    --time-to-live-specification "Enabled=true, AttributeName=ttl" \
    --region "$AWS_REGION" \
    2>/dev/null || echo "TTL already configured or update failed - continuing..."
echo "✓ TTL configured"
echo ""

# Step 3: Update worker Lambda environment variables
echo "Step 3: Updating worker Lambda environment variables..."
aws lambda update-function-configuration \
    --function-name "$WORKER_LAMBDA_NAME" \
    --environment "Variables={
        AWS_REGION=$AWS_REGION,
        DYNAMODB_TABLE=$DYNAMODB_TABLE,
        REPORT_BUCKET=qubitz-detailed-discovery-bucket,
        REPORT_PREFIX=reports/,
        SSE_MODE=AES256,
        PRESIGN_TTL_SEC=3600,
        BEDROCK_REGION=$AWS_REGION,
        BEDROCK_MODEL_ID=anthropic.claude-3-7-sonnet-20250219-v1:0
    }" \
    --region "$AWS_REGION"
echo "✓ Worker Lambda environment updated"
echo ""

# Step 4: Grant worker Lambda permissions to DynamoDB
echo "Step 4: Granting worker Lambda DynamoDB permissions..."
cat > /tmp/dynamodb-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:$AWS_REGION:$ACCOUNT_ID:table/$DYNAMODB_TABLE"
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name "qubitz-detailed-discovery-role" \
    --policy-name "QubitzDynamoDBAccess" \
    --policy-document file:///tmp/dynamodb-policy.json \
    2>/dev/null || echo "Note: If role name is different, you'll need to update this manually"
echo "✓ DynamoDB permissions granted"
echo ""

# Step 5: Create/Update coordinator Lambda (assuming you want to deploy it)
echo "Step 5: Creating coordinator Lambda function..."
echo "Note: You need to package and deploy lambda_coordinator.py first"
echo "To deploy coordinator Lambda, run:"
echo ""
echo "  # Create deployment package"
echo "  zip lambda_coordinator.zip lambda_coordinator.py"
echo ""
echo "  # Create IAM role for coordinator Lambda"
echo "  aws iam create-role \\"
echo "    --role-name qubitz-coordinator-role \\"
echo "    --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}'"
echo ""
echo "  # Attach basic execution policy"
echo "  aws iam attach-role-policy \\"
echo "    --role-name qubitz-coordinator-role \\"
echo "    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
echo ""
echo "  # Create the Lambda function"
echo "  aws lambda create-function \\"
echo "    --function-name $COORDINATOR_LAMBDA_NAME \\"
echo "    --runtime python3.11 \\"
echo "    --role arn:aws:iam::$ACCOUNT_ID:role/qubitz-coordinator-role \\"
echo "    --handler lambda_coordinator.handler \\"
echo "    --zip-file fileb://lambda_coordinator.zip \\"
echo "    --timeout 30 \\"
echo "    --region $AWS_REGION"
echo ""
read -p "Have you deployed the coordinator Lambda? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please deploy coordinator Lambda first, then re-run this script"
    exit 1
fi

# Step 6: Grant coordinator Lambda permissions
echo "Step 6: Granting coordinator Lambda permissions..."
cat > /tmp/coordinator-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": "arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:$WORKER_LAMBDA_NAME"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:$AWS_REGION:$ACCOUNT_ID:table/$DYNAMODB_TABLE"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::qubitz-detailed-discovery-bucket/*"
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name "qubitz-coordinator-role" \
    --policy-name "QubitzCoordinatorPolicy" \
    --policy-document file:///tmp/coordinator-policy.json
echo "✓ Coordinator permissions granted"
echo ""

# Step 7: Update coordinator Lambda environment
echo "Step 7: Updating coordinator Lambda environment..."
aws lambda update-function-configuration \
    --function-name "$COORDINATOR_LAMBDA_NAME" \
    --environment "Variables={
        AWS_REGION=$AWS_REGION,
        WORKER_LAMBDA_ARN=arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:$WORKER_LAMBDA_NAME,
        DYNAMODB_TABLE=$DYNAMODB_TABLE,
        PRESIGN_TTL_SEC=3600
    }" \
    --region "$AWS_REGION"
echo "✓ Coordinator environment updated"
echo ""

# Step 8: Create Lambda Function URL
echo "Step 8: Creating Lambda Function URL for coordinator..."
FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name "$COORDINATOR_LAMBDA_NAME" \
    --auth-type AWS_IAM \
    --region "$AWS_REGION" \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || \
    aws lambda get-function-url-config \
        --function-name "$COORDINATOR_LAMBDA_NAME" \
        --region "$AWS_REGION" \
        --query 'FunctionUrl' \
        --output text)

echo "✓ Function URL created: $FUNCTION_URL"
echo ""

# Step 9: Add resource-based policy for Function URL invocation
echo "Step 9: Adding Function URL invoke permissions..."
aws lambda add-permission \
    --function-name "$COORDINATOR_LAMBDA_NAME" \
    --statement-id "FunctionURLAllowPublicAccess" \
    --action "lambda:InvokeFunctionUrl" \
    --principal "*" \
    --function-url-auth-type "AWS_IAM" \
    --region "$AWS_REGION" \
    2>/dev/null || echo "Permission already exists"
echo "✓ Function URL permissions configured"
echo ""

# Cleanup
rm -f /tmp/dynamodb-policy.json /tmp/coordinator-policy.json

echo "================================================"
echo "✓ Setup Complete!"
echo "================================================"
echo ""
echo "Your Function URL: $FUNCTION_URL"
echo ""
echo "Usage:"
echo "------"
echo "1. Submit a job (POST):"
echo "   curl -X POST '$FUNCTION_URL' \\"
echo "     --aws-sigv4 'aws:amz:$AWS_REGION:lambda' \\"
echo "     --user \$AWS_ACCESS_KEY_ID:\$AWS_SECRET_ACCESS_KEY \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d @sample-payload-detailed_discovery.json"
echo ""
echo "2. Check job status (GET):"
echo "   curl '$FUNCTION_URL?job_id=YOUR_JOB_ID' \\"
echo "     --aws-sigv4 'aws:amz:$AWS_REGION:lambda' \\"
echo "     --user \$AWS_ACCESS_KEY_ID:\$AWS_SECRET_ACCESS_KEY"
echo ""
echo "================================================"

