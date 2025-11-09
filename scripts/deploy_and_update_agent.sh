#!/bin/bash
# Deploy SAM application and update Bedrock Agent alias to latest version
# This script automates the manual steps required after sam deploy

set -e  # Exit on error

STACK_NAME="kondate-planner"
REGION="ap-northeast-1"

echo "=========================================="
echo "Deploying Kondate Planner"
echo "=========================================="

# Step 1: Get current Agent Version before deployment
echo ""
echo "[1/4] Getting current agent version..."
AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentId`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$AGENT_ID" ]; then
  AGENT_VERSION_BEFORE=$(aws bedrock-agent get-agent \
    --agent-id "$AGENT_ID" \
    --region "$REGION" \
    --query 'agent.agentVersion' \
    --output text 2>/dev/null || echo "")
  echo "Current Agent Version: $AGENT_VERSION_BEFORE"
else
  echo "Stack not found (first deployment)"
  AGENT_VERSION_BEFORE=""
fi

# Step 2: Deploy CloudFormation stack (AutoPrepare will prepare DRAFT automatically)
echo ""
echo "[2/4] Running sam deploy..."
if sam deploy --resolve-s3; then
  echo "✓ CloudFormation stack deployed/updated successfully"
else
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 1 ]; then
    echo "ℹ No CloudFormation changes detected - stack is up to date"
  else
    echo "✗ Deployment failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
  fi
fi

# Step 3: Get Agent ID and check if agent version changed
echo ""
echo "[3/4] Checking if agent was modified..."
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

# Check if agent version changed
AGENT_VERSION_AFTER=$(aws bedrock-agent get-agent \
  --agent-id "$AGENT_ID" \
  --region "$REGION" \
  --query 'agent.agentVersion' \
  --output text)

echo "Agent Version After Deploy: $AGENT_VERSION_AFTER"

AGENT_CHANGED=false
if [ "$AGENT_VERSION_BEFORE" != "$AGENT_VERSION_AFTER" ]; then
  echo "✓ Agent was modified (version changed from $AGENT_VERSION_BEFORE to $AGENT_VERSION_AFTER)"
  AGENT_CHANGED=true
else
  echo "ℹ Agent was not modified (version unchanged: $AGENT_VERSION_AFTER)"
  AGENT_CHANGED=false
fi

if [ "$AGENT_CHANGED" = true ]; then
  # Step 4: Update alias (automatically creates new version and points to it)
  echo ""
  echo "[4/4] Updating production alias..."
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
