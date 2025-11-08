import os
import logging
from botocore.exceptions import ClientError
from utils import dynamodb, create_response, decimal_to_float

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RECIPES_TABLE = os.environ['RECIPES_TABLE']

def lambda_handler(event, context):
    try:
        recipe_id = event['pathParameters']['recipe_id']
        table = dynamodb.Table(RECIPES_TABLE)
        
        response = table.get_item(Key={'recipe_id': recipe_id})
        item = response.get('Item')

        if not item:
            return create_response(404, {'error': 'Recipe not found'})

        item = decimal_to_float(item)

        return create_response(200, item)

    except ClientError as e:
        logger.error(f"Error getting recipe: {e.response['Error']['Message']}")
        return create_response(500, {'error': 'Could not fetch recipe'})
    except KeyError:
        logger.error("'recipe_id' not found in path parameters")
        return create_response(400, {'error': "'recipe_id' not found in path"})
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

