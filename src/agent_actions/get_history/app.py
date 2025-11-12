from __future__ import annotations

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Any

from utils import get_dynamodb, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_TABLE = os.environ["HISTORY_TABLE"]


def safe_int_conversion(
    value: Any,
    field_name: str,
    min_value: int | None = None,
    max_value: int | None = None,
    default: int | None = None,
) -> int:
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


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
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

        dynamodb = get_dynamodb()

        # Generate all date keys to fetch
        date_keys = [
            {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")}
            for i in range(days)
        ]

        history_list = []

        # DynamoDB batch_get_item has a limit of 100 items per request
        # Process in chunks of 100
        for i in range(0, len(date_keys), 100):
            chunk = date_keys[i : i + 100]
            response = dynamodb.batch_get_item(
                RequestItems={HISTORY_TABLE: {"Keys": chunk}}
            )

            # Extract items from the response
            if HISTORY_TABLE in response.get("Responses", {}):
                for item in response["Responses"][HISTORY_TABLE]:
                    history_list.append(decimal_to_float(item))

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
