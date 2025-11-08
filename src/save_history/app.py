import json
import os
import logging
from datetime import datetime, timedelta

from utils import dynamodb, create_response, decimal_to_float

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_TABLE = os.environ['HISTORY_TABLE']


def safe_int_conversion(value, field_name, min_value=None, max_value=None, default=None):
    """Safely convert a value to an integer with validation."""
    if value is None or value == '':
        if default is not None:
            return default
        raise ValueError(f"{field_name}が指定されていません")
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name}は整数値である必要があります")
    if min_value is not None and int_value < min_value:
        raise ValueError(f"{field_name}は{min_value}以上である必要があります")
    if max_value is not None and int_value > max_value:
        raise ValueError(f"{field_name}は{max_value}以下である必要があります")
    return int_value


def validate_date_format(date_string):
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def save_history(event):
    """Save menu history (POST)."""
    body = json.loads(event.get('body', '{}'))

    required_fields = ['date', 'meals']
    for field in required_fields:
        if field not in body:
            return create_response(400, {'error': f'{field}は必須項目です'})

    if not validate_date_format(body.get('date')):
        return create_response(400, {'error': '日付は YYYY-MM-DD 形式で指定してください'})

    # Basic validation for meals structure
    if not isinstance(body.get('meals'), dict):
        return create_response(400, {'error': 'mealsはオブジェクト形式である必要があります'})

    history = {
        'date': body['date'],
        'meals': body['meals'],
        'recipes': [],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    for meal_type in ['breakfast', 'lunch', 'dinner']:
        if meal_type in body['meals']:
            for recipe in body['meals'][meal_type]:
                if recipe.get('recipe_id'):
                    history['recipes'].append(recipe['recipe_id'])

    if 'notes' in body:
        history['notes'] = body['notes']

    table = dynamodb.Table(HISTORY_TABLE)
    table.put_item(Item=history)

    return create_response(201, {
        'message': '献立履歴を保存しました',
        'history': decimal_to_float(history)
    })


def get_history(event):
    """Get menu history (GET)."""
    query_params = event.get('queryStringParameters', {}) or {}
    days = safe_int_conversion(
        query_params.get('days'), 'days', min_value=1, max_value=365, default=30
    )

    table = dynamodb.Table(HISTORY_TABLE)
    history_list = []

    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        response = table.get_item(Key={'date': date})
        if 'Item' in response:
            history_list.append(decimal_to_float(response['Item']))

    history_list.sort(key=lambda x: x['date'], reverse=True)

    return create_response(200, {
        'history': history_list,
        'count': len(history_list)
    })


def lambda_handler(event, context):
    """Main Lambda handler, routing based on HTTP method."""
    try:
        http_method = event.get('requestContext', {}).get('http', {}).get('method')

        if http_method == 'POST':
            return save_history(event)
        elif http_method == 'GET':
            return get_history(event)
        else:
            return create_response(405, {'error': 'Method Not Allowed'})

    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Client error: {str(e)}")
        return create_response(400, {'error': str(e)})
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

