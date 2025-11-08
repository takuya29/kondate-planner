import json
import os
import uuid
import logging
from datetime import datetime

from utils import dynamodb, create_response

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RECIPES_TABLE = os.environ['RECIPES_TABLE']


def lambda_handler(event, context):
    """Lambda to create a new recipe."""
    try:
        body = json.loads(event.get('body', '{}'))

        if 'name' not in body:
            return create_response(400, {'error': 'nameは必須項目です'})

        recipe = {
            'recipe_id': body.get('recipe_id', f"recipe_{uuid.uuid4().hex[:8]}"),
            'name': body['name'],
            'category': body.get('category', '未分類'),
            'cooking_time': body.get('cooking_time', 30),
            'ingredients': body.get('ingredients', []),
            'recipe_url': body.get('recipe_url', ''),
            'tags': body.get('tags', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        table = dynamodb.Table(RECIPES_TABLE)
        table.put_item(Item=recipe)

        return create_response(201, {
            'message': 'レシピを作成しました',
            'recipe': recipe
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {str(e)}")
        return create_response(400, {'error': f'Invalid JSON format: {str(e)}'})
    except Exception as e:
        logger.error(f"Error creating recipe: {str(e)}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

