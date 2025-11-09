import json
import boto3
from decimal import Decimal

# AWS Clients (initialized once)
dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")


def create_response(status_code, body, is_json=True):
    """Creates a standard API Gateway response."""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    }
    if is_json:
        headers["Content-Type"] = "application/json"
        body = json.dumps(body, ensure_ascii=False)

    return {"statusCode": status_code, "headers": headers, "body": body}


def decimal_to_float(obj):
    """Recursively converts DynamoDB Decimal types to Python floats or ints."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj
