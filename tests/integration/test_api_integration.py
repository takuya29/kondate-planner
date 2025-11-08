"""Integration tests for API workflows."""

import json
import pytest
from moto import mock_aws
from datetime import datetime
import sys
import os

# Add src paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/create_recipe"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/get_recipes"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/save_history"))

from src.create_recipe.app import lambda_handler as create_recipe_handler
from src.get_recipes.app import lambda_handler as get_recipes_handler
from src.save_history.app import lambda_handler as save_history_handler


@pytest.mark.integration
@mock_aws
class TestRecipeWorkflow:
    """Integration tests for full recipe workflow."""

    def test_create_and_get_recipe_workflow(
        self, lambda_context, mock_dynamodb_recipes_table
    ):
        """Test creating a recipe and then retrieving it."""
        # Step 1: Create a recipe
        create_event = {
            "body": json.dumps(
                {
                    "name": "統合テストレシピ",
                    "category": "メイン",
                    "cooking_time": 25,
                    "ingredients": ["材料A", "材料B"],
                    "instructions": "調理手順",
                    "tags": ["テスト"],
                }
            )
        }

        create_response = create_recipe_handler(create_event, lambda_context)
        assert create_response["statusCode"] == 201

        created_recipe = json.loads(create_response["body"])["recipe"]
        recipe_id = created_recipe["recipe_id"]

        # Step 2: Get all recipes
        get_event = {"queryStringParameters": None}

        get_response = get_recipes_handler(get_event, lambda_context)
        assert get_response["statusCode"] == 200

        recipes = json.loads(get_response["body"])["recipes"]
        assert len(recipes) == 1
        assert recipes[0]["recipe_id"] == recipe_id
        assert recipes[0]["name"] == "統合テストレシピ"

    def test_create_multiple_recipes_and_filter(
        self, lambda_context, mock_dynamodb_recipes_table
    ):
        """Test creating multiple recipes and filtering by category."""
        # Create recipes in different categories
        categories = ["メイン", "副菜", "メイン"]
        recipe_ids = []

        for i, category in enumerate(categories):
            create_event = {
                "body": json.dumps({"name": f"レシピ{i}", "category": category})
            }

            response = create_recipe_handler(create_event, lambda_context)
            assert response["statusCode"] == 201
            recipe_ids.append(json.loads(response["body"])["recipe"]["recipe_id"])

        # Filter by 'メイン' category
        get_event = {"queryStringParameters": {"category": "メイン"}}

        response = get_recipes_handler(get_event, lambda_context)
        recipes = json.loads(response["body"])["recipes"]

        assert len(recipes) == 2
        for recipe in recipes:
            assert recipe["category"] == "メイン"


@pytest.mark.integration
@mock_aws
class TestHistoryWorkflow:
    """Integration tests for history workflow."""

    def test_save_and_get_history_workflow(
        self, lambda_context, mock_dynamodb_history_table
    ):
        """Test saving history and then retrieving it."""
        # Step 1: Save history
        save_event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": "2025-11-08",
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}],
                        "lunch": [{"recipe_id": "recipe_002", "name": "ハンバーグ"}],
                        "dinner": [{"recipe_id": "recipe_003", "name": "鮭の塩焼き"}],
                    },
                    "notes": "統合テスト",
                }
            ),
        }

        save_response = save_history_handler(save_event, lambda_context)
        assert save_response["statusCode"] == 201

        # Step 2: Get history
        get_event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "7"},
        }

        get_response = save_history_handler(get_event, lambda_context)
        assert get_response["statusCode"] == 200

        history = json.loads(get_response["body"])["history"]
        # Should find our saved history
        assert any(h["date"] == "2025-11-08" for h in history)

    def test_update_existing_history(self, lambda_context, mock_dynamodb_history_table):
        """Test updating history for an existing date."""
        date = "2025-11-08"

        # Save initial history
        save_event_1 = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": date,
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}]
                    },
                }
            ),
        }

        response_1 = save_history_handler(save_event_1, lambda_context)
        assert response_1["statusCode"] == 201

        # Update history for same date
        save_event_2 = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": date,
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_002", "name": "卵焼き"}],
                        "lunch": [{"recipe_id": "recipe_003", "name": "ハンバーグ"}],
                    },
                }
            ),
        }

        response_2 = save_history_handler(save_event_2, lambda_context)
        assert response_2["statusCode"] == 201

        # Get history and verify it was updated
        get_event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "1"},
        }

        get_response = save_history_handler(get_event, lambda_context)
        history = json.loads(get_response["body"])["history"]

        # Find the entry for our date
        date_entry = next((h for h in history if h["date"] == date), None)
        assert date_entry is not None
        # Should have the updated data
        assert "lunch" in date_entry["meals"]


@pytest.mark.integration
@pytest.mark.slow
class TestCompleteMenuPlanningWorkflow:
    """Integration test for complete menu planning workflow."""

    @mock_aws
    def test_full_workflow(
        self, lambda_context, mock_dynamodb_recipes_table, mock_dynamodb_history_table
    ):
        """Test the complete workflow: create recipes, save history, suggest menu."""
        # Step 1: Create multiple recipes
        recipes_data = [
            {"name": "トースト", "category": "主食", "cooking_time": 5},
            {"name": "卵焼き", "category": "副菜", "cooking_time": 10},
            {"name": "ハンバーグ", "category": "メイン", "cooking_time": 30},
            {"name": "味噌汁", "category": "汁物", "cooking_time": 10},
        ]

        created_recipes = []
        for recipe_data in recipes_data:
            create_event = {"body": json.dumps(recipe_data)}
            response = create_recipe_handler(create_event, lambda_context)
            assert response["statusCode"] == 201
            created_recipes.append(json.loads(response["body"])["recipe"])

        # Step 2: Verify recipes were created
        get_event = {"queryStringParameters": None}
        response = get_recipes_handler(get_event, lambda_context)
        assert response["statusCode"] == 200
        recipes = json.loads(response["body"])["recipes"]
        assert len(recipes) == len(recipes_data)

        # Step 3: Save some history
        today = datetime.now().strftime("%Y-%m-%d")
        save_event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": today,
                    "meals": {
                        "breakfast": [
                            {
                                "recipe_id": created_recipes[0]["recipe_id"],
                                "name": created_recipes[0]["name"],
                            }
                        ],
                        "lunch": [
                            {
                                "recipe_id": created_recipes[2]["recipe_id"],
                                "name": created_recipes[2]["name"],
                            }
                        ],
                        "dinner": [
                            {
                                "recipe_id": created_recipes[3]["recipe_id"],
                                "name": created_recipes[3]["name"],
                            }
                        ],
                    },
                }
            ),
        }

        response = save_history_handler(save_event, lambda_context)
        assert response["statusCode"] == 201

        # Step 4: Verify history was saved
        get_history_event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "1"},
        }

        response = save_history_handler(get_history_event, lambda_context)
        assert response["statusCode"] == 200
        history = json.loads(response["body"])["history"]
        assert len(history) > 0

        # Note: We don't test suggest_menu here as it requires mocking Bedrock
        # which is better done in unit tests
