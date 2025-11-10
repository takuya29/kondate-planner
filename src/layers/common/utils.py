from __future__ import annotations

import json
import re
import boto3
from decimal import Decimal
from typing import Any

from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient

# AWS Clients (lazy-initialized to avoid import-time errors in test environments)
_dynamodb: DynamoDBServiceResource | None = None
_bedrock: BedrockRuntimeClient | None = None


def get_dynamodb() -> DynamoDBServiceResource:
    """Get or create DynamoDB resource."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def get_bedrock() -> BedrockRuntimeClient:
    """Get or create Bedrock client."""
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")
    return _bedrock


def create_response(
    status_code: int, body: Any, is_json: bool = True
) -> dict[str, Any]:
    """Creates a standard API Gateway response."""
    headers: dict[str, str] = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    }
    if is_json:
        headers["Content-Type"] = "application/json"
        body = json.dumps(body, ensure_ascii=False)

    return {"statusCode": status_code, "headers": headers, "body": body}


def decimal_to_float(obj: Any) -> Any:
    """Recursively converts DynamoDB Decimal types to Python floats or ints."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def parse_bedrock_parameter(value: Any, field_name: str = "parameter") -> Any:
    """
    Convert Bedrock Agent parameter format to proper Python object.

    Bedrock Agent sometimes sends parameters in Python dict-like format instead of JSON:
    Input: {lunch=[{recipe_id=recipe_019, name=焼きそば}], breakfast=[...]}
    Output: {"lunch":[{"recipe_id":"recipe_019","name":"焼きそば"}],"breakfast":[...]}

    Args:
        value: The parameter value (can be string, dict, or other type)
        field_name: Name of the field for error messages

    Returns:
        Parsed Python object (dict, list, etc.)

    Raises:
        ValueError: If the value cannot be parsed
    """
    # If already a dict or list, return as-is
    if isinstance(value, (dict, list)):
        return value

    # If not a string, return as-is
    if not isinstance(value, str):
        return value

    # If empty string, return as-is
    if value == "":
        return value

    # Try to parse as JSON first
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    # Convert Python-like dict format to JSON
    # Input: {lunch=[{recipe_id=recipe_019, name=焼きそば}], breakfast=[...]}
    # Output: {"lunch":[{"recipe_id":"recipe_019","name":"焼きそば"}],"breakfast":[...]}

    try:
        converted = value

        # Step 1: Replace = with :
        converted = converted.replace("=", ":")

        # Step 2: Add quotes around keys (words followed by colon)
        # Matches: word: -> "word":
        converted = re.sub(r"([{,]\s*)([a-z_]+):", r'\1"\2":', converted)

        # Step 3: Add quotes around unquoted string values
        # Matches values that are not already quoted and not numbers/booleans
        # Pattern: ": recipe_019" -> ": "recipe_019""
        converted = re.sub(r":\s*([a-zA-Z][a-zA-Z0-9_]*)", r': "\1"', converted)

        # Step 4: Add quotes around Japanese/special character values
        # Matches: ": 焼きそば," -> ": "焼きそば","
        converted = re.sub(
            r':\s*([^"\[\]{},:\s][^,}\]]*?)([,}\]])',
            lambda m: f': "{m.group(1).strip()}"{m.group(2)}',
            converted,
        )

        # Try to parse the converted string
        return json.loads(converted)

    except (json.JSONDecodeError, Exception) as e:
        raise ValueError(
            f"Unable to parse {field_name}. "
            f"Expected JSON or Python dict format. Error: {str(e)}"
        )
