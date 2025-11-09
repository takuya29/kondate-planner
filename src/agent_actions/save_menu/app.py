import os
import logging
import json
from datetime import datetime

from utils import dynamodb, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_TABLE = os.environ["HISTORY_TABLE"]


def validate_date_format(date_string):
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def lambda_handler(event, context):
    """
    Bedrock Agent action to save menu history.

    Input (from agent):
        {
            "messageVersion": "1.0",
            "agent": {...},
            "actionGroup": "...",
            "function": "save_menu",
            "parameters": [
                {"name": "date", "type": "string", "value": "2025-11-09"},
                {"name": "meals", "type": "object", "value": "{...}"},
                {"name": "notes", "type": "string", "value": "..."}
            ]
        }

    Output (to agent):
        {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "...",
                "function": "save_menu",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": "{\"success\": true, \"date\": \"2025-11-09\", \"message\": \"...\"}"
                        }
                    }
                }
            }
        }
    """
    try:
        # Log the full event for debugging
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract parameters from Bedrock Agent event format
        # For POST requests with requestBody, parameters are in requestBody.content.application/json
        parameters_list = event.get("parameters", [])
        if not parameters_list and "requestBody" in event:
            request_body = event.get("requestBody", {})
            content = request_body.get("content", {})
            parameters_list = content.get("application/json", [])

        parameters = {p["name"]: p["value"] for p in parameters_list}
        logger.info(f"Extracted parameters: {json.dumps(parameters)}")

        # Parse meals JSON if it's a string
        meals = parameters.get("meals")
        if isinstance(meals, str):
            meals = json.loads(meals)

        date = parameters.get("date")
        notes = parameters.get("notes")

        # Validate required fields
        if not date:
            raise ValueError("dateは必須項目です")
        if not meals:
            raise ValueError("mealsは必須項目です")

        # Validate date format
        if not validate_date_format(date):
            raise ValueError("日付は YYYY-MM-DD 形式で指定してください")

        # Validate meals structure
        if not isinstance(meals, dict):
            raise ValueError("mealsはオブジェクト形式である必要があります")

        logger.info(f"Saving menu history for date: {date}")

        # Build history object
        history = {
            "date": date,
            "meals": meals,
            "recipes": [],  # Flat list of recipe IDs
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Extract recipe IDs from meals structure
        for meal_type in ["breakfast", "lunch", "dinner"]:
            if meal_type in meals:
                for recipe in meals[meal_type]:
                    if recipe.get("recipe_id"):
                        history["recipes"].append(recipe["recipe_id"])

        # Add optional notes
        if notes:
            history["notes"] = notes

        # Save to DynamoDB
        table = dynamodb.Table(HISTORY_TABLE)
        table.put_item(Item=history)

        logger.info(f"Successfully saved menu history for {date}")

        # Return in Bedrock Agent response format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({
                            "success": True,
                            "date": date,
                            "message": "献立履歴を保存しました"
                        })
                    }
                }
            }
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
                        "body": json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": f"保存に失敗しました: {str(e)}"
                        })
                    }
                }
            }
        }
    except Exception as e:
        logger.error(f"Error saving menu: {str(e)}", exc_info=True)
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({
                            "success": False,
                            "error": str(e),
                            "message": f"保存中にエラーが発生しました: {str(e)}"
                        })
                    }
                }
            }
        }
