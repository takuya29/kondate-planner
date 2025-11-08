"""Unit tests for get_recipes Lambda function."""
import json
import pytest
from unittest.mock import Mock, patch
from moto import mock_dynamodb
from decimal import Decimal
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/get_recipes'))

from app import lambda_handler, decimal_to_float


@pytest.mark.unit
class TestGetRecipes:
    """Test suite for get_recipes Lambda function."""

    @mock_dynamodb
    def test_get_recipes_success(self, lambda_context, mock_dynamodb_recipes_table):
        """Test successful retrieval of all recipes."""
        # Add sample recipes to table
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'トースト',
            'category': '主食'
        })
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_002',
            'name': '卵焼き',
            'category': '副菜'
        })

        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'recipes' in body
        assert 'count' in body
        assert body['count'] == 2

    @mock_dynamodb
    def test_get_recipes_empty_table(self, lambda_context, mock_dynamodb_recipes_table):
        """Test getting recipes from empty table."""
        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['recipes'] == []
        assert body['count'] == 0

    @mock_dynamodb
    def test_get_recipes_with_category_filter(self, lambda_context, mock_dynamodb_recipes_table):
        """Test filtering recipes by category."""
        # Add recipes with different categories
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'トースト',
            'category': '主食'
        })
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_002',
            'name': '卵焼き',
            'category': '副菜'
        })
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_003',
            'name': 'ご飯',
            'category': '主食'
        })

        event = {
            'queryStringParameters': {
                'category': '主食'
            }
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 2
        for recipe in body['recipes']:
            assert recipe['category'] == '主食'

    @mock_dynamodb
    def test_get_recipes_no_match_category(self, lambda_context, mock_dynamodb_recipes_table):
        """Test filtering with category that doesn't exist."""
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'トースト',
            'category': '主食'
        })

        event = {
            'queryStringParameters': {
                'category': '存在しないカテゴリ'
            }
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 0
        assert body['recipes'] == []

    @mock_dynamodb
    def test_get_recipes_sorted_by_name(self, lambda_context, mock_dynamodb_recipes_table):
        """Test that recipes are sorted by name."""
        # Add recipes in random order
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_003',
            'name': 'んめいどう',  # Should be last
            'category': '主食'
        })
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'あいうえお',  # Should be first
            'category': '副菜'
        })
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_002',
            'name': 'かきくけこ',  # Should be middle
            'category': 'メイン'
        })

        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        names = [r['name'] for r in body['recipes']]
        assert names == sorted(names)

    @mock_dynamodb
    def test_get_recipes_cors_headers(self, lambda_context, mock_dynamodb_recipes_table):
        """Test that CORS headers are present."""
        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert 'headers' in response
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'

    def test_get_recipes_dynamodb_error(self, lambda_context):
        """Test handling of DynamoDB errors."""
        event = {
            'queryStringParameters': None
        }

        with patch('boto3.resource') as mock_resource:
            mock_table = Mock()
            mock_table.scan.side_effect = Exception('DynamoDB error')
            mock_resource.return_value.Table.return_value = mock_table

            response = lambda_handler(event, lambda_context)

            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'error' in body

    @mock_dynamodb
    def test_get_recipes_null_query_params(self, lambda_context, mock_dynamodb_recipes_table):
        """Test handling of null query parameters."""
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'テスト',
            'category': '主食'
        })

        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 1

    def test_decimal_to_float_conversion(self):
        """Test decimal to float conversion utility."""
        # Test Decimal conversion
        assert decimal_to_float(Decimal('10.5')) == 10.5
        assert decimal_to_float(Decimal('10')) == 10

        # Test dict conversion
        result = decimal_to_float({'value': Decimal('10.5')})
        assert result == {'value': 10.5}

        # Test list conversion
        result = decimal_to_float([Decimal('10'), Decimal('20.5')])
        assert result == [10, 20.5]

        # Test nested structures
        result = decimal_to_float({
            'values': [Decimal('10'), Decimal('20.5')],
            'nested': {'inner': Decimal('30')}
        })
        assert result == {
            'values': [10, 20.5],
            'nested': {'inner': 30}
        }

        # Test non-Decimal values pass through
        assert decimal_to_float('string') == 'string'
        assert decimal_to_float(123) == 123

    @mock_dynamodb
    def test_get_recipes_with_decimal_fields(self, lambda_context, mock_dynamodb_recipes_table):
        """Test that Decimal fields from DynamoDB are properly converted."""
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'テスト',
            'category': '主食',
            'cooking_time': 30  # This will be stored as Decimal in DynamoDB
        })

        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Ensure no Decimal objects in JSON (would cause serialization error)
        assert isinstance(body['recipes'][0]['cooking_time'], int)

    @mock_dynamodb
    def test_get_recipes_missing_optional_fields(self, lambda_context, mock_dynamodb_recipes_table):
        """Test recipes with missing optional fields."""
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'ミニマルレシピ'
            # No category, cooking_time, etc.
        })

        event = {
            'queryStringParameters': None
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 1
        assert body['recipes'][0]['name'] == 'ミニマルレシピ'

    @mock_dynamodb
    def test_get_recipes_empty_category_filter(self, lambda_context, mock_dynamodb_recipes_table):
        """Test with empty category filter value."""
        mock_dynamodb_recipes_table.put_item(Item={
            'recipe_id': 'recipe_001',
            'name': 'テスト',
            'category': '主食'
        })

        event = {
            'queryStringParameters': {
                'category': ''
            }
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 200
        # Empty category should match nothing or all depending on implementation
