import json
import os
import boto3
import logging
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
RECIPES_TABLE = os.environ["RECIPES_TABLE"]


def decimal_to_float(obj):
    """DynamoDB DecimalをPython標準型に変換"""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def lambda_handler(event, context):
    """Lambda関数のメインハンドラー"""
    try:
        table = dynamodb.Table(RECIPES_TABLE)

        # クエリパラメータから検索条件を取得（オプション）
        query_params = event.get("queryStringParameters", {}) or {}
        category = query_params.get("category")

        # 全レシピを取得
        response = table.scan()
        recipes = decimal_to_float(response.get("Items", []))

        # カテゴリでフィルタリング（指定された場合）
        if category:
            recipes = [r for r in recipes if r.get("category") == category]

        # レシピ名でソート
        recipes.sort(key=lambda x: x.get("name", ""))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"recipes": recipes, "count": len(recipes)}, ensure_ascii=False
            ),
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"error": f"Internal server error: {str(e)}"}, ensure_ascii=False
            ),
        }
