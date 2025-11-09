"""Shared pytest fixtures for all tests."""

import json
import os
import sys
from pathlib import Path
from decimal import Decimal

import pytest
from moto import mock_aws

# Add src/layers/common to Python path so tests can import utils
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "layers" / "common"))


# Helper function to import action handlers dynamically
def import_action_handler(action_name):
    """Import lambda_handler from specific action directory."""
    action_path = Path(__file__).parent.parent / "src" / "agent_actions" / action_name
    sys.path.insert(0, str(action_path))
    try:
        import app

        # Force reload to get the correct module
        import importlib

        importlib.reload(app)
        return app.lambda_handler
    finally:
        # Remove the path after import to avoid conflicts
        sys.path.remove(str(action_path))


@pytest.fixture
def get_recipes_handler():
    """Get the get_recipes lambda handler."""
    return import_action_handler("get_recipes")


@pytest.fixture
def get_history_handler():
    """Get the get_history lambda handler."""
    return import_action_handler("get_history")


@pytest.fixture
def save_menu_handler():
    """Get the save_menu lambda handler."""
    return import_action_handler("save_menu")


@pytest.fixture
def sample_recipes():
    """Load sample recipes from fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "sample_recipes.json", "r", encoding="utf-8") as f:
        recipes = json.load(f)
    # Convert numeric values to Decimal to match DynamoDB behavior
    return [convert_to_decimal(recipe) for recipe in recipes]


@pytest.fixture
def sample_history():
    """Load sample history from fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "sample_history.json", "r", encoding="utf-8") as f:
        history = json.load(f)
    # Convert numeric values to Decimal to match DynamoDB behavior
    return [convert_to_decimal(item) for item in history]


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables."""
    env = {
        "RECIPES_TABLE": "test-recipes-table",
        "HISTORY_TABLE": "test-history-table",
        "AWS_DEFAULT_REGION": "ap-northeast-1",
    }
    for key, value in env.items():
        os.environ[key] = value
    yield env
    # Cleanup
    for key in env:
        os.environ.pop(key, None)


@pytest.fixture
def mock_dynamodb_tables(mock_env_vars, sample_recipes, sample_history):
    """Create mock DynamoDB tables with sample data."""
    with mock_aws():
        import boto3

        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")

        # Create recipes table
        recipes_table = dynamodb.create_table(
            TableName=mock_env_vars["RECIPES_TABLE"],
            KeySchema=[{"AttributeName": "recipe_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "recipe_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create history table
        history_table = dynamodb.create_table(
            TableName=mock_env_vars["HISTORY_TABLE"],
            KeySchema=[{"AttributeName": "date", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "date", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Populate recipes table
        for recipe in sample_recipes:
            recipes_table.put_item(Item=recipe)

        # Populate history table
        for history_item in sample_history:
            history_table.put_item(Item=history_item)

        yield {
            "recipes_table": recipes_table,
            "history_table": history_table,
            "dynamodb": dynamodb,
        }


@pytest.fixture
def bedrock_agent_event():
    """Create a sample Bedrock Agent event."""
    return {
        "messageVersion": "1.0",
        "agent": {
            "name": "kondate-planner-agent",
            "id": "test-agent-id",
            "alias": "production",
            "version": "1",
        },
        "sessionId": "test-session-id",
        "sessionAttributes": {},
        "promptSessionAttributes": {},
        "actionGroup": "GetRecipes",
        "apiPath": "/recipes",
        "httpMethod": "GET",
        "parameters": [],
    }


def convert_to_decimal(obj):
    """Recursively convert floats/ints to Decimal to match DynamoDB behavior."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int):
        return Decimal(obj)
    if isinstance(obj, dict):
        return {k: convert_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_decimal(item) for item in obj]
    return obj
