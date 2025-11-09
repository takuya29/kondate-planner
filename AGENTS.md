# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

献立作成補助ツール (Menu Planning Assistant) - An AWS SAM serverless application that provides AI-powered meal planning using Amazon Bedrock Agents with Claude Sonnet 4.5. Users interact via Slack (through AWS Chatbot), and the agent suggests balanced meal plans based on available recipes and past menu history.

**Stack**: Python 3.12, AWS Lambda, Amazon Bedrock Agents, AWS Chatbot, Slack, DynamoDB
**Region**: ap-northeast-1 (Tokyo)

## Architecture Overview

```
User in Slack
    ↓
AWS Chatbot (managed service - handles Slack integration)
    ↓
Bedrock Agent (kondate-menu-planner)
    ↓
Action Lambdas (get_recipes, get_history, save_menu)
    ↓
DynamoDB (recipes, menu-history)
```

**Key Difference from Previous Architecture**: No REST API or custom Slack handler. AWS Chatbot handles all Slack integration, and the Bedrock Agent orchestrates Lambda actions via natural language understanding.

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

### Post-Deployment Setup

After `sam deploy`, you need to:

1. **Upload OpenAPI schemas to S3**:
```bash
# Get bucket name from stack outputs
aws cloudformation describe-stacks --stack-name kondate-planner \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentSchemasBucketName`].OutputValue' --output text

# Upload schemas
aws s3 cp src/schemas/recipe-management.yaml s3://kondate-agent-schemas-{YOUR-ACCOUNT-ID}/recipe-management.yaml
aws s3 cp src/schemas/history-management.yaml s3://kondate-agent-schemas-{YOUR-ACCOUNT-ID}/history-management.yaml
```

2. **Create Bedrock Agent** (see "Bedrock Agent Configuration" section below)

3. **Configure AWS Chatbot** (see "AWS Chatbot Setup" section below)

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
      "recipe_id": "uuid",
      "name": "string",
      "category": "string",
      "cooking_time": number,
      "ingredients": ["string"],
      "recipe_url": "string",
      "tags": ["string"]
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
        "breakfast": [{"recipe_id": "...", "name": "..."}],
        "lunch": [...],
        "dinner": [...]
      },
      "recipes": ["recipe_id1", "recipe_id2"],  // Flat list for deduplication
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
    "breakfast": [{"recipe_id": "...", "name": "..."}],
    "lunch": [...],
    "dinner": [...]
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
- **`create_response()`**: Legacy function (not used by agent actions, kept for compatibility)

**Note**: The layer structure is `src/layers/common/utils.py` (not nested in a `python/` subdirectory). SAM automatically packages this correctly for Lambda layer deployment.

### OpenAPI Schemas (`src/schemas/`)

Define how the Bedrock Agent calls each Lambda action:

- **`recipe-management.yaml`**: Defines `get_recipes` action
- **`history-management.yaml`**: Defines `get_history` and `save_menu` actions

**Important**: These schemas are the "instruction manual" for the agent. The `description` fields are critical - the agent reads them to understand when to use each action.

### DynamoDB Schema

**kondate-recipes** (PK: recipe_id)
- `name`, `category`, `cooking_time`, `ingredients[]`, `recipe_url`, `tags[]`, `created_at`, `updated_at`

**kondate-menu-history** (PK: date as YYYY-MM-DD)
- `meals` (Map): `{breakfast: [{recipe_id, name}], lunch: [...], dinner: [...]}`
- `recipes[]`: Flat list of all recipe_ids used in that day (for deduplication)
- `notes`, `created_at`, `updated_at`

## Bedrock Agent Configuration

After deploying the SAM stack, create the agent manually in the Bedrock console:

### Step 1: Create Agent

1. Go to AWS Bedrock Console → Agents → Create agent
2. **Agent name**: `kondate-menu-planner`
3. **Agent description**: `Meal planning assistant for Japanese recipes`
4. **Model**: `Claude Sonnet 4.5` (`anthropic.claude-sonnet-4-5-20250929-v1:0`)
5. **IAM Role**: Use the role from stack output `BedrockAgentRoleArn`

### Step 2: Agent Instructions

Paste the following into the agent instructions:

```
You are a helpful meal planning assistant that helps users create balanced Japanese meal plans.

AVAILABLE RECIPES AND HISTORY:
- Call get_recipes() to see all available recipes. You can optionally filter by category.
- Call get_history() to see recent menus (default 30 days). Use this to avoid repeating recipes.

MEAL PLANNING RULES:
When generating menu suggestions:
1. Breakfast: 1-2 dishes (e.g., rice + miso soup, or toast + salad)
2. Lunch: 1-3 dishes (balanced meal or bento-style)
3. Dinner: 2-3 dishes (main + side + soup is common)
4. Variety: Don't repeat the same main protein on consecutive days
5. Balance: Include vegetables in every meal when possible
6. Cooking time: Mix quick recipes (<30min) with more involved ones

WORKFLOW:
1. When user asks for menu suggestions, fetch recipes and recent history
2. Generate a menu plan for the requested number of days (typically 3 or 7)
3. Present the menu clearly with recipe names and categories
4. Ask: "この献立で保存しますか？ (Would you like me to save this menu?)"
5. ONLY call save_menu() if user explicitly confirms (yes/はい/保存して/looks good/etc.)
6. If user says no or requests changes, regenerate based on their feedback

TONE:
- Be friendly and conversational
- Respond in Japanese or English based on user's language
- Provide brief cooking tips or nutritional insights when relevant
```

### Step 3: Add Action Groups

**Action Group 1: RecipeManagement**
- **Name**: `RecipeManagement`
- **Description**: `Access to recipe database`
- **Lambda**: Select `GetRecipesActionFunction` from the list
- **OpenAPI Schema**:
  - Select "S3 Object"
  - Bucket: `kondate-agent-schemas-{YOUR-ACCOUNT-ID}`
  - Object key: `recipe-management.yaml`

**Action Group 2: HistoryManagement**
- **Name**: `HistoryManagement`
- **Description**: `Manage menu history`
- **Lambda**: Select `GetHistoryActionFunction` from the list
- **OpenAPI Schema**:
  - Select "S3 Object"
  - Bucket: `kondate-agent-schemas-{YOUR-ACCOUNT-ID}`
  - Object key: `history-management.yaml`

**Action Group 3: SaveHistory**
- **Name**: `SaveHistory`
- **Description**: `Save approved menus`
- **Lambda**: Select `SaveMenuActionFunction` from the list
- **OpenAPI Schema**: Same as HistoryManagement (contains both actions)

### Step 4: Prepare and Test

1. Click "Prepare" to build the agent
2. Wait for preparation to complete (~2 minutes)
3. Test in the console with prompts like:
   - "3日分の献立を提案して" (Suggest a 3-day menu)
   - "最近の献立を見せて" (Show recent menus)
4. Create an **Alias** (e.g., `production`) for use with AWS Chatbot

## AWS Chatbot Setup

After creating the Bedrock Agent, configure AWS Chatbot to connect Slack:

### Step 1: Configure Slack Workspace

1. Go to AWS Chatbot Console
2. Click "Configure new client" → Select **Slack**
3. Authorize your Slack workspace
4. Select a Slack channel (e.g., `#kondate-planner`)

### Step 2: Configure Bedrock Agent Integration

1. In the channel configuration:
   - Enable "Amazon Bedrock Agent"
   - Select agent: `kondate-menu-planner`
   - Select alias: `production` (or `DRAFT` for testing)
2. Set IAM role permissions:
   - Grant `AmazonBedrockFullAccess` (or scoped policy for your agent)

### Step 3: Test in Slack

Go to your configured Slack channel and type:
```
@AWS 3日分の献立を提案して
```

The agent should:
1. Fetch recipes
2. Fetch recent history
3. Generate a balanced 3-day menu
4. Ask for confirmation before saving

## Critical Implementation Details

### Amazon Bedrock Permissions

**Model Access**: Claude Sonnet 4.5 via Inference Profile (cross-region)

The Bedrock Agent Role must have permissions for:
- **Inference Profile**: `arn:aws:bedrock:ap-northeast-1:{account}:inference-profile/jp.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Foundation Models** in both regions:
  - `arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0`
  - `arn:aws:bedrock:ap-northeast-3::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0`

This is already configured in the SAM template's `BedrockAgentRole`.

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
    "breakfast": [{"recipe_id": "abc", "name": "味噌汁"}],
    "lunch": [{"recipe_id": "def", "name": "カレー"}],
    "dinner": [{"recipe_id": "ghi", "name": "焼き魚"}]
  }
}' | sam local invoke SaveMenuActionFunction
```

### Testing the Agent

**In Bedrock Console**:
- Use the built-in test interface after preparing the agent
- Provides detailed trace of action invocations

**In Slack (via AWS Chatbot)**:
- Mention `@AWS` followed by your request
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

1. **Schemas Not Uploaded**: If agent can't find actions, verify schemas are in S3 at the correct path
2. **Lambda Permissions**: Ensure Lambda resource-based policies allow `bedrock.amazonaws.com` to invoke
3. **Agent Not Prepared**: Always "Prepare" the agent after making changes to action groups or instructions
4. **AWS Chatbot IAM**: Chatbot's IAM role needs permission to invoke the Bedrock Agent
5. **Menu History Structure**: The `meals` field contains nested arrays - each meal type is an array of recipe objects
6. **Date Format**: History dates are `YYYY-MM-DD` strings (not ISO8601 timestamps)
7. **Explicit Confirmation**: Agent should NEVER call `save_menu` without user approval - this is critical for UX

## Deployment Checklist

When deploying to a new environment:

- [ ] Run `sam build && sam deploy --guided`
- [ ] Note the S3 bucket name from outputs
- [ ] Upload OpenAPI schemas to S3
- [ ] Create Bedrock Agent in console (use stack outputs for ARNs)
- [ ] Add action groups with correct Lambda ARNs
- [ ] Prepare the agent
- [ ] Test in Bedrock console
- [ ] Create agent alias (`production`)
- [ ] Configure AWS Chatbot with Slack workspace
- [ ] Connect Chatbot to agent alias
- [ ] Test end-to-end in Slack channel
- [ ] Seed sample data: `python scripts/seed_data.py --recipes 20 --history 30`

## Future Enhancements

- Replace DynamoDB recipe data source with Notion API integration
- Add pagination for large recipe/history datasets (DynamoDB Scan limits)
- Support multi-week menu planning
- Add nutritional analysis using recipe ingredients
- Support dietary restrictions and preferences
