"""Integration tests for DynamoDB interactions across all actions."""
import json
from datetime import datetime

import pytest


class TestDynamoDBIntegration:
    """Integration tests for DynamoDB operations."""

    def test_full_workflow_recipes_to_menu(
        self, mock_dynamodb_tables, bedrock_agent_event
    ):
        """Test full workflow: get recipes, create menu, get history."""
        from src.agent_actions.get_recipes import app as get_recipes_app
        from src.agent_actions.save_menu import app as save_menu_app
        from src.agent_actions.get_history import app as get_history_app

        # Step 1: Get available recipes
        get_recipes_event = bedrock_agent_event.copy()
        get_recipes_event["actionGroup"] = "GetRecipes"
        recipes_response = get_recipes_app.lambda_handler(get_recipes_event, None)
        assert recipes_response["response"]["httpStatusCode"] == 200

        recipes_body = json.loads(
            recipes_response["response"]["responseBody"]["application/json"]["body"]
        )
        assert len(recipes_body["recipes"]) > 0

        # Step 2: Create a menu using some recipes
        save_menu_event = bedrock_agent_event.copy()
        save_menu_event["actionGroup"] = "SaveMenu"
        save_menu_event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {
                            "name": "date",
                            "type": "string",
                            "value": datetime.now().strftime("%Y-%m-%d"),
                        },
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [
                                        {
                                            "recipe_id": recipes_body["recipes"][0][
                                                "recipe_id"
                                            ],
                                            "name": recipes_body["recipes"][0]["name"],
                                        }
                                    ],
                                    "lunch": [
                                        {
                                            "recipe_id": recipes_body["recipes"][1][
                                                "recipe_id"
                                            ],
                                            "name": recipes_body["recipes"][1]["name"],
                                        }
                                    ],
                                }
                            ),
                        },
                    ]
                }
            }
        }
        save_response = save_menu_app.lambda_handler(save_menu_event, None)
        assert save_response["response"]["httpStatusCode"] == 200

        # Step 3: Retrieve history and verify the saved menu appears
        get_history_event = bedrock_agent_event.copy()
        get_history_event["actionGroup"] = "GetHistory"
        get_history_event["parameters"] = [
            {"name": "days", "type": "integer", "value": "1"}
        ]
        history_response = get_history_app.lambda_handler(get_history_event, None)
        assert history_response["response"]["httpStatusCode"] == 200

        history_body = json.loads(
            history_response["response"]["responseBody"]["application/json"]["body"]
        )
        # Should find today's menu
        assert len(history_body["history"]) >= 1
        today_menu = next(
            (
                h
                for h in history_body["history"]
                if h["date"] == datetime.now().strftime("%Y-%m-%d")
            ),
            None,
        )
        assert today_menu is not None
        assert "breakfast" in today_menu["meals"]
        assert "lunch" in today_menu["meals"]

    def test_recipe_filtering_and_menu_creation(
        self, mock_dynamodb_tables, bedrock_agent_event
    ):
        """Test filtering recipes by category and using them in menu."""
        from src.agent_actions.get_recipes import app as get_recipes_app
        from src.agent_actions.save_menu import app as save_menu_app

        # Get only 主菜 recipes
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "category", "type": "string", "value": "主菜"}]
        recipes_response = get_recipes_app.lambda_handler(event, None)
        recipes_body = json.loads(
            recipes_response["response"]["responseBody"]["application/json"]["body"]
        )

        main_dishes = recipes_body["recipes"]
        assert len(main_dishes) > 0
        assert all(r["category"] == "主菜" for r in main_dishes)

        # Create menu using a main dish
        save_event = bedrock_agent_event.copy()
        save_event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-15"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "dinner": [
                                        {
                                            "recipe_id": main_dishes[0]["recipe_id"],
                                            "name": main_dishes[0]["name"],
                                        }
                                    ]
                                }
                            ),
                        },
                    ]
                }
            }
        }
        save_response = save_menu_app.lambda_handler(save_event, None)
        assert save_response["response"]["httpStatusCode"] == 200

    def test_history_shows_recent_menus(
        self, mock_dynamodb_tables, bedrock_agent_event
    ):
        """Test that history retrieves menus from fixture data."""
        from src.agent_actions.get_history import app as get_history_app

        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "30"}]

        response = get_history_app.lambda_handler(event, None)
        body = json.loads(
            response["response"]["responseBody"]["application/json"]["body"]
        )

        # Should find the 2 menus from sample_history.json
        assert len(body["history"]) == 2
        dates = [h["date"] for h in body["history"]]
        assert "2025-11-08" in dates
        assert "2025-11-07" in dates

    def test_overwrite_existing_menu(self, mock_dynamodb_tables, bedrock_agent_event):
        """Test overwriting an existing menu entry."""
        from src.agent_actions.save_menu import app as save_menu_app
        from src.agent_actions.get_history import app as get_history_app

        # First attempt: should fail without overwrite flag
        save_event = bedrock_agent_event.copy()
        save_event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-08"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {"breakfast": [{"recipe_id": "new_001", "name": "新しい"}]}
                            ),
                        },
                    ]
                }
            }
        }
        response1 = save_menu_app.lambda_handler(save_event, None)
        assert response1["response"]["httpStatusCode"] == 409

        # Second attempt: with overwrite flag
        save_event["requestBody"]["content"]["application/json"]["properties"].append(
            {"name": "overwrite", "type": "boolean", "value": "true"}
        )
        response2 = save_menu_app.lambda_handler(save_event, None)
        assert response2["response"]["httpStatusCode"] == 200

        body = json.loads(
            response2["response"]["responseBody"]["application/json"]["body"]
        )
        assert body["overwritten"] is True

    def test_empty_meals_in_history(self, mock_dynamodb_tables, bedrock_agent_event):
        """Test saving and retrieving menu with empty meal slots."""
        from src.agent_actions.save_menu import app as save_menu_app
        from src.agent_actions.get_history import app as get_history_app

        # Save menu with only lunch
        save_event = bedrock_agent_event.copy()
        save_event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-16"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [],
                                    "lunch": [
                                        {"recipe_id": "recipe_001", "name": "味噌汁"}
                                    ],
                                    "dinner": [],
                                }
                            ),
                        },
                    ]
                }
            }
        }
        save_response = save_menu_app.lambda_handler(save_event, None)
        assert save_response["response"]["httpStatusCode"] == 200

        # Retrieve and verify
        get_history_event = bedrock_agent_event.copy()
        get_history_event["parameters"] = [
            {"name": "days", "type": "integer", "value": "1"}
        ]
        history_response = get_history_app.lambda_handler(get_history_event, None)
        history_body = json.loads(
            history_response["response"]["responseBody"]["application/json"]["body"]
        )

        # Find our saved menu
        menu = next(
            (h for h in history_body["history"] if h["date"] == "2025-11-16"), None
        )
        assert menu is not None
        assert menu["meals"]["lunch"][0]["recipe_id"] == "recipe_001"
