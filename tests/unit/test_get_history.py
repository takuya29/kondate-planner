"""Unit tests for get_history action (src/agent_actions/get_history/app.py)."""

import json


class TestGetHistoryAction:
    """Test cases for get_history Lambda handler."""

    def test_get_history_default_days(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test fetching history with default days (30)."""
        event = bedrock_agent_event.copy()
        event["actionGroup"] = "GetHistory"
        event["apiPath"] = "/history"
        event["parameters"] = []

        response = get_history_handler(event, None)

        assert response["messageVersion"] == "1.0"
        assert response["response"]["httpStatusCode"] == 200

        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert "history" in body
        # Should return the 2 history items from sample_history.json
        assert len(body["history"]) == 2

    def test_get_history_custom_days(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test fetching history with custom number of days."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "7"}]

        response = get_history_handler(event, None)

        assert response["response"]["httpStatusCode"] == 200
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        # With 7 days and only 2 items in fixtures, should return 2
        assert len(body["history"]) <= 7

    def test_get_history_sorted_by_date(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test that history is sorted by date (most recent first)."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "30"}]

        response = get_history_handler(event, None)
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)

        if len(body["history"]) > 1:
            dates = [item["date"] for item in body["history"]]
            # Check that dates are in descending order
            assert dates == sorted(dates, reverse=True)

    def test_get_history_invalid_days_string(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test validation error with invalid days parameter (string)."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "invalid"}]

        response = get_history_handler(event, None)

        # Should return 400 error
        assert response["response"]["httpStatusCode"] == 400
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert "error" in body
        assert "must be an integer" in body["error"]

    def test_get_history_days_below_minimum(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test validation error with days below minimum (0)."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "0"}]

        response = get_history_handler(event, None)

        assert response["response"]["httpStatusCode"] == 400
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert "error" in body
        assert "at least 1" in body["error"]

    def test_get_history_days_above_maximum(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test validation error with days above maximum (366)."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "366"}]

        response = get_history_handler(event, None)

        assert response["response"]["httpStatusCode"] == 400
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        assert "error" in body
        assert "at most 365" in body["error"]

    def test_get_history_one_day(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test fetching history for 1 day."""
        event = bedrock_agent_event.copy()
        event["parameters"] = [{"name": "days", "type": "integer", "value": "1"}]

        response = get_history_handler(event, None)

        assert response["response"]["httpStatusCode"] == 200
        body_str = response["response"]["responseBody"]["application/json"]["body"]
        body = json.loads(body_str)
        # Should check today only
        assert len(body["history"]) <= 1

    def test_get_history_empty_table(
        self, mock_env_vars, bedrock_agent_event, get_history_handler
    ):
        """Test fetching history from an empty table."""
        from moto import mock_aws
        import boto3

        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
            dynamodb.create_table(
                TableName=mock_env_vars["HISTORY_TABLE"],
                KeySchema=[{"AttributeName": "date", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "date", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            event = bedrock_agent_event.copy()
            response = get_history_handler(event, None)

            body_str = response["response"]["responseBody"]["application/json"]["body"]
            body = json.loads(body_str)
            assert body["history"] == []

    def test_get_history_decimal_conversion(
        self, mock_dynamodb_tables, bedrock_agent_event, get_history_handler
    ):
        """Test that Decimal values are properly converted."""
        event = bedrock_agent_event.copy()
        response = get_history_handler(event, None)

        body_str = response["response"]["responseBody"]["application/json"]["body"]
        # Should not raise error when converting to JSON
        body = json.loads(body_str)
        assert isinstance(body["history"], list)

    def test_get_history_error_handling(
        self, mock_env_vars, bedrock_agent_event, get_history_handler
    ):
        """Test error handling when DynamoDB operation fails."""
        from moto import mock_aws

        with mock_aws():
            # Don't create the table
            event = bedrock_agent_event.copy()
            response = get_history_handler(event, None)

            # Should return error response
            assert response["response"]["httpStatusCode"] == 500
            body_str = response["response"]["responseBody"]["application/json"]["body"]
            body = json.loads(body_str)
            assert "error" in body
