# Scripts

Utility scripts for managing the Kondate Planner application.

## Available Scripts

### `seed_data.py`
Generates and inserts sample/test data into DynamoDB tables.

```bash
python scripts/seed_data.py --recipes 20 --history 30
```

**Options**:
- `--recipes N`: Number of sample recipes to generate (default: 20)
- `--history N`: Number of days of meal history to generate (default: 30)

---

### `migrate_from_notion.py`
Migrates recipe and meal plan data from Notion data sources to DynamoDB.

```bash
python scripts/migrate_from_notion.py
```

**Prerequisites**:
1. Copy `.env.example` to `.env.local`
2. Set environment variables:
   - `NOTION_API_KEY`: Your Notion integration token
   - `NOTION_RECIPES_DB_ID`: Notion recipes data source ID
   - `NOTION_HISTORY_DB_ID`: Notion meal plan data source ID

**Expected Notion structure**:
- **Recipes**: `Name` (title), `分類` (select), `材料` (multi_select), `URL` (url)
- **Meal Plans**: `Date` (date), `meal` (select), `recipes` (relation), `memo` (title)

---

### `deploy_and_update_agent.sh`
Automated deployment script that builds, deploys, and updates the Bedrock Agent.

```bash
./scripts/deploy_and_update_agent.sh
```

**What it does**:
1. Runs `sam build`
2. Runs `sam deploy`
3. Prepares the Bedrock Agent (creates new version)
4. Updates the agent alias to point to latest version

---

## Configuration Files

### `.env.example`
Template for environment variables.

### `.env.local` (gitignored)
Your actual Notion API credentials. Copy from `.env.example` and fill in:

```bash
cp scripts/.env.example scripts/.env.local
```

### `requirements.txt`
Python dependencies for scripts:
- `boto3>=1.34.0` - AWS SDK for Python
- `notion-client>=2.2.1` - Notion API client
- `python-dotenv>=1.0.0` - Environment variable management

Install with:
```bash
pip install -r scripts/requirements.txt
```
