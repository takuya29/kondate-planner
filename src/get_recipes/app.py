import os
import logging

from utils import dynamodb, create_response, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RECIPES_TABLE = os.environ['RECIPES_TABLE']


def lambda_handler(event, context):
    """Lambda to get all recipes, with optional category filtering."""
    try:
        table = dynamodb.Table(RECIPES_TABLE)

        query_params = event.get('queryStringParameters', {}) or {}
        category = query_params.get('category')

        response = table.scan()
        recipes = decimal_to_float(response.get('Items', []))

        if category:
            recipes = [r for r in recipes if r.get('category') == category]

        recipes.sort(key=lambda x: x.get('name', ''))

        return create_response(200, {
            'recipes': recipes,
            'count': len(recipes)
        })

    except Exception as e:
        logger.error(f"Error getting recipes: {str(e)}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

