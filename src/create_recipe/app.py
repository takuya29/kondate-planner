import json
import os
import boto3
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
RECIPES_TABLE = os.environ['RECIPES_TABLE']


def lambda_handler(event, context):
    """Lambda関数のメインハンドラー"""
    try:
        # リクエストボディを取得
        body = json.loads(event.get('body', '{}'))

        # 必須フィールドのバリデーション
        required_fields = ['name']
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

        # レシピデータを作成
        recipe = {
            'recipe_id': body.get('recipe_id', f"recipe_{uuid.uuid4().hex[:8]}"),
            'name': body['name'],
            'category': body.get('category', '未分類'),
            'cooking_time': body.get('cooking_time', 30),
            'ingredients': body.get('ingredients', []),
            'instructions': body.get('instructions', ''),
            'tags': body.get('tags', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # DynamoDBに保存
        table = dynamodb.Table(RECIPES_TABLE)
        table.put_item(Item=recipe)

        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'レシピを作成しました',
                'recipe': recipe
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
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
