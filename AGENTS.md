# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

献立作成補助ツール (Menu Planning Assistant) - An AWS SAM serverless application that provides AI-powered meal planning using Amazon Bedrock (Claude Sonnet 4.5). The system suggests balanced meal plans based on available recipes and past menu history.

**Stack**: Python 3.12, AWS Lambda, API Gateway (HTTP API), DynamoDB, Amazon Bedrock
**Region**: ap-northeast-1 (Tokyo)

## Build and Development Commands

### Build and Deploy

```bash
# Build the SAM application (uses parallel builds)
sam build

# Deploy (first time - will prompt for configuration)
sam deploy --guided

# Deploy subsequent times
sam deploy

# Delete all resources
sam delete
```

### Local Development

```bash
# Start API locally on http://localhost:3000
sam local start-api

# Invoke a specific Lambda function
echo '{"body": "{\"days\": 3}"}' | sam local invoke SuggestMenuFunction
sam local invoke GetRecipesFunction
```

### Data Management

```bash
# Seed sample data (requires boto3 installed)
python scripts/seed_data.py --recipes 20 --history 30
```

### Python Environment

The project uses a Python virtual environment:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies for a specific function
pip install -r src/suggest_menu/requirements.txt
```

## Architecture

### Lambda Functions and Their Responsibilities

1. **SuggestMenuFunction** (`src/suggest_menu/app.py`)
   - Generates AI-powered meal plans for 3 or 7 days
   - Fetches all recipes from DynamoDB (Scan operation)
   - Fetches recent 30-day menu history to avoid repetition
   - Constructs prompts with recipe constraints and nutritional guidelines
   - Calls Amazon Bedrock Claude Sonnet 4.5 for generation
   - Handles JSON extraction from Bedrock responses (including code blocks)

2. **GetRecipesFunction** (`src/get_recipes/app.py`)
   - Retrieves all recipes or filters by category
   - Simple Scan operation with optional filtering

3. **CreateRecipeFunction** (`src/create_recipe/app.py`)
   - Creates new recipes with validation
   - Generates UUIDs for recipe IDs
   - Adds timestamps

4. **SaveHistoryFunction** (`src/save_history/app.py`)
   - Handles both POST (save) and GET (retrieve) for menu history
   - POST: Validates date format (YYYY-MM-DD), meal structure (breakfast/lunch/dinner arrays)
   - POST: Extracts recipe_ids from meal arrays and stores flat list in `recipes` field
   - GET: Supports `?days=N` query parameter (1-365, default 30)
   - Uses `safe_int_conversion()` utility for integer validation

### Shared Lambda Layer (`src/layers/common/python/utils.py`)

To reduce code duplication, a shared Lambda Layer is used. It provides common utilities to all functions. Key components include:
- **AWS Clients**: `dynamodb` and `bedrock` clients are initialized once and imported.
- **`create_response(status_code, body)`**: A helper to generate standardized API Gateway JSON responses.
- **`decimal_to_float(obj)`**: Recursively converts DynamoDB `Decimal` objects to Python `float` or `int`.

### Data Flow for Menu Suggestion
1. Client POSTs to `/suggest` with `{"days": 3 or 7}`
2. Lambda fetches all recipes (DynamoDB Scan on `kondate-recipes`)
3. Lambda fetches recent 30-day history (individual GetItem calls on `kondate-menu-history`)
4. Lambda builds structured prompt with:
   - Available recipes list (id, name, category, cooking time)
   - Recent recipe IDs to avoid repetition
   - Meal composition rules (breakfast: 1-2 items, lunch: 1-3 items, dinner: 2-3 items)
   - Nutritional balance constraints
5. Bedrock returns JSON with nested structure: `menu_plan[].meals.{breakfast,lunch,dinner}[]`
6. Lambda extracts JSON (handling markdown code blocks) and returns to client

### DynamoDB Schema

**kondate-recipes** (PK: recipe_id)
- `name`, `category`, `cooking_time`, `ingredients[]`, `recipe_url`, `tags[]`, `created_at`, `updated_at`

**kondate-menu-history** (PK: date as YYYY-MM-DD)
- `meals` (Map): `{breakfast: [{recipe_id, name}], lunch: [...], dinner: [...]}`
- `recipes[]`: Flat list of all recipe_ids used in that day
- `notes`, `created_at`, `updated_at`

Note: Both `SaveHistoryFunction` and `GetHistoryFunction` use the same handler (`src/save_history/app.py`) that branches on HTTP method.

## Critical Implementation Details

### Amazon Bedrock Configuration

**Model ID**: `jp.anthropic.claude-sonnet-4-5-20250929-v1:0` (Inference Profile)

**IMPORTANT**: Claude Sonnet 4.5 MUST be accessed via Inference Profile, not direct model ID. The Inference Profile routes requests across multiple regions (ap-northeast-1 and ap-northeast-3), so IAM permissions must include:
- The Inference Profile ARN in the deployment region
- Foundation model ARNs in BOTH ap-northeast-1 AND ap-northeast-3

Incorrect model IDs will fail with "The provided model identifier is invalid" or "Invocation of model ID with on-demand throughput isn't supported".

### JSON Parsing from Bedrock

Bedrock responses may contain JSON wrapped in markdown code blocks. The `call_bedrock()` function in `src/suggest_menu/app.py` handles this by:
1. Checking for ` ```json` markers and extracting content
2. Falling back to generic ` ``` ` markers
3. Using try-except with detailed error logging for JSONDecodeError

### Date and Integer Validation

Use the `safe_int_conversion()` utility for validating integer inputs like `days` query parameters. It provides:
- Type conversion with clear error messages
- Range validation (min/max)
- Default value handling

Date validation requires exact `YYYY-MM-DD` format (see `validate_date_format()`).

### Decimal Handling

DynamoDB returns numeric values as `Decimal` objects. Use the `decimal_to_float()` helper, now centralized in the shared Lambda Layer, to recursively convert Decimals to int/float before JSON serialization.

## Testing Considerations

When testing Lambda functions:
- All functions expect API Gateway HTTP API event format
- Body is always stringified JSON in `event['body']`
- Query parameters in `event['queryStringParameters']`
- HTTP method in `event['requestContext']['http']['method']`

Local testing requires DynamoDB tables to exist (either AWS or DynamoDB Local on port 8000).

## Common Pitfalls

1. **Bedrock Permissions**: Remember to grant permissions to BOTH the Inference Profile and the foundation models in multiple regions
2. **Menu History Structure**: The `meals` field contains nested arrays - each meal type (breakfast/lunch/dinner) is an array of recipe objects, not a single recipe
3. **Date Format**: History dates are stored as strings in `YYYY-MM-DD` format (not ISO8601 timestamps)
4. **Scan Operations**: Both recipes and history use Scan operations, which may need pagination for large datasets (not currently implemented)
