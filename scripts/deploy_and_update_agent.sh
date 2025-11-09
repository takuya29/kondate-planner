#!/bin/bash
# Deploy SAM application and update Bedrock Agent alias to latest version
# This script automates the manual steps required after sam deploy

set -e  # Exit on error

STACK_NAME="kondate-planner"
REGION="ap-northeast-1"

echo "=========================================="
echo "Deploying Kondate Planner"
echo "=========================================="

# Step 1: Deploy CloudFormation stack (AutoPrepare will prepare DRAFT automatically)
echo ""
echo "[1/3] Running sam deploy..."
sam deploy --resolve-s3

# Step 2: Get Agent ID from CloudFormation outputs
echo ""
echo "[2/3] Getting Agent ID and Alias ID from stack outputs..."
AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentId`].OutputValue' \
  --output text)

if [ -z "$AGENT_ID" ]; then
  echo "Error: Could not retrieve Agent ID from CloudFormation outputs"
  exit 1
fi

echo "Agent ID: $AGENT_ID"
echo "(Agent DRAFT is auto-prepared by CloudFormation)"

# Step 3: Update alias (automatically creates new version and points to it)
echo ""
echo "[3/3] Updating production alias..."
ALIAS_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentAliasId`].OutputValue' \
  --output text)

if [ -z "$ALIAS_ID" ]; then
  echo "Error: Could not retrieve Alias ID from CloudFormation outputs"
  exit 1
fi

echo "Alias ID: $ALIAS_ID"

# Update alias (automatically creates version and points to it when routing-configuration is omitted)
UPDATE_RESULT=$(aws bedrock-agent update-agent-alias \
  --agent-id "$AGENT_ID" \
  --agent-alias-id "$ALIAS_ID" \
  --agent-alias-name "production" \
  --region "$REGION" \
  --output json)

# Extract the version from the routing configuration
VERSION=$(echo $UPDATE_RESULT | jq -r '.agentAlias.routingConfiguration[0].agentVersion')

echo "✓ Alias updated (automatically created and pointed to version: $VERSION)"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Agent ID: $AGENT_ID"
echo "Alias ID: $ALIAS_ID"
echo "New Version: $VERSION"
echo "Alias now points to: version $VERSION"
echo ""
echo "Your changes are now live in Slack via Amazon Q Developer!"
