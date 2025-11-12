"""Unit tests for shared utilities (src/layers/common/utils.py)."""

from decimal import Decimal

import pytest

from utils import decimal_to_float, parse_bedrock_parameter


class TestDecimalToFloat:
    """Test cases for decimal_to_float function."""

    def test_convert_simple_decimal(self):
        """Test converting a simple Decimal to float."""
        result = decimal_to_float(Decimal("10.5"))
        assert result == 10.5
        assert isinstance(result, float)

    def test_convert_decimal_integer(self):
        """Test converting a Decimal integer to int."""
        result = decimal_to_float(Decimal("10"))
        assert result == 10
        assert isinstance(result, int)

    def test_convert_dict_with_decimals(self):
        """Test converting a dictionary containing Decimals."""
        input_dict = {
            "servings": Decimal("20"),
            "rating": Decimal("4.5"),
            "name": "Test Recipe",
        }
        result = decimal_to_float(input_dict)
        assert result == {"servings": 20, "rating": 4.5, "name": "Test Recipe"}
        assert isinstance(result["servings"], int)
        assert isinstance(result["rating"], float)

    def test_convert_nested_dict(self):
        """Test converting nested dictionaries with Decimals."""
        input_dict = {
            "recipe": {
                "prep_time": Decimal("30"),
                "servings": Decimal("4"),
            },
            "nutrition": {"calories": Decimal("500.5")},
        }
        result = decimal_to_float(input_dict)
        assert result["recipe"]["prep_time"] == 30
        assert result["recipe"]["servings"] == 4
        assert result["nutrition"]["calories"] == 500.5

    def test_convert_list_with_decimals(self):
        """Test converting a list containing Decimals."""
        input_list = [Decimal("1"), Decimal("2.5"), Decimal("3")]
        result = decimal_to_float(input_list)
        assert result == [1, 2.5, 3]
        assert isinstance(result[0], int)
        assert isinstance(result[1], float)

    def test_convert_nested_list_and_dict(self):
        """Test converting complex nested structures."""
        input_data = {
            "recipes": [
                {"prep_time": Decimal("20"), "name": "Recipe 1"},
                {"prep_time": Decimal("30"), "name": "Recipe 2"},
            ],
            "totals": [Decimal("50"), Decimal("100.5")],
        }
        result = decimal_to_float(input_data)
        assert result["recipes"][0]["prep_time"] == 20
        assert result["recipes"][1]["prep_time"] == 30
        assert result["totals"] == [50, 100.5]

    def test_non_decimal_unchanged(self):
        """Test that non-Decimal types are unchanged."""
        assert decimal_to_float("string") == "string"
        assert decimal_to_float(42) == 42
        assert decimal_to_float(None) is None
        assert decimal_to_float(True) is True


class TestParseBedRockParameter:
    """Test cases for parse_bedrock_parameter function."""

    def test_parse_dict_unchanged(self):
        """Test that a dict is returned unchanged."""
        input_dict = {"key": "value"}
        result = parse_bedrock_parameter(input_dict, "test")
        assert result == input_dict

    def test_parse_list_unchanged(self):
        """Test that a list is returned unchanged."""
        input_list = [1, 2, 3]
        result = parse_bedrock_parameter(input_list, "test")
        assert result == input_list

    def test_parse_json_string(self):
        """Test parsing a valid JSON string."""
        json_string = '{"lunch": ["カレー", "サラダ"]}'
        result = parse_bedrock_parameter(json_string, "meals")
        assert result == {"lunch": ["カレー", "サラダ"]}

    def test_parse_python_dict_format_simple(self):
        """Test parsing Python dict format (key=value) with string arrays."""
        # Bedrock might send arrays as JSON strings
        json_string = '{"lunch": ["カレー", "サラダ"]}'
        result = parse_bedrock_parameter(json_string, "meals")
        assert result["lunch"][0] == "カレー"
        assert result["lunch"][1] == "サラダ"

    def test_parse_python_dict_format_complex(self):
        """Test parsing complex JSON format with multiple meals."""
        json_string = '{"breakfast": ["味噌汁", "納豆"], "lunch": ["焼きそば"], "dinner": ["焼き魚", "サラダ"]}'
        result = parse_bedrock_parameter(json_string, "meals")
        assert len(result) == 3
        assert result["breakfast"][0] == "味噌汁"
        assert result["breakfast"][1] == "納豆"
        assert result["lunch"][0] == "焼きそば"
        assert result["dinner"][0] == "焼き魚"
        assert result["dinner"][1] == "サラダ"

    def test_parse_python_dict_with_japanese_chars(self):
        """Test parsing Python dict with Japanese characters."""
        python_dict = "{name=鮭の塩焼き, category=主菜}"
        result = parse_bedrock_parameter(python_dict, "recipe")
        assert result["name"] == "鮭の塩焼き"
        assert result["category"] == "主菜"

    def test_parse_non_string_unchanged(self):
        """Test that non-string types are returned unchanged."""
        assert parse_bedrock_parameter(42, "test") == 42
        assert parse_bedrock_parameter(None, "test") is None
        assert parse_bedrock_parameter(True, "test") is True

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unable to parse"):
            parse_bedrock_parameter("{invalid format}", "test")

    def test_parse_empty_string(self):
        """Test parsing an empty string."""
        result = parse_bedrock_parameter("", "test")
        assert result == ""

    def test_parse_python_dict_multiple_recipe_items(self):
        """Test parsing JSON with multiple items in a meal array."""
        json_string = '{"dinner": ["味噌汁", "白米", "焼き魚"]}'
        result = parse_bedrock_parameter(json_string, "meals")
        assert len(result["dinner"]) == 3
        assert result["dinner"][0] == "味噌汁"
        assert result["dinner"][1] == "白米"
        assert result["dinner"][2] == "焼き魚"
