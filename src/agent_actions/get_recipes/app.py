import os
import logging
import json

from utils import get_dynamodb, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RECIPES_TABLE = os.environ["RECIPES_TABLE"]


def lambda_handler(event, context):
    """
    Bedrock Agent action to get all recipes, with optional category filtering.

    Input (from agent):
        {
            "messageVersion": "1.0",
            "agent": {...},
            "actionGroup": "...",
            "function": "get_recipes",
            "parameters": [
                {"name": "category", "type": "string", "value": "主菜"}
            ]
        }

    Output (to agent):
        {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "...",
                "function": "get_recipes",
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": "{\"recipes\": [...]}"
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
        parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}
        category = parameters.get("category")

        logger.info(f"Getting recipes with category filter: {category}")

        table = get_dynamodb().Table(RECIPES_TABLE)
        response = table.scan()
        recipes = decimal_to_float(response.get("Items", []))

        # Filter by category if specified
        if category:
            recipes = [r for r in recipes if r.get("category") == category]
            logger.info(f"Filtered to {len(recipes)} recipes in category '{category}'")

        # Sort by name for consistent ordering
        recipes.sort(key=lambda x: x.get("name", ""))

        # Return in Bedrock Agent response format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {"body": json.dumps({"recipes": recipes})}
                },
            },
        }

    except Exception as e:
        logger.error(f"Error getting recipes: {str(e)}", exc_info=True)
        # Return error in Bedrock Agent format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": str(e), "recipes": []})
                    }
                },
            },
        }
