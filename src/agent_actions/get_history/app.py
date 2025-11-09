import os
import logging
from datetime import datetime, timedelta

from utils import dynamodb, decimal_to_float

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


def lambda_handler(event, context):
    """
    Bedrock Agent action to get menu history.

    Input (from agent):
        {
            "days": number (optional, default 30, range 1-365)
        }

    Output (to agent):
        {
            "history": [
                {
                    "date": "YYYY-MM-DD",
                    "meals": {
                        "breakfast": [{"recipe_id": "...", "name": "..."}],
                        "lunch": [{"recipe_id": "...", "name": "..."}],
                        "dinner": [{"recipe_id": "...", "name": "..."}]
                    },
                    "recipes": ["recipe_id1", "recipe_id2"],  # Flat list for deduplication
                    "notes": "string (optional)"
                }
            ]
        }
    """
    try:
        # Agent passes parameters directly
        days = safe_int_conversion(
            event.get('days'), 'days', min_value=1, max_value=365, default=30
        )

        logger.info(f"Getting menu history for past {days} days")

        table = dynamodb.Table(HISTORY_TABLE)
        history_list = []

        # Fetch history for the specified number of days
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            response = table.get_item(Key={'date': date})
            if 'Item' in response:
                history_list.append(decimal_to_float(response['Item']))

        # Sort by date (most recent first)
        history_list.sort(key=lambda x: x['date'], reverse=True)

        logger.info(f"Found {len(history_list)} history entries")

        return {
            'history': history_list
        }

    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return {
            'error': str(e),
            'history': []
        }
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'history': []
        }
