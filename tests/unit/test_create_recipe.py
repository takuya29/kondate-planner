"""Unit tests for create_recipe Lambda function."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_dynamodb
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/create_recipe'))

from app import lambda_handler


@pytest.mark.unit
class TestCreateRecipe:
    """Test suite for create_recipe Lambda function."""

    @mock_dynamodb
    def test_create_recipe_success(self, lambda_context):
        """Test successful recipe creation."""
        event = {
            'body': json.dumps({
                'name': 'テストレシピ',
                'category': 'メイン',
                'cooking_time': 30,
                'ingredients': ['材料1', '材料2'],
                'instructions': 'テスト手順',
                'tags': ['tag1', 'tag2']
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'message' in body
        assert 'recipe' in body
        assert body['recipe']['name'] == 'テストレシピ'
        assert body['recipe']['category'] == 'メイン'
        assert body['recipe']['cooking_time'] == 30

    @mock_dynamodb
    def test_create_recipe_minimal_fields(self, lambda_context):
        """Test recipe creation with only required fields."""
        event = {
            'body': json.dumps({
                'name': 'シンプルレシピ'
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['recipe']['name'] == 'シンプルレシピ'
        # Check defaults
        assert body['recipe']['category'] == '未分類'
        assert body['recipe']['cooking_time'] == 30
        assert body['recipe']['ingredients'] == []

    def test_create_recipe_missing_name(self, lambda_context):
        """Test that missing 'name' field returns 400."""
        event = {
            'body': json.dumps({
                'category': 'メイン',
                'cooking_time': 30
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'name' in body['error']

    def test_create_recipe_empty_body(self, lambda_context):
        """Test that empty body returns 400."""
        event = {
            'body': json.dumps({})
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 400

    def test_create_recipe_invalid_json(self, lambda_context):
        """Test that invalid JSON returns 500."""
        event = {
            'body': 'invalid json'
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body

    def test_create_recipe_missing_body(self, lambda_context):
        """Test that missing body is handled gracefully."""
        event = {}

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 400

    @mock_dynamodb
    def test_create_recipe_with_custom_id(self, lambda_context):
        """Test creating recipe with custom recipe_id."""
        custom_id = 'recipe_custom_123'
        event = {
            'body': json.dumps({
                'recipe_id': custom_id,
                'name': 'カスタムIDレシピ'
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['recipe']['recipe_id'] == custom_id

    @mock_dynamodb
    def test_create_recipe_auto_generated_id(self, lambda_context):
        """Test that recipe_id is auto-generated if not provided."""
        event = {
            'body': json.dumps({
                'name': '自動IDレシピ'
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'recipe_id' in body['recipe']
        assert body['recipe']['recipe_id'].startswith('recipe_')

    @mock_dynamodb
    def test_create_recipe_timestamps(self, lambda_context):
        """Test that timestamps are added."""
        event = {
            'body': json.dumps({
                'name': 'タイムスタンプテスト'
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'created_at' in body['recipe']
        assert 'updated_at' in body['recipe']

    @mock_dynamodb
    def test_create_recipe_cors_headers(self, lambda_context):
        """Test that CORS headers are present."""
        event = {
            'body': json.dumps({
                'name': 'CORSテスト'
            })
        }

        response = lambda_handler(event, lambda_context)

        assert 'headers' in response
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'

    @mock_dynamodb
    def test_create_recipe_large_payload(self, lambda_context):
        """Test creating recipe with large payload."""
        event = {
            'body': json.dumps({
                'name': 'ラージペイロード',
                'ingredients': ['材料' + str(i) for i in range(100)],
                'instructions': 'テスト手順 ' * 1000,
                'tags': ['tag' + str(i) for i in range(50)]
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert len(body['recipe']['ingredients']) == 100
        assert len(body['recipe']['tags']) == 50

    def test_create_recipe_dynamodb_error(self, lambda_context):
        """Test handling of DynamoDB errors."""
        event = {
            'body': json.dumps({
                'name': 'DynamoDBエラーテスト'
            })
        }

        with patch('boto3.resource') as mock_resource:
            mock_table = Mock()
            mock_table.put_item.side_effect = Exception('DynamoDB error')
            mock_resource.return_value.Table.return_value = mock_table

            response = lambda_handler(event, lambda_context)

            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert 'error' in body

    @mock_dynamodb
    def test_create_recipe_empty_arrays(self, lambda_context):
        """Test that empty arrays are handled correctly."""
        event = {
            'body': json.dumps({
                'name': '空配列テスト',
                'ingredients': [],
                'tags': []
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['recipe']['ingredients'] == []
        assert body['recipe']['tags'] == []

    @mock_dynamodb
    def test_create_recipe_special_characters(self, lambda_context):
        """Test recipe creation with special characters."""
        event = {
            'body': json.dumps({
                'name': 'テスト!@#$%^&*()',
                'instructions': '特殊文字: <>?:"{}|_+~`'
            })
        }

        response = lambda_handler(event, lambda_context)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['recipe']['name'] == 'テスト!@#$%^&*()'
