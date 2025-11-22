# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kondate Planner (Menu Planning Assistant) - An AWS SAM serverless application that provides AI-powered meal planning using Amazon Bedrock Agents. Users interact via Slack (through Amazon Q Developer), and the agent suggests balanced meal plans based on available recipes and past menu history.

**Stack**: Python 3.12, AWS Lambda, Amazon Bedrock Agents, Amazon Q Developer, Slack, DynamoDB
**Region**: ap-northeast-1 (Tokyo)

## Architecture Overview

```
User in Slack
    ↓
Amazon Q Developer (managed service - handles Slack integration)
    ↓
Bedrock Agent (kondate-menu-planner)
    ↓
Action Lambdas (get_recipes, get_history, save_menu)
    ↓
DynamoDB (recipes, menu-history)
```

Amazon Q Developer handles all Slack integration, and the Bedrock Agent orchestrates Lambda actions via natural language understanding.

## Build and Development Commands

### Build and Deploy

```bash
# Build the SAM application
sam build

# Deploy (first time - will prompt for configuration)
sam deploy --guided

# Deploy subsequent times
sam deploy

# Delete all resources
sam delete
```

### Post-Deployment Verification

After running `sam deploy` with Slack parameters, verify the deployment:

```bash
# Check stack outputs
aws cloudformation describe-stacks --stack-name kondate-planner \
  --query 'Stacks[0].Outputs[?OutputKey==`DeveloperQSlackChannelArn`].OutputValue' --output text

# You should see the ARN of your Slack channel configuration
```

**What gets automatically created:**
- ✅ Bedrock Agent with all action groups
- ✅ Agent alias (`production`)
- ✅ Developer Q Slack channel configuration
- ✅ IAM roles with proper permissions
- ✅ DynamoDB tables
- ✅ Lambda functions with layers

**Next steps:**
1. Seed sample data (see "Data Management" section below)
2. Test in Slack (see "Amazon Q Developer Setup" section)

### Local Testing

```bash
# Test individual action functions
echo '{"category": "主菜"}' | sam local invoke GetRecipesActionFunction
echo '{"days": 7}' | sam local invoke GetHistoryActionFunction
echo '{"date": "2025-11-09", "meals": {"breakfast": [], "lunch": [], "dinner": []}}' | sam local invoke SaveMenuActionFunction
```

Note: Local testing requires DynamoDB tables to exist in AWS (no DynamoDB Local support for these functions).

### Data Management

```bash
# Seed sample data (requires boto3 installed and AWS credentials)
python scripts/seed_data.py --recipes 20 --history 30
```

### Python Environment

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies for a specific function
pip install -r src/agent_actions/get_recipes/requirements.txt
```

## Architecture Details

### Lambda Action Functions

All action functions are designed for Bedrock Agent invocation (not API Gateway):
- Accept parameters directly in event (no API Gateway wrapper)
- Return plain Python dicts (no HTTP status codes)
- Include error handling that returns errors as data

#### 1. **GetRecipesAction** (`src/agent_actions/get_recipes/app.py`)

**Purpose**: Fetches all recipes with optional category filtering

**Input**:
```json
{
  "category": "string (optional)"  // e.g., "主菜", "副菜", "汁物"
}
```

**Output**:
```json
{
  "recipes": [
    {
      "name": "string",
      "category": "string",
      "ingredients": ["string"],
      "recipe_url": "string"
    }
  ]
}
```

**When Agent Uses This**:
- User asks about available recipes
- Planning menus and needs to see recipe options
- User wants to filter by specific category

#### 2. **GetHistoryAction** (`src/agent_actions/get_history/app.py`)

**Purpose**: Retrieves menu history for past N days

**Input**:
```json
{
  "days": number  // Optional, 1-365, default 30
}
```

**Output**:
```json
{
  "history": [
    {
      "date": "YYYY-MM-DD",
      "meals": {
        "breakfast": ["レシピ名1", "レシピ名2"],
        "lunch": ["レシピ名1", "レシピ名2"],
        "dinner": ["レシピ名1", "レシピ名2", "レシピ名3"]
      },
      "recipes": ["レシピ名1", "レシピ名2", "レシピ名3"],  // Flat list for deduplication
      "notes": "string (optional)"
    }
  ]
}
```

**When Agent Uses This**:
- Planning new menus (to avoid repeating recent recipes)
- User asks about recent eating patterns
- Ensuring variety in meal suggestions

#### 3. **SaveMenuAction** (`src/agent_actions/save_menu/app.py`)

**Purpose**: Saves a confirmed menu plan to history

**Input**:
```json
{
  "date": "YYYY-MM-DD",
  "meals": {
    "breakfast": ["レシピ名1", "レシピ名2"],
    "lunch": ["レシピ名1", "レシピ名2"],
    "dinner": ["レシピ名1", "レシピ名2", "レシピ名3"]
  },
  "notes": "string (optional)"
}
```

**Output**:
```json
{
  "success": boolean,
  "date": "YYYY-MM-DD",
  "message": "string"
}
```

**When Agent Uses This**:
- **ONLY after user explicitly confirms** (e.g., "yes", "保存して", "looks good")
- Never automatically - always wait for approval

### Shared Lambda Layer (`src/layers/common/utils.py`)

Provides common utilities to all action functions:
- **AWS Clients**: `dynamodb` and `bedrock` clients (initialized once)
- **`decimal_to_float(obj)`**: Recursively converts DynamoDB `Decimal` to Python `float`/`int`
- **`parse_bedrock_parameter(value, field_name)`**: Converts Bedrock Agent parameters from Python dict format to proper JSON objects
- **`create_response()`**: Legacy function (not used by agent actions, kept for compatibility)

**Note**: The layer structure is `src/layers/common/utils.py` (not nested in a `python/` subdirectory). SAM automatically packages this correctly for Lambda layer deployment.

### OpenAPI Schemas

**Current Implementation**: OpenAPI schemas are **embedded inline** in `template.yaml` (lines 159-365) as part of each action group definition. This allows CloudFormation to manage everything in a single file.

**Legacy Schema Files** (`src/schemas/`): For reference only
- `get-recipes.yaml` - Reference schema for get_recipes action
- `get-history.yaml` - Reference schema for get_history action
- `save-menu.yaml` - Reference schema for save_menu action

**Important**: The schemas in `src/schemas/` are NOT used by the deployed agent. They serve as reference documentation only. All active schemas are defined inline in `template.yaml`. The `description` fields in the inline schemas are critical - the agent reads them to understand when to use each action.

### DynamoDB Schema

**kondate-recipes** (PK: name)
- Primary Key: `name` (recipe name is unique and human-readable)
- Attributes: `category`, `ingredients[]`, `recipe_url`, `created_at`, `updated_at`
- GSI: `CategoryIndex` (PK: category) - for efficient category filtering

**kondate-menu-history** (PK: date as YYYY-MM-DD)
- `meals` (Map): `{breakfast: ["レシピ名1", ...], lunch: [...], dinner: [...]}`
  - Each meal type is now a simple array of recipe names (strings)
- `recipes[]`: Flat list of all recipe names used in that day (for deduplication)
- `notes`, `created_at`, `updated_at`

**Schema Simplification Benefits**:
- ✅ Simpler structure: Recipe names instead of UUIDs
- ✅ Human-readable: Easy to debug and inspect data
- ✅ Agent-friendly: Works directly with names users understand
- ✅ No ID generation needed during migration from Notion

## Bedrock Agent Configuration

**The Bedrock Agent is now fully managed via CloudFormation!** 🎉

The `template.yaml` automatically creates:

1. **Bedrock Agent** (`KondateAgent`) with:
   - Agent name: `kondate-planner-agent`
   - Foundation Model (configurable via inference profile)
   - Complete agent instructions (embedded in template)
   - All three action groups with inline OpenAPI schemas:
     - `GetRecipes` → `GetRecipesActionFunction`
     - `GetHistory` → `GetHistoryActionFunction`
     - `SaveMenu` → `SaveMenuActionFunction`

2. **Agent Alias** (`KondateAgentAlias`):
   - Alias name: `production`
   - Automatically linked to the latest agent version

3. **IAM Role** (`BedrockAgentRole`) with:
   - Permissions to invoke all Lambda functions
   - Access to Foundation Model via inference profile (cross-region)
   - CloudWatch Logs access for debugging

### Viewing the Agent

After deployment, you can view and test the agent in the Bedrock console:

1. Go to **AWS Bedrock Console** → **Agents**
2. Select `kondate-planner-agent`
3. You'll see all action groups automatically configured
4. Use the built-in test interface to interact with the agent

### Modifying Agent Instructions

To update the agent's behavior:

1. Edit the `Instruction` field in `template.yaml` (lines 117-229)
2. Run `sam build && sam deploy`
3. CloudFormation will update the agent automatically
4. The agent will auto-prepare with the new instructions

**Note**: You can also modify instructions directly in the Bedrock console, but those changes will be overwritten on the next `sam deploy`. Always update `template.yaml` for persistent changes.

### Agent Behavior and Features

The agent includes several key features:

**Date Awareness**:
- Automatically calculates and communicates date ranges (e.g., "11月11日から11月13日の献立を提案します")
- Handles relative dates like "明日から" (from tomorrow) and "来週" (next week)
- Always displays specific dates in menu suggestions

**Proactive Menu Checking**:
- Checks for existing menus before suggesting new ones
- Displays existing menu details if dates are already occupied
- Asks user confirmation before proceeding with new suggestions

**Context and Insights**:
- Provides seasonal ingredient suggestions (e.g., "秋なので、きのこ料理を入れました")
- Considers recent eating patterns for balance (e.g., "最近肉が多かったので、魚料理を中心に")
- Adjusts suggestions for weekends vs. weekdays

### Switching Foundation Models

The agent uses an inference profile (cross-region routing) for better availability. To switch models:

**Deploy with different model**:
```bash
sam deploy --parameter-overrides \
  BedrockInferenceProfile="jp.anthropic.claude-haiku-4-5-20251001-v1:0"
```

**Common models**:
- `jp.anthropic.claude-sonnet-4-5-20250929-v1:0` - Claude Sonnet 4.5 (default, highest quality)
- `jp.anthropic.claude-haiku-4-5-20251001-v1:0` - Claude Haiku 4.5 (cost-effective)
- `apac.anthropic.claude-3-haiku-20240307-v1:0` - Claude 3 Haiku (lower cost)

No IAM permission updates needed - the role allows all models and inference profiles.

## Amazon Q Developer Setup

The Amazon Q Developer Slack channel is now managed via CloudFormation. Here's how to set it up:

### Prerequisites (One-Time Setup)

**IMPORTANT**: Before deploying the CloudFormation stack, you must authorize your Slack workspace with Amazon Q Developer:

1. Go to **Amazon Q Developer Console** → **Configure new client**
2. Select **Slack**
3. Click **Configure** and authorize your Slack workspace
4. After authorization, note down your **Slack Workspace ID** (visible in the console)
5. Get your **Slack Channel ID**:
   - In Slack, right-click the channel name
   - Select **Copy Link**
   - The channel ID is the last part of the URL (e.g., `C12345ABCDE`)

### Deployment with Slack Parameters

Deploy the stack with your Slack credentials:

```bash
sam deploy --parameter-overrides \
  SlackWorkspaceId=YOUR_WORKSPACE_ID \
  SlackChannelId=YOUR_CHANNEL_ID
```

### What Gets Created

The CloudFormation stack creates:

1. **AWS::Chatbot::SlackChannelConfiguration** (`DeveloperQSlackChannel`)
   - Links your Slack channel to Amazon Q Developer
   - Connects to the Bedrock Agent alias
   - Uses the `AmazonQChatbotRole` IAM role
   - Uses `InvokeBedrockAgentPolicy` as guardrail

2. **Shared Policy** (`InvokeBedrockAgentPolicy`)
   - Used by both the IAM role AND the guardrail policy
   - Allows `bedrock:InvokeAgent`, `bedrock:GetAgent`, `bedrock:ListAgents`
   - Scoped to all agents in the account (minimal scope needed for Amazon Q Developer)

3. **IAM Role** (`AmazonQChatbotRole`)
   - Assumed by Amazon Q Developer service
   - Attached policies: `InvokeBedrockAgentPolicy` + `CloudWatchLogsReadOnlyAccess`

### Adding Bedrock Connector in Slack

After deployment completes, you need to connect the Bedrock Agent to your Slack channel:

**Step 1: Get Agent ARN and Alias ID**

Option 1 - Via CLI:
```bash
aws cloudformation describe-stacks --stack-name kondate-planner \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentArn` || OutputKey==`BedrockAgentAliasId`].[OutputKey,OutputValue]' \
  --output table
```

Option 2 - Via Bedrock Agent Console:
- Go to **Bedrock Agent Console** → **Agents** → **kondate-planner-agent**
- Agent ARN is shown at the top of the agent details page
- Alias ID can be found in the **Aliases** section (look for `production`)

**Step 2: Add the connector in Slack**

In your Slack channel, run:

```
@Amazon Q connector add kondate-planner <Agent ARN> <Alias ID>
```

**Example**:
```
@Amazon Q connector add kondate-planner arn:aws:bedrock:ap-northeast-1:123456789012:agent/ABCDEFGHIJ TESTALIASID
```

**Other useful commands**:
- List connectors: `@Amazon Q connector list`
- Delete connector: `@Amazon Q connector delete kondate-planner`

### Testing in Slack

After adding the connector, test in your configured Slack channel:

```
@Amazon Q 3日分の献立を提案して
```

The agent should:
1. Fetch recipes
2. Fetch recent history
3. Generate a balanced 3-day menu
4. Ask for confirmation before saving

### Updating Configuration

To change Slack channel or workspace:

```bash
sam deploy --parameter-overrides \
  SlackWorkspaceId=NEW_WORKSPACE_ID \
  SlackChannelId=NEW_CHANNEL_ID
```

CloudFormation will update the channel configuration without recreating other resources.

## Critical Implementation Details

### Bedrock Agent Parameter Parsing

Bedrock Agent sometimes sends parameters in Python dict format instead of JSON:
```
{lunch=[焼きそば, サラダ], breakfast=[...]}
```

**Solution**: The shared layer includes `parse_bedrock_parameter()` utility (`utils.py`) that handles this conversion using regex-based transformation. This is used by `save_menu` action to parse the `meals` parameter. The conversion is transparent to the user but critical for reliability.

**Note**: With the simplified schema (recipe names as strings instead of objects), parameter parsing is now simpler and more reliable.

### Amazon Bedrock Permissions

**Model Access**: Foundation Model via Inference Profile (cross-region)

The Bedrock Agent Role has permissions to access:
- **Any inference profile** in your account: `inference-profile/*`
- **Any foundation model** in any region: `foundation-model/*`

This allows you to switch between any Bedrock model without needing to update IAM permissions. The role is appropriately scoped (inference profiles limited to your account) while allowing flexible model selection.

**Configurable via Parameter**: Set `BedrockInferenceProfile` parameter during deployment to use different models:
- Default: `jp.anthropic.claude-sonnet-4-5-20250929-v1:0` (Claude Sonnet 4.5)
- Example: `jp.anthropic.claude-haiku-4-5-20251001-v1:0` (Claude Haiku 4.5 for cost savings)

**Note**: Cross-region inference profiles may invoke models in other regions, which is why the policy allows foundation models in all regions (`arn:aws:bedrock:*::foundation-model/*`).

### Date and Integer Validation

Action functions use shared validation utilities:
- **`safe_int_conversion()`**: Validates integer inputs (e.g., `days` parameter)
- **`validate_date_format()`**: Ensures dates are `YYYY-MM-DD` format

### Decimal Handling

DynamoDB returns numeric values as `Decimal` objects. All action functions use `decimal_to_float()` from the shared layer to convert before returning data to the agent.

### Error Handling Pattern

Agent actions return errors as data (not exceptions):

```python
# Good - agent can handle this gracefully
return {
    'success': False,
    'error': 'Validation failed',
    'message': 'User-friendly error message'
}

# Bad - would crash the agent
raise ValueError('Validation failed')
```

## Testing Considerations

### Testing Action Functions Directly

Each action function expects a plain dict event:

```bash
# Test GetRecipesAction
echo '{"category": "主菜"}' | sam local invoke GetRecipesActionFunction

# Test GetHistoryAction
echo '{"days": 7}' | sam local invoke GetHistoryActionFunction

# Test SaveMenuAction
echo '{
  "date": "2025-11-09",
  "meals": {
    "breakfast": ["味噌汁", "納豆"],
    "lunch": ["カレー"],
    "dinner": ["焼き魚", "サラダ"]
  }
}' | sam local invoke SaveMenuActionFunction
```

### Testing the Agent

**In Bedrock Console**:
- Use the built-in test interface after preparing the agent
- Provides detailed trace of action invocations

**In Slack (via Amazon Q Developer)**:
- Mention `@Amazon Q ask kondate-planner` followed by your request
- Agent responses appear as threaded messages

### Common Test Scenarios

1. **Menu Suggestion**:
   - Input: "3日分の献立を提案して"
   - Expected: Agent calls `get_recipes`, `get_history`, then suggests menu
   - Expected: Agent asks for confirmation before saving

2. **View History**:
   - Input: "最近の献立を見せて"
   - Expected: Agent calls `get_history` with default 30 days

3. **Filtered Recipes**:
   - Input: "主菜のレシピを見せて"
   - Expected: Agent calls `get_recipes` with `category="主菜"`

4. **Save Confirmation**:
   - Input: "保存して" (after menu suggestion)
   - Expected: Agent calls `save_menu` with the previously suggested menu

## Common Pitfalls

1. **Missing Slack Parameters**: Deployment will fail if you don't provide `SlackWorkspaceId` and `SlackChannelId` parameters
2. **Slack Workspace Not Authorized**: You must authorize your Slack workspace in Amazon Q Developer console BEFORE deploying the CloudFormation stack
3. **Lambda Permissions**: Ensure Lambda resource-based policies allow `bedrock.amazonaws.com` to invoke (automatically configured in template)
4. **Menu History Structure**: The `meals` field contains simple arrays - each meal type is an array of recipe names (strings)
5. **Date Format**: History dates are `YYYY-MM-DD` strings (not ISO8601 timestamps)
6. **Explicit Confirmation**: Agent should NEVER call `save_menu` without user approval - this is critical for UX
7. **Public Repository**: Never commit actual Slack IDs to `samconfig.toml` if using a public repo
8. **Recipe Categories**: When adding custom recipes, use standard categories: `主菜` (main dish), `副菜` (side dish), `汁物` (soup), `主食` (staple/carbs), `デザート` (dessert)

## Deployment Checklist

When deploying to a new environment:

### First-Time Setup
- [ ] Authorize Slack workspace in Amazon Q Developer Console (one-time)
- [ ] Get Slack Workspace ID from Amazon Q Developer Console
- [ ] Get Slack Channel ID from Slack (right-click channel > Copy Link)

### Deployment
- [ ] Run `sam build`
- [ ] Run `sam deploy --parameter-overrides SlackWorkspaceId=XXX SlackChannelId=YYY`
- [ ] Verify stack outputs show all resources created

### Add Bedrock Connector
- [ ] Get Agent ARN and Alias ID: `aws cloudformation describe-stacks --stack-name kondate-planner --query 'Stacks[0].Outputs[?OutputKey==\`BedrockAgentArn\` || OutputKey==\`BedrockAgentAliasId\`].[OutputKey,OutputValue]' --output table`
- [ ] In Slack: `@Amazon Q connector add kondate-planner <Agent ARN> <Alias ID>`

### Testing
- [ ] Test in Slack: `@Amazon Q 3日分の献立を提案して`
- [ ] (Optional) Test in Bedrock console using the agent test interface

### Data Setup
- [ ] Seed sample data: `python scripts/seed_data.py --recipes 20 --history 30`

**That's it!** The Bedrock Agent, action groups, IAM roles, and Slack integration are all managed by CloudFormation now.

## CI/CD with GitHub Actions

The project supports automated deployment via GitHub Actions, triggered on pushes to the main branch or manual workflow dispatch.

### Workflow Configuration

**Location**: `.github/workflows/deploy.yml`

**Triggers**:
- Push to `main` branch
- Manual workflow dispatch (via GitHub Actions UI)

**Steps**:
1. Checkout code
2. Set up Python 3.12
3. Install SAM CLI
4. Configure AWS credentials (OIDC recommended)
5. Run `sam build`
6. Run `sam deploy` with Slack parameters

### AWS Authentication Setup

#### Option 1: OIDC (Recommended)

OIDC provides better security than long-lived access keys:

**1. Create IAM OIDC Identity Provider**:
```bash
# Via AWS Console: IAM → Identity providers → Add provider
# Provider type: OpenID Connect
# Provider URL: https://token.actions.githubusercontent.com
# Audience: sts.amazonaws.com
```

**2. Create IAM Role with Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:OWNER/kondate-planner:*"
        }
      }
    }
  ]
}
```

**3. Attach Required Permissions**:
- CloudFormation (create/update stacks)
- S3 (upload SAM artifacts)
- Lambda (create/update functions)
- IAM (create/update roles)
- DynamoDB (create/update tables)
- Bedrock (create/update agents)
- Chatbot (create/update Slack configurations)

**Recommended Managed Policies**:
- `AWSCloudFormationFullAccess`
- `AWSLambda_FullAccess`
- `IAMFullAccess` (or custom minimal policy)
- `AmazonDynamoDBFullAccess`

**Custom Policies for Bedrock and Chatbot**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "chatbot:*"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Option 2: Access Keys (Not Recommended)

Use IAM user with access keys only if OIDC is not feasible. Store `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as GitHub Secrets.

### GitHub Secrets Configuration

**Required Secrets** (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ROLE_ARN` | IAM Role ARN for OIDC authentication | `arn:aws:iam::123456789012:role/GitHubActionsRole` |
| `SLACK_WORKSPACE_ID` | Slack Workspace ID from Amazon Q Developer Console | `T1234567890` |
| `SLACK_CHANNEL_ID` | Slack Channel ID | `C1234567890` |

**Optional Secrets** (if using access keys instead of OIDC):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (or hardcode `ap-northeast-1` in workflow)

### Workflow File Structure

```yaml
name: Deploy SAM Application to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for OIDC
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Set up AWS SAM CLI
        uses: aws-actions/setup-sam@v2

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-northeast-1

      - name: SAM Build
        run: sam build

      - name: SAM Deploy
        run: |
          sam deploy \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset \
            --parameter-overrides \
              SlackWorkspaceId=${{ secrets.SLACK_WORKSPACE_ID }} \
              SlackChannelId=${{ secrets.SLACK_CHANNEL_ID }}
```

### Manual Workflow Execution

To manually trigger deployment:
1. Go to **Actions** tab in GitHub
2. Select **Deploy SAM Application to AWS**
3. Click **Run workflow**
4. Select branch (usually `main`)
5. Click **Run workflow** button

### Deployment Verification

After workflow completes, verify deployment:

```bash
# Check stack outputs
aws cloudformation describe-stacks --stack-name kondate-planner \
  --query 'Stacks[0].Outputs' --output table

# Check Bedrock Agent status
aws bedrock-agent get-agent --agent-id <AGENT_ID>
```

### Troubleshooting CI/CD

**Common Issues**:

1. **OIDC Authentication Failed**:
   - Verify IAM OIDC provider is configured correctly
   - Check trust policy repository name matches exactly
   - Ensure workflow has `id-token: write` permission

2. **SAM Deploy Fails with Permission Error**:
   - Verify IAM role has all required permissions
   - Check CloudFormation stack events for specific errors
   - Ensure S3 bucket for SAM artifacts exists

3. **Slack Parameters Missing**:
   - Verify `SLACK_WORKSPACE_ID` and `SLACK_CHANNEL_ID` secrets are set
   - Check workflow logs to see parameter values (masked)

4. **Changeset Contains No Changes**:
   - Normal behavior when no code/template changes
   - Workflow uses `--no-fail-on-empty-changeset` to handle this

### Security Best Practices

- **Never commit secrets to repository**: Use GitHub Secrets for all sensitive values
- **Use OIDC over access keys**: Automatic credential rotation, better audit trail
- **Restrict workflow permissions**: Use minimal `permissions:` block
- **Review CloudFormation changesets**: Monitor what resources are being modified
- **Rotate access keys regularly**: If using access keys instead of OIDC

### Future CI/CD Enhancements

- Add testing stage before deployment (run unit tests, integration tests)
- Multi-environment deployment (staging, production)
- Manual approval gate for production deployments
- Post-deployment verification (health checks, smoke tests)
- Rollback mechanism on deployment failure
- Slack notifications on deployment success/failure

## Future Enhancements

- Replace DynamoDB recipe data source with Notion API integration
- Add pagination for large recipe/history datasets (DynamoDB Scan limits)
- Support multi-week menu planning
- Add nutritional analysis using recipe ingredients
- Support dietary restrictions and preferences
