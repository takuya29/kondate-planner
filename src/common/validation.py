"""
Common validation utilities for Lambda functions
"""


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
