"""Unit tests for get_recipes action (src/agent_actions/get_recipes/app.py)."""

import json


class TestGetRecipesAction:
    """Test cases for get_recipes Lambda handler."""

    def test_get_all_recipes(
        self, mock_dynamodb_tables, bedrock_agent_event, get_recipes_handler
    ):
        """Test fetching all recipes without category filter."""
        # Prepare event
        event = bedrock_agent_event.copy()
        event["actionGroup"] = "GetRecipes"
        event["apiPath"] = "/recipes"
        event["parameters"] = []

        # Execute
        response = get_recipes_handler(event, None)

        # Verify response structure
        assert response["messageVersion"] == "1.0"
        assert response["response"]["httpStatusCode"] == 200

        # Verify response body
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert "recipes" in body
        assert len(body["recipes"]) == 5  # All recipes from sample_recipes.json

        # Verify recipes are sorted by name
        recipe_names = [r["name"] for r in body["recipes"]]
        assert recipe_names == sorted(recipe_names)

    def test_get_recipes_by_category(
        self, mock_dynamodb_tables, bedrock_agent_event, get_recipes_handler
    ):
        """Test fetching recipes filtered by category."""
        # Prepare event
        event = bedrock_agent_event.copy()
        event["actionGroup"] = "GetRecipes"
        event["parameters"] = [{"name": "category", "type": "string", "value": "主菜"}]

        # Execute
        response = get_recipes_handler(event, None)

        # Verify response
        assert response["response"]["httpStatusCode"] == 200
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)

        # Should only have recipes in "主菜" category
        assert len(body["recipes"]) == 2  # 鮭の塩焼き and カレーライス
        for recipe in body["recipes"]:
            assert recipe["category"] == "主菜"

    def test_get_recipes_by_category_soup(
        self, mock_dynamodb_tables, bedrock_agent_event, get_recipes_handler
    ):
        """Test fetching recipes in 汁物 category."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "category", "type": "string", "value": "汁物"}]

        response = get_recipes_handler(event, None)
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)

        assert len(body["recipes"]) == 1
        assert body["recipes"][0]["name"] == "味噌汁"

    def test_get_recipes_nonexistent_category(
        self, mock_dynamodb_tables, bedrock_agent_event, get_recipes_handler
    ):
        """Test fetching recipes with a category that doesn't exist."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [
            {"name": "category", "type": "string", "value": "存在しないカテゴリ"}
        ]

        response = get_recipes_handler(event, None)
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)

        # Should return empty list
        assert len(body["recipes"]) == 0

    def test_get_recipes_empty_table(
        self, mock_env_vars, bedrock_agent_event, get_recipes_handler
    ):
        """Test fetching recipes from an empty table."""
        from moto import mock_aws
        import boto3

        with mock_aws():
            # Create empty table
            dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
            dynamodb.create_table(
                TableName=mock_env_vars["RECIPES_TABLE"],
                KeySchema=[{"AttributeName": "recipe_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "recipe_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            event = bedrock_agent_event.copy()
            response = get_recipes_handler(event, None)

            body_str = response["response"]["responseBody"]["application/json"]["body"]
            body = json.loads(body_str)
            assert body["recipes"] == []

    def test_get_recipes_decimal_conversion(
        self, mock_dynamodb_tables, bedrock_agent_event, get_recipes_handler
    ):
        """Test that Decimal values are properly converted to int/float."""
        event = bedrock_agent_event.copy()
        response = get_recipes_handler(event, None)

        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)

    def test_get_recipes_error_handling(
        self, mock_env_vars, bedrock_agent_event, get_recipes_handler
    ):
        """Test error handling when DynamoDB operation fails."""
        from moto import mock_aws

        with mock_aws():
            # Don't create the table, so scan will fail
            event = bedrock_agent_event.copy()
            response = get_recipes_handler(event, None)

            # Should return error response
            assert response["response"]["httpStatusCode"] == 500
            body_str = response["response"]["responseBody"]["application/json"]["body"]
            body = json.loads(body_str)
            assert "error" in body
            assert body["recipes"] == []
