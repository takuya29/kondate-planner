import os
import logging
from datetime import datetime

from utils import dynamodb, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_TABLE = os.environ['HISTORY_TABLE']


def validate_date_format(date_string):
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def lambda_handler(event, context):
    """
    Bedrock Agent action to save menu history.

    Input (from agent):
        {
            "date": "YYYY-MM-DD",
            "meals": {
                "breakfast": [{"recipe_id": "...", "name": "..."}],
                "lunch": [{"recipe_id": "...", "name": "..."}],
                "dinner": [{"recipe_id": "...", "name": "..."}]
            },
            "notes": "string (optional)"
        }

    Output (to agent):
        {
            "success": boolean,
            "date": "YYYY-MM-DD",
            "message": "string"
        }
    """
    try:
        # Validate required fields
        required_fields = ['date', 'meals']
        for field in required_fields:
            if field not in event:
                raise ValueError(f'{field}は必須項目です')

        # Validate date format
        if not validate_date_format(event.get('date')):
            raise ValueError('日付は YYYY-MM-DD 形式で指定してください')

        # Validate meals structure
        if not isinstance(event.get('meals'), dict):
            raise ValueError('mealsはオブジェクト形式である必要があります')

        logger.info(f"Saving menu history for date: {event['date']}")

        # Build history object
        history = {
            'date': event['date'],
            'meals': event['meals'],
            'recipes': [],  # Flat list of recipe IDs
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # Extract recipe IDs from meals structure
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            if meal_type in event['meals']:
                for recipe in event['meals'][meal_type]:
                    if recipe.get('recipe_id'):
                        history['recipes'].append(recipe['recipe_id'])

        # Add optional notes
        if 'notes' in event:
            history['notes'] = event['notes']

        # Save to DynamoDB
        table = dynamodb.Table(HISTORY_TABLE)
        table.put_item(Item=history)

        logger.info(f"Successfully saved menu history for {event['date']}")

        return {
            'success': True,
            'date': event['date'],
            'message': '献立履歴を保存しました'
        }

    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'保存に失敗しました: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Error saving menu: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': f'保存中にエラーが発生しました: {str(e)}'
        }
