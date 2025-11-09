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
DEPLOY_OUTPUT=$(mktemp)
AGENT_CHANGED=false

if sam deploy --resolve-s3 2>&1 | tee "$DEPLOY_OUTPUT"; then
  echo "✓ CloudFormation stack deployed/updated successfully"

  # Check if KondateAgent was in the changeset (created or modified)
  if grep -E "(CREATE_COMPLETE|UPDATE_COMPLETE).*KondateAgent.*AWS::Bedrock::Agent" "$DEPLOY_OUTPUT" > /dev/null; then
    echo "✓ Bedrock Agent (KondateAgent) was created or modified"
    AGENT_CHANGED=true
  else
    echo "ℹ Bedrock Agent (KondateAgent) was not modified"
    AGENT_CHANGED=false
  fi
else
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 1 ]; then
    echo "ℹ No CloudFormation changes detected - stack is up to date"
    AGENT_CHANGED=false
  else
    echo "✗ Deployment failed with exit code $EXIT_CODE"
    rm -f "$DEPLOY_OUTPUT"
    exit $EXIT_CODE
  fi
fi

rm -f "$DEPLOY_OUTPUT"

# Step 2: Get Agent ID from CloudFormation outputs
echo ""
echo "[2/3] Getting Agent ID from stack outputs..."
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

if [ "$AGENT_CHANGED" = true ]; then
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
else
  echo ""
  echo "=========================================="
  echo "No Changes - Skipping Alias Update"
  echo "=========================================="
  echo "Agent ID: $AGENT_ID"
  echo ""
  echo "No agent changes detected, alias was not updated."
  echo "Current production alias continues to point to the existing version."
fi
