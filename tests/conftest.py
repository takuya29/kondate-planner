"""Shared pytest fixtures for all tests."""
import os
import pytest
from moto import mock_dynamodb
import boto3
from decimal import Decimal


# Set test environment variables
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set environment variables for tests."""
    os.environ['RECIPES_TABLE'] = 'RecipesTable-Test'
    os.environ['HISTORY_TABLE'] = 'HistoryTable-Test'
    os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-3-sonnet-20240229-v1:0'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-1'


@pytest.fixture
def mock_dynamodb_recipes_table():
    """Create a mock DynamoDB recipes table."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')

        table = dynamodb.create_table(
            TableName='RecipesTable-Test',
            KeySchema=[
                {'AttributeName': 'recipe_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'recipe_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table


@pytest.fixture
def mock_dynamodb_history_table():
    """Create a mock DynamoDB history table."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')

        table = dynamodb.create_table(
            TableName='HistoryTable-Test',
            KeySchema=[
                {'AttributeName': 'date', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'date', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table


@pytest.fixture
def sample_recipe():
    """Sample recipe data."""
    return {
        'recipe_id': 'recipe_test123',
        'name': 'テストレシピ',
        'category': 'メイン',
        'cooking_time': 30,
        'ingredients': ['材料1', '材料2'],
        'instructions': 'テスト手順',
        'tags': ['tag1', 'tag2']
    }


@pytest.fixture
def sample_history():
    """Sample history data."""
    return {
        'date': '2025-11-08',
        'meals': {
            'breakfast': [
                {'recipe_id': 'recipe_001', 'name': 'トースト'},
                {'recipe_id': 'recipe_002', 'name': '卵焼き'}
            ],
            'lunch': [
                {'recipe_id': 'recipe_003', 'name': 'ハンバーグ'},
                {'recipe_id': 'recipe_004', 'name': '味噌汁'}
            ],
            'dinner': [
                {'recipe_id': 'recipe_005', 'name': '鮭の塩焼き'},
                {'recipe_id': 'recipe_006', 'name': 'サラダ'}
            ]
        },
        'notes': 'テストメモ'
    }


@pytest.fixture
def api_gateway_event():
    """Sample API Gateway event."""
    return {
        'body': '{}',
        'requestContext': {
            'http': {
                'method': 'POST'
            }
        },
        'queryStringParameters': None
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    class LambdaContext:
        def __init__(self):
            self.function_name = 'test-function'
            self.memory_limit_in_mb = 128
            self.invoked_function_arn = 'arn:aws:lambda:ap-northeast-1:123456789012:function:test-function'
            self.aws_request_id = 'test-request-id'

    return LambdaContext()
