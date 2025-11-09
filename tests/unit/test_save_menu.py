"""Unit tests for save_menu action (src/agent_actions/save_menu/app.py)."""

import json

import pytest


class TestSaveMenuAction:
    """Test cases for save_menu Lambda handler."""

    def test_save_menu_success(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test successfully saving a new menu."""
        event = bedrock_agent_event.copy()
        event["actionGroup"] = "SaveMenu"
        event["apiPath"] = "/menu"
        event["httpMethod"] = "POST"
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-10"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [
                                        {"recipe_id": "recipe_001", "name": "味噌汁"}
                                    ],
                                    "lunch": [
                                        {
                                            "recipe_id": "recipe_004",
                                            "name": "カレーライス",
                                        }
                                    ],
                                    "dinner": [
                                        {
                                            "recipe_id": "recipe_002",
                                            "name": "鮭の塩焼き",
                                        }
                                    ],
                                }
                            ),
                        },
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        assert response["messageVersion"] == "1.0"
        assert response["response"]["httpStatusCode"] == 200

        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is True
        assert body["date"] == "2025-11-10"
        assert "successfully" in body["message"].lower()

    def test_save_menu_with_notes(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test saving a menu with notes."""
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-11"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [
                                        {"recipe_id": "recipe_001", "name": "味噌汁"}
                                    ]
                                }
                            ),
                        },
                        {
                            "name": "notes",
                            "type": "string",
                            "value": "健康的な献立",
                        },
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)
        assert response["response"]["httpStatusCode"] == 200

    def test_save_menu_duplicate_without_overwrite(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test saving a menu for a date that already exists (without overwrite)."""
        # Try to save menu for 2025-11-08 which already exists in fixtures
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-08"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [
                                        {"recipe_id": "recipe_001", "name": "味噌汁"}
                                    ]
                                }
                            ),
                        },
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        # Should return 409 conflict
        assert response["response"]["httpStatusCode"] == 409
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is False
        assert body["error"] == "duplicate_date"
        assert "existing_menu" in body

    def test_save_menu_duplicate_with_overwrite(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test overwriting an existing menu."""
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-08"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [
                                        {"recipe_id": "recipe_001", "name": "味噌汁"}
                                    ]
                                }
                            ),
                        },
                        {"name": "overwrite", "type": "boolean", "value": "true"},
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        assert response["response"]["httpStatusCode"] == 200
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is True
        assert body["overwritten"] is True

    def test_save_menu_invalid_date_format(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test validation error with invalid date format."""
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "11/10/2025"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps({"breakfast": []}),
                        },
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        assert response["response"]["httpStatusCode"] == 400
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is False
        assert "YYYY-MM-DD" in body["error"]

    def test_save_menu_missing_date(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test validation error when date is missing."""
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps({"breakfast": []}),
                        }
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        assert response["response"]["httpStatusCode"] == 400
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is False
        assert "date is required" in body["error"]

    def test_save_menu_missing_meals(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test validation error when meals is missing."""
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-10"}
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        assert response["response"]["httpStatusCode"] == 400
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is False
        assert "meals is required" in body["error"]

    def test_save_menu_bedrock_python_dict_format(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test parsing meals parameter in Bedrock Python dict format."""
        # Simulate Bedrock Agent sending Python dict format instead of JSON
        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-12"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": "{breakfast=[{recipe_id=recipe_001, name=味噌汁}], lunch=[{recipe_id=recipe_004, name=カレー}]}",
                        },
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)

        # Should successfully parse and save
        assert response["response"]["httpStatusCode"] == 200
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert body["success"] is True

    def test_save_menu_recipe_id_extraction(
        self, mock_dynamodb_tables, bedrock_agent_event, save_menu_handler
    ):
        """Test that recipe_ids are extracted into flat list."""
        import boto3

        event = bedrock_agent_event.copy()
        event["requestBody"] = {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "date", "type": "string", "value": "2025-11-13"},
                        {
                            "name": "meals",
                            "type": "object",
                            "value": json.dumps(
                                {
                                    "breakfast": [
                                        {"recipe_id": "recipe_001", "name": "味噌汁"}
                                    ],
                                    "lunch": [
                                        {"recipe_id": "recipe_002", "name": "鮭"}
                                    ],
                                    "dinner": [
                                        {"recipe_id": "recipe_003", "name": "おひたし"},
                                        {"recipe_id": "recipe_004", "name": "カレー"},
                                    ],
                                }
                            ),
                        },
                    ]
                }
            }
        }

        response = save_menu_handler(event, None)
        assert response["response"]["httpStatusCode"] == 200

        # Verify the saved item has recipe_ids in flat list
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.Table("test-history-table")
        saved_item = table.get_item(Key={"date": "2025-11-13"})["Item"]
        assert len(saved_item["recipes"]) == 4
        assert "recipe_001" in saved_item["recipes"]
        assert "recipe_004" in saved_item["recipes"]

    def test_save_menu_error_handling(
        self, mock_env_vars, bedrock_agent_event, save_menu_handler
    ):
        """Test error handling when DynamoDB operation fails."""
        from moto import mock_aws

        with mock_aws():
            # Don't create the table
            event = bedrock_agent_event.copy()
            event["requestBody"] = {
                "content": {
                    "application/json": {
                        "properties": [
                            {"name": "date", "type": "string", "value": "2025-11-10"},
                            {
                                "name": "meals",
                                "type": "object",
                                "value": json.dumps({"breakfast": []}),
                            },
                        ]
                    }
                }
            }

            response = save_menu_handler(event, None)

            # Should return error response
            assert response["response"]["httpStatusCode"] == 500
            body_str = response["response"]["responseBody"]["application/json"]["body"]
            body = json.loads(body_str)
            assert body["success"] is False
            assert "error" in body
