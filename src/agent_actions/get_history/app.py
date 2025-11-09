import os
import logging
import json
from datetime import datetime, timedelta

from utils import get_dynamodb, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_TABLE = os.environ["HISTORY_TABLE"]


def safe_int_conversion(
    value, field_name, min_value=None, max_value=None, default=None
):
    """Safely convert a value to an integer with validation."""
    if value is None or value == "":
        if default is not None:
            return default
        raise ValueError(f"{field_name} is required")
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be an integer")
    if min_value is not None and int_value < min_value:
        raise ValueError(f"{field_name} must be at least {min_value}")
    if max_value is not None and int_value > max_value:
        raise ValueError(f"{field_name} must be at most {max_value}")
    return int_value


def lambda_handler(event, context):
    """
    Bedrock Agent action to get menu history.

    Input (from agent):
        {
            "messageVersion": "1.0",
            "agent": {...},
            "actionGroup": "...",
            "function": "get_history",
            "parameters": [
                {"name": "days", "type": "integer", "value": "7"}
            ]
        }

    Output (to agent):
        {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "...",
                "function": "get_history",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": "{\"history\": [...]}"
                        }
                    }
                }
            }
        }
    """
    try:
        # Extract parameters from Bedrock Agent event format
        parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}
        days = safe_int_conversion(
            parameters.get("days"), "days", min_value=1, max_value=365, default=30
        )

        logger.info(f"Getting menu history for past {days} days")

        table = get_dynamodb().Table(HISTORY_TABLE)
        history_list = []

        # Fetch history for the specified number of days
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            response = table.get_item(Key={"date": date})
            if "Item" in response:
                history_list.append(decimal_to_float(response["Item"]))

        # Sort by date (most recent first)
        history_list.sort(key=lambda x: x["date"], reverse=True)

        logger.info(f"Found {len(history_list)} history entries")

        # Return in Bedrock Agent response format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {"body": json.dumps({"history": history_list})}
                },
            },
        }

    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 400,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": str(e), "history": []})
                    }
                },
            },
        }
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}", exc_info=True)
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": str(e), "history": []})
                    }
                },
            },
        }
