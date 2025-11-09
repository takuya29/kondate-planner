import os
import logging

from utils import dynamodb, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RECIPES_TABLE = os.environ['RECIPES_TABLE']


def lambda_handler(event, context):
    """
    Bedrock Agent action to get all recipes, with optional category filtering.

    Input (from agent):
        {
            "category": "string (optional)"  # e.g., "主菜", "副菜", "汁物"
        }

    Output (to agent):
        {
            "recipes": [
                {
                    "recipe_id": "uuid",
                    "name": "string",
                    "category": "string",
                    "cooking_time": number,
                    "ingredients": ["string"],
                    "recipe_url": "string",
                    "tags": ["string"]
                }
            ]
        }
    """
    try:
        # Agent passes parameters directly in event (not wrapped in API Gateway format)
        category = event.get('category')

        logger.info(f"Getting recipes with category filter: {category}")

        table = dynamodb.Table(RECIPES_TABLE)
        response = table.scan()
        recipes = decimal_to_float(response.get('Items', []))

        # Filter by category if specified
        if category:
            recipes = [r for r in recipes if r.get('category') == category]
            logger.info(f"Filtered to {len(recipes)} recipes in category '{category}'")

        # Sort by name for consistent ordering
        recipes.sort(key=lambda x: x.get('name', ''))

        # Return plain dict (agent handles serialization)
        return {
            'recipes': recipes
        }

    except Exception as e:
        logger.error(f"Error getting recipes: {str(e)}", exc_info=True)
        # Return error in agent-friendly format
        return {
            'error': str(e),
            'recipes': []
        }
