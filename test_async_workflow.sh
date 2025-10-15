#!/bin/bash

# Test script for the async report generation workflow

FUNCTION_URL="https://zpsfp6yy4ucpagy454srjfsq4a0lguis.lambda-url.eu-west-2.on.aws/"

echo "================================================"
echo "Testing Async Report Generation Workflow"
echo "================================================"
echo ""

# Step 1: Submit a job
echo "Step 1: Submitting report generation job..."
echo "-------------------------------------------"

RESPONSE=$(curl -s -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d @test_json_comprehensive.json)

echo "Response: $RESPONSE"
echo ""

# Extract job_id from response using python
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))" 2>/dev/null)

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to get job_id. Response was:"
    echo "$RESPONSE"
    exit 1
fi

echo "✅ Job submitted successfully!"
echo "Job ID: $JOB_ID"
echo ""

# Step 2: Poll for job completion
echo "Step 2: Checking job status..."
echo "-------------------------------------------"

MAX_ATTEMPTS=40  # 40 attempts * 10 seconds = 400 seconds (6.7 minutes)
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    echo "Attempt $ATTEMPT of $MAX_ATTEMPTS - Checking status..."
    
    STATUS_RESPONSE=$(curl -s "$FUNCTION_URL?job_id=$JOB_ID")
    
    # Extract status using python
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
    
    echo "  Status: $STATUS"
    
    if [ "$STATUS" = "COMPLETED" ]; then
        echo ""
        echo "✅ Job completed successfully!"
        echo "================================================"
        echo "Full Response:"
        echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
        echo "================================================"
        
        # Extract and display presigned URL
        PRESIGNED_URL=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('s3', {}).get('presigned_url', ''))" 2>/dev/null)
        if [ -n "$PRESIGNED_URL" ]; then
            echo ""
            echo "📄 Download your report:"
            echo "$PRESIGNED_URL"
            echo ""
            echo "You can download it with:"
            echo "curl -o report.pdf '$PRESIGNED_URL'"
        fi
        
        exit 0
    elif [ "$STATUS" = "FAILED" ]; then
        echo ""
        echo "❌ Job failed!"
        echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
        exit 1
    elif [ "$STATUS" = "PENDING" ] || [ "$STATUS" = "PROCESSING" ]; then
        echo "  ⏳ Job is still processing... waiting 10 seconds"
        sleep 10
    else
        echo "  ⚠️  Unknown status: $STATUS"
        echo "  Response: $STATUS_RESPONSE"
        sleep 10
    fi
done

echo ""
echo "⏰ Timeout: Job did not complete within expected time"
echo "Last known status: $STATUS"
echo "You can check the status later with:"
echo "curl '$FUNCTION_URL?job_id=$JOB_ID'"

