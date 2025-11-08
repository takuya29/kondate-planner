"""Unit tests for save_history Lambda function."""

import json
import pytest
from moto import mock_aws
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/save_history"))

from app import lambda_handler, validate_date_format, safe_int_conversion


@pytest.mark.unit
class TestSaveHistory:
    """Test suite for save_history Lambda function (POST)."""

    @mock_aws
    def test_save_history_success(self, lambda_context, mock_dynamodb_history_table):
        """Test successful history save."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": "2025-11-08",
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}],
                        "lunch": [{"recipe_id": "recipe_002", "name": "ハンバーグ"}],
                        "dinner": [{"recipe_id": "recipe_003", "name": "鮭の塩焼き"}],
                    },
                }
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "message" in body
        assert "history" in body
        assert body["history"]["date"] == "2025-11-08"

    @mock_aws
    def test_save_history_with_notes(self, lambda_context, mock_dynamodb_history_table):
        """Test saving history with notes."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": "2025-11-08",
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}]
                    },
                    "notes": "テストメモ",
                }
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["history"]["notes"] == "テストメモ"

    def test_save_history_missing_date(self, lambda_context):
        """Test that missing date returns 400."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}]
                    }
                }
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "date" in body["error"]

    def test_save_history_missing_meals(self, lambda_context):
        """Test that missing meals returns 400."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"date": "2025-11-08"}),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "meals" in body["error"]

    def test_save_history_invalid_date_format(self, lambda_context):
        """Test that invalid date format returns 400."""
        invalid_dates = [
            "2025/11/08",  # Wrong separator
            "11-08-2025",  # Wrong order
            "2025-11-8",  # Missing leading zero
            "2025-13-01",  # Invalid month
            "2025-11-32",  # Invalid day
            "invalid",  # Completely wrong
            "",  # Empty
        ]

        for invalid_date in invalid_dates:
            event = {
                "requestContext": {"http": {"method": "POST"}},
                "body": json.dumps(
                    {
                        "date": invalid_date,
                        "meals": {
                            "breakfast": [
                                {"recipe_id": "recipe_001", "name": "トースト"}
                            ]
                        },
                    }
                ),
            }

            response = lambda_handler(event, lambda_context)
            assert response["statusCode"] == 400

    def test_save_history_empty_meal_array(self, lambda_context):
        """Test that empty meal arrays return 400."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {"date": "2025-11-08", "meals": {"breakfast": []}}  # Empty array
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_save_history_non_array_meals(self, lambda_context):
        """Test that non-array meals return 400."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {"date": "2025-11-08", "meals": {"breakfast": "not an array"}}
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_save_history_missing_recipe_id(self, lambda_context):
        """Test that recipes without recipe_id return 400."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": "2025-11-08",
                    "meals": {"breakfast": [{"name": "トースト"}]},  # Missing recipe_id
                }
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400

    def test_save_history_missing_recipe_name(self, lambda_context):
        """Test that recipes without name return 400."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": "2025-11-08",
                    "meals": {
                        "breakfast": [{"recipe_id": "recipe_001"}]  # Missing name
                    },
                }
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400

    @mock_aws
    def test_save_history_multiple_meals(
        self, lambda_context, mock_dynamodb_history_table
    ):
        """Test saving history with all three meal types."""
        event = {
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps(
                {
                    "date": "2025-11-08",
                    "meals": {
                        "breakfast": [
                            {"recipe_id": "recipe_001", "name": "トースト"},
                            {"recipe_id": "recipe_002", "name": "卵焼き"},
                        ],
                        "lunch": [{"recipe_id": "recipe_003", "name": "ハンバーグ"}],
                        "dinner": [
                            {"recipe_id": "recipe_004", "name": "鮭の塩焼き"},
                            {"recipe_id": "recipe_005", "name": "味噌汁"},
                        ],
                    },
                }
            ),
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        # Check that all recipe IDs are in the recipes array
        assert "recipe_001" in body["history"]["recipes"]
        assert "recipe_002" in body["history"]["recipes"]
        assert "recipe_003" in body["history"]["recipes"]
        assert "recipe_004" in body["history"]["recipes"]
        assert "recipe_005" in body["history"]["recipes"]


@pytest.mark.unit
class TestGetHistory:
    """Test suite for save_history Lambda function (GET)."""

    @mock_aws
    def test_get_history_success(self, lambda_context, mock_dynamodb_history_table):
        """Test successful history retrieval."""
        # Add some history data
        today = datetime.now().strftime("%Y-%m-%d")
        mock_dynamodb_history_table.put_item(
            Item={
                "date": today,
                "meals": {
                    "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}]
                },
                "recipes": ["recipe_001"],
            }
        )

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": None,
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "history" in body
        assert "count" in body

    @mock_aws
    def test_get_history_with_days_param(
        self, lambda_context, mock_dynamodb_history_table
    ):
        """Test getting history with days parameter."""
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "7"},
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200

    def test_get_history_invalid_days_non_numeric(self, lambda_context):
        """Test that non-numeric days returns 400."""
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "invalid"},
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400

    def test_get_history_invalid_days_too_small(self, lambda_context):
        """Test that days < 1 returns 400."""
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "0"},
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400

    def test_get_history_invalid_days_too_large(self, lambda_context):
        """Test that days > 365 returns 400."""
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"days": "366"},
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400

    def test_get_history_default_days(self, lambda_context):
        """Test that default days is 30."""
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": None,
        }

        # The function should not error with default
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 200

    def test_method_not_allowed(self, lambda_context):
        """Test that unsupported HTTP methods return 405."""
        event = {"requestContext": {"http": {"method": "DELETE"}}}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 405


@pytest.mark.unit
class TestHelperFunctions:
    """Test suite for helper functions."""

    def test_validate_date_format_valid(self):
        """Test valid date formats."""
        assert validate_date_format("2025-11-08") is True
        assert validate_date_format("2025-01-01") is True
        assert validate_date_format("2025-12-31") is True

    def test_validate_date_format_invalid(self):
        """Test invalid date formats."""
        assert validate_date_format("2025/11/08") is False
        assert validate_date_format("11-08-2025") is False
        assert validate_date_format("2025-13-01") is False
        assert validate_date_format("invalid") is False
        assert validate_date_format("") is False
        assert validate_date_format(None) is False

    def test_safe_int_conversion_success(self):
        """Test successful integer conversion."""
        assert safe_int_conversion("10", "test") == 10
        assert safe_int_conversion(10, "test") == 10
        assert safe_int_conversion("100", "test", min_value=1, max_value=200) == 100

    def test_safe_int_conversion_with_default(self):
        """Test integer conversion with default value."""
        assert safe_int_conversion(None, "test", default=30) == 30
        assert safe_int_conversion("", "test", default=30) == 30

    def test_safe_int_conversion_missing_no_default(self):
        """Test that missing value without default raises error."""
        with pytest.raises(ValueError):
            safe_int_conversion(None, "test")

    def test_safe_int_conversion_non_numeric(self):
        """Test that non-numeric value raises error."""
        with pytest.raises(ValueError):
            safe_int_conversion("invalid", "test")

    def test_safe_int_conversion_min_value(self):
        """Test min_value validation."""
        with pytest.raises(ValueError):
            safe_int_conversion("0", "test", min_value=1)

    def test_safe_int_conversion_max_value(self):
        """Test max_value validation."""
        with pytest.raises(ValueError):
            safe_int_conversion("100", "test", max_value=50)
