import json
import os
import boto3
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
HISTORY_TABLE = os.environ['HISTORY_TABLE']


def safe_int_conversion(value, field_name, min_value=None, max_value=None, default=None):
    """
    Safely convert a value to an integer with validation.

    Args:
        value: The value to convert (can be string, int, None, etc.)
        field_name: Name of the field for error messages
        min_value: Optional minimum value (inclusive)
        max_value: Optional maximum value (inclusive)
        default: Optional default value if value is None or empty

    Returns:
        The converted integer value

    Raises:
        ValueError: If the value cannot be converted to a valid integer
    """
    # Handle None or empty values
    if value is None or value == '':
        if default is not None:
            return default
        raise ValueError(f"{field_name}が指定されていません")

    # Try to convert to integer
    try:
        int_value = int(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"{field_name}は整数値である必要があります")

    # Validate range if specified
    if min_value is not None and int_value < min_value:
        raise ValueError(f"{field_name}は{min_value}以上である必要があります")

    if max_value is not None and int_value > max_value:
        raise ValueError(f"{field_name}は{max_value}以下である必要があります")

    return int_value


def decimal_to_float(obj):
    """DynamoDB DecimalをPython標準型に変換"""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def validate_date_format(date_string):
    """日付フォーマット(YYYY-MM-DD)の妥当性を検証"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def save_history(event):
    """献立履歴を保存（POST）"""
    body = json.loads(event.get('body', '{}'))

    # 必須フィールドのバリデーション
    required_fields = ['date', 'meals']
    for field in required_fields:
        if field not in body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'{field}は必須項目です'
                }, ensure_ascii=False)
            }

    # 日付フォーマットのバリデーション
    if not validate_date_format(body.get('date')):
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': '日付は YYYY-MM-DD 形式で指定してください（例: 2024-01-15）'
            }, ensure_ascii=False)
        }

    # meals構造のバリデーション
    for meal_type in ['breakfast', 'lunch', 'dinner']:
        if meal_type in body['meals']:
            meal_data = body['meals'][meal_type]
            if not isinstance(meal_data, list):
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': f'{meal_type}は配列形式である必要があります'
                    }, ensure_ascii=False)
                }
            if len(meal_data) == 0:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': f'{meal_type}は空の配列にできません'
                    }, ensure_ascii=False)
                }
            for recipe in meal_data:
                if not isinstance(recipe, dict) or 'recipe_id' not in recipe or 'name' not in recipe:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': f'{meal_type}の各レシピにはrecipe_idとnameが必要です'
                        }, ensure_ascii=False)
                    }

    # 履歴データを作成
    history = {
        'date': body['date'],
        'meals': body['meals'],
        'recipes': [],  # レシピIDのリストを保存
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    # レシピIDを抽出（配列形式）
    for meal_type in ['breakfast', 'lunch', 'dinner']:
        if meal_type in body['meals']:
            for recipe in body['meals'][meal_type]:
                recipe_id = recipe.get('recipe_id')
                if recipe_id:
                    history['recipes'].append(recipe_id)

    # メモがあれば追加
    if 'notes' in body:
        history['notes'] = body['notes']

    # DynamoDBに保存
    table = dynamodb.Table(HISTORY_TABLE)
    table.put_item(Item=history)

    return {
        'statusCode': 201,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': '献立履歴を保存しました',
            'history': decimal_to_float(history)
        }, ensure_ascii=False)
    }


def get_history(event):
    """献立履歴を取得（GET）"""
    query_params = event.get('queryStringParameters', {}) or {}

    try:
        days = safe_int_conversion(
            query_params.get('days'),
            'days',
            min_value=1,
            max_value=365,
            default=30
        )
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            }, ensure_ascii=False)
        }

    table = dynamodb.Table(HISTORY_TABLE)
    history_list = []

    # 過去N日分の履歴を取得
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        response = table.get_item(Key={'date': date})
        if 'Item' in response:
            history_list.append(decimal_to_float(response['Item']))

    # 日付の新しい順にソート
    history_list.sort(key=lambda x: x['date'], reverse=True)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'history': history_list,
            'count': len(history_list)
        }, ensure_ascii=False)
    }


def lambda_handler(event, context):
    """Lambda関数のメインハンドラー"""
    try:
        # HTTPメソッドによって処理を分岐
        http_method = event.get('requestContext', {}).get('http', {}).get('method')

        if http_method == 'POST':
            return save_history(event)
        elif http_method == 'GET':
            return get_history(event)
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Method not allowed'
                }, ensure_ascii=False)
            }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            }, ensure_ascii=False)
        }
