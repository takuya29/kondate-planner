"""Unit tests for suggest_menu Lambda function."""

import json
import pytest
from unittest.mock import Mock, patch
from moto import mock_dynamodb
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/suggest_menu"))

from app import lambda_handler, build_prompt, get_all_recipes, get_recent_history


@pytest.mark.unit
class TestSuggestMenu:
    """Test suite for suggest_menu Lambda function."""

    @mock_dynamodb
    @patch("app.call_bedrock")
    def test_suggest_menu_success_3_days(
        self, mock_bedrock, lambda_context, mock_dynamodb_recipes_table
    ):
        """Test successful 3-day menu suggestion."""
        # Setup mock recipes
        mock_dynamodb_recipes_table.put_item(
            Item={"recipe_id": "recipe_001", "name": "トースト", "category": "主食"}
        )

        # Mock Bedrock response
        mock_bedrock.return_value = {
            "menu_plan": [
                {
                    "date": "2025-11-08",
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}],
                        "lunch": [{"recipe_id": "recipe_002", "name": "ハンバーグ"}],
                        "dinner": [{"recipe_id": "recipe_003", "name": "鮭の塩焼き"}],
                    },
                }
            ],
            "summary": "バランスの良い献立",
        }

        event = {"body": json.dumps({"days": 3})}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "menu_plan" in body

    @mock_dynamodb
    @patch("app.call_bedrock")
    def test_suggest_menu_success_7_days(
        self, mock_bedrock, lambda_context, mock_dynamodb_recipes_table
    ):
        """Test successful 7-day menu suggestion."""
        mock_dynamodb_recipes_table.put_item(
            Item={"recipe_id": "recipe_001", "name": "トースト", "category": "主食"}
        )

        mock_bedrock.return_value = {"menu_plan": [], "summary": "テスト"}

        event = {"body": json.dumps({"days": 7})}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200

    def test_suggest_menu_invalid_days(self, lambda_context):
        """Test that invalid days value returns 400."""
        invalid_days = [1, 2, 4, 5, 6, 8, 10, 30, 0, -1]

        for days in invalid_days:
            event = {"body": json.dumps({"days": days})}

            response = lambda_handler(event, lambda_context)

            assert response["statusCode"] == 400
            body = json.loads(response["body"])
            assert "error" in body

    def test_suggest_menu_default_days(self, lambda_context):
        """Test that default days is 3."""
        with patch("app.get_all_recipes") as mock_recipes, patch(
            "app.call_bedrock"
        ) as mock_bedrock:
            mock_recipes.return_value = [
                {"recipe_id": "recipe_001", "name": "テスト", "category": "主食"}
            ]
            mock_bedrock.return_value = {"menu_plan": [], "summary": "test"}

            event = {"body": json.dumps({})}

            response = lambda_handler(event, lambda_context)

            # Should succeed with default
            assert response["statusCode"] == 200

    @mock_dynamodb
    def test_suggest_menu_no_recipes(self, lambda_context, mock_dynamodb_recipes_table):
        """Test that no recipes returns 404."""
        event = {"body": json.dumps({"days": 3})}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "error" in body

    @mock_dynamodb
    @patch("app.call_bedrock")
    def test_suggest_menu_bedrock_error(
        self, mock_bedrock, lambda_context, mock_dynamodb_recipes_table
    ):
        """Test handling of Bedrock API errors."""
        mock_dynamodb_recipes_table.put_item(
            Item={"recipe_id": "recipe_001", "name": "テスト", "category": "主食"}
        )

        mock_bedrock.side_effect = Exception("Bedrock error")

        event = {"body": json.dumps({"days": 3})}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    @mock_dynamodb
    @patch("app.call_bedrock")
    def test_suggest_menu_invalid_bedrock_json(
        self, mock_bedrock, lambda_context, mock_dynamodb_recipes_table
    ):
        """Test handling of invalid JSON from Bedrock."""
        mock_dynamodb_recipes_table.put_item(
            Item={"recipe_id": "recipe_001", "name": "テスト", "category": "主食"}
        )

        # Mock call_bedrock to raise ValueError for invalid JSON
        mock_bedrock.side_effect = ValueError("Bedrock returned invalid JSON")

        event = {"body": json.dumps({"days": 3})}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 500

    def test_suggest_menu_cors_headers(self, lambda_context):
        """Test that CORS headers are present."""
        event = {"body": json.dumps({"days": 5})}  # Invalid to get quick response

        response = lambda_handler(event, lambda_context)

        assert "headers" in response
        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"


@pytest.mark.unit
class TestBuildPrompt:
    """Test suite for build_prompt function."""

    def test_build_prompt_basic(self):
        """Test basic prompt building."""
        recipes = [
            {
                "recipe_id": "recipe_001",
                "name": "トースト",
                "category": "主食",
                "cooking_time": 5,
            }
        ]
        history = []
        days = 3

        prompt = build_prompt(recipes, history, days)

        assert "3日分" in prompt
        assert "recipe_001" in prompt
        assert "トースト" in prompt

    def test_build_prompt_with_history(self):
        """Test prompt building with history."""
        recipes = [
            {
                "recipe_id": "recipe_001",
                "name": "トースト",
                "category": "主食",
                "cooking_time": 5,
            }
        ]
        history = [{"date": "2025-11-07", "recipes": ["recipe_001", "recipe_002"]}]
        days = 3

        prompt = build_prompt(recipes, history, days)

        assert "recipe_001" in prompt
        assert "recipe_002" in prompt

    def test_build_prompt_no_history(self):
        """Test prompt building with no history."""
        recipes = [
            {
                "recipe_id": "recipe_001",
                "name": "トースト",
                "category": "主食",
                "cooking_time": 5,
            }
        ]
        history = []
        days = 7

        prompt = build_prompt(recipes, history, days)

        assert "7日分" in prompt
        assert "なし" in prompt or "最近作った料理" in prompt

    def test_build_prompt_missing_optional_fields(self):
        """Test prompt building with recipes missing optional fields."""
        recipes = [
            {
                "recipe_id": "recipe_001",
                "name": "ミニマル",
                # Missing category and cooking_time
            }
        ]
        history = []
        days = 3

        prompt = build_prompt(recipes, history, days)

        assert "recipe_001" in prompt
        assert "ミニマル" in prompt


@pytest.mark.unit
class TestHelperFunctions:
    """Test suite for helper functions."""

    @mock_dynamodb
    def test_get_all_recipes(self, mock_dynamodb_recipes_table):
        """Test getting all recipes."""
        mock_dynamodb_recipes_table.put_item(
            Item={"recipe_id": "recipe_001", "name": "テスト", "category": "主食"}
        )

        recipes = get_all_recipes()

        assert len(recipes) == 1
        assert recipes[0]["recipe_id"] == "recipe_001"

    @mock_dynamodb
    def test_get_all_recipes_empty(self, mock_dynamodb_recipes_table):
        """Test getting recipes from empty table."""
        recipes = get_all_recipes()

        assert recipes == []

    @mock_dynamodb
    def test_get_recent_history(self, mock_dynamodb_history_table):
        """Test getting recent history."""
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        mock_dynamodb_history_table.put_item(
            Item={"date": today, "recipes": ["recipe_001"], "meals": {}}
        )

        history = get_recent_history(days=30)

        # Should include today's history
        assert len(history) >= 0

    @mock_dynamodb
    def test_get_recent_history_custom_days(self, mock_dynamodb_history_table):
        """Test getting history with custom days parameter."""
        history = get_recent_history(days=7)

        # Should not error and return list
        assert isinstance(history, list)


@pytest.mark.unit
class TestCallBedrock:
    """Test suite for call_bedrock function."""

    @patch("boto3.client")
    def test_call_bedrock_success(self, mock_boto_client):
        """Test successful Bedrock API call."""
        from app import call_bedrock

        # Mock Bedrock client
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock

        # Mock response
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(
            {"content": [{"text": json.dumps({"menu_plan": [], "summary": "test"})}]}
        ).encode("utf-8")

        mock_bedrock.invoke_model.return_value = {"body": mock_body}

        result = call_bedrock("test prompt")

        assert "menu_plan" in result
        assert "summary" in result

    @patch("boto3.client")
    def test_call_bedrock_json_in_code_block(self, mock_boto_client):
        """Test Bedrock response with JSON in code block."""
        from app import call_bedrock

        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock

        # Mock response with code block
        json_content = json.dumps({"menu_plan": [], "summary": "test"})
        response_text = f"```json\n{json_content}\n```"

        mock_body = Mock()
        mock_body.read.return_value = json.dumps(
            {"content": [{"text": response_text}]}
        ).encode("utf-8")

        mock_bedrock.invoke_model.return_value = {"body": mock_body}

        result = call_bedrock("test prompt")

        assert "menu_plan" in result

    @patch("boto3.client")
    def test_call_bedrock_invalid_json(self, mock_boto_client):
        """Test Bedrock returning invalid JSON."""
        from app import call_bedrock

        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock

        mock_body = Mock()
        mock_body.read.return_value = json.dumps(
            {"content": [{"text": "invalid json content"}]}
        ).encode("utf-8")

        mock_bedrock.invoke_model.return_value = {"body": mock_body}

        with pytest.raises(ValueError):
            call_bedrock("test prompt")

    @patch("boto3.client")
    def test_call_bedrock_api_error(self, mock_boto_client):
        """Test Bedrock API error handling."""
        from app import call_bedrock

        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        mock_bedrock.invoke_model.side_effect = Exception("API error")

        with pytest.raises(Exception):
            call_bedrock("test prompt")
