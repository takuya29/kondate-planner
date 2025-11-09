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
        # For POST requests with requestBody, parameters are in requestBody.content.application/json.properties
        parameters_list = event.get("parameters", [])
        if not parameters_list and "requestBody" in event:
            request_body = event.get("requestBody", {})
            content = request_body.get("content", {})
            app_json = content.get("application/json", {})
            parameters_list = app_json.get("properties", [])

        parameters = {p["name"]: p["value"] for p in parameters_list}
        logger.info(f"Extracted parameters: {json.dumps(parameters)}")

        # Parse meals JSON if it's a string
        meals = parameters.get("meals")
        if isinstance(meals, str):
            # Bedrock Agent returns Python-like format: {key=[{key=value}]}
            # Convert to proper JSON format by using ast.literal_eval approach
            try:
                meals = json.loads(meals)
            except json.JSONDecodeError:
                logger.info("Converting Python-like format to JSON")
                import re
                meals_str = meals

                # Convert Python-like dict format to JSON:
                # Input: {lunch=[{recipe_id=recipe_019, name=焼きそば}], breakfast=[...]}
                # Output: {"lunch":[{"recipe_id":"recipe_019","name":"焼きそば"}],"breakfast":[...]}

                # Step 1: Replace = with :
                meals_str = meals_str.replace('=', ':')

                # Step 2: Add quotes around keys (words followed by colon)
                # Matches: word: -> "word":
                meals_str = re.sub(r'([{,]\s*)([a-z_]+):', r'\1"\2":', meals_str)

                # Step 3: Add quotes around unquoted string values
                # Matches values that are not already quoted and not numbers/booleans
                # Pattern: ": recipe_019" -> ": "recipe_019""
                meals_str = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9_]*)', r': "\1"', meals_str)

                # Step 4: Add quotes around Japanese/special character values
                # Matches: ": 焼きそば," -> ": "焼きそば","
                meals_str = re.sub(r':\s*([^"\[\]{},:\s][^,}\]]*?)([,}\]])', lambda m: f': "{m.group(1).strip()}"{m.group(2)}', meals_str)

                logger.info(f"Converted meals string: {meals_str}")
                try:
                    meals = json.loads(meals_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Still failed to parse after conversion: {str(e)}")
                    logger.error(f"Converted string was: {meals_str}")
                    raise ValueError(f"Invalid meals format: {str(e)}")

        date = parameters.get("date")
        notes = parameters.get("notes")

        # Validate required fields
        if not date:
            raise ValueError("date is required")
        if not meals:
            raise ValueError("meals is required")

        # Validate date format
        if not validate_date_format(date):
            raise ValueError("date must be in YYYY-MM-DD format")

        # Validate meals structure
        if not isinstance(meals, dict):
            raise ValueError("meals must be an object")

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
                            "message": "Menu history saved successfully"
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
                            "message": f"Failed to save menu: {str(e)}"
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
                            "message": f"Error occurred while saving menu: {str(e)}"
                        })
                    }
                }
            }
        }
