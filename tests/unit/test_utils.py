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
            "cooking_time": Decimal("20"),
            "rating": Decimal("4.5"),
            "name": "Test Recipe",
        }
        result = decimal_to_float(input_dict)
        assert result == {"cooking_time": 20, "rating": 4.5, "name": "Test Recipe"}
        assert isinstance(result["cooking_time"], int)
        assert isinstance(result["rating"], float)

    def test_convert_nested_dict(self):
        """Test converting nested dictionaries with Decimals."""
        input_dict = {
            "recipe": {
                "cooking_time": Decimal("30"),
                "servings": Decimal("4"),
            },
            "nutrition": {"calories": Decimal("500.5")},
        }
        result = decimal_to_float(input_dict)
        assert result["recipe"]["cooking_time"] == 30
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
                {"cooking_time": Decimal("20"), "name": "Recipe 1"},
                {"cooking_time": Decimal("30"), "name": "Recipe 2"},
            ],
            "totals": [Decimal("50"), Decimal("100.5")],
        }
        result = decimal_to_float(input_data)
        assert result["recipes"][0]["cooking_time"] == 20
        assert result["recipes"][1]["cooking_time"] == 30
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
        json_string = '{"lunch": [{"recipe_id": "recipe_001", "name": "カレー"}]}'
        result = parse_bedrock_parameter(json_string, "meals")
        assert result == {"lunch": [{"recipe_id": "recipe_001", "name": "カレー"}]}

    def test_parse_python_dict_format_simple(self):
        """Test parsing Python dict format (key=value)."""
        python_dict = "{lunch=[{recipe_id=recipe_001, name=カレー}]}"
        result = parse_bedrock_parameter(python_dict, "meals")
        assert result["lunch"][0]["recipe_id"] == "recipe_001"
        assert result["lunch"][0]["name"] == "カレー"

    def test_parse_python_dict_format_complex(self):
        """Test parsing complex Python dict format with multiple meals."""
        python_dict = (
            "{breakfast=[{recipe_id=recipe_001, name=味噌汁}], "
            "lunch=[{recipe_id=recipe_002, name=焼きそば}], "
            "dinner=[{recipe_id=recipe_003, name=焼き魚}]}"
        )
        result = parse_bedrock_parameter(python_dict, "meals")
        assert len(result) == 3
        assert result["breakfast"][0]["recipe_id"] == "recipe_001"
        assert result["lunch"][0]["recipe_id"] == "recipe_002"
        assert result["dinner"][0]["recipe_id"] == "recipe_003"

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
        """Test parsing Python dict with multiple items in a meal array."""
        python_dict = (
            "{dinner=[{recipe_id=recipe_001, name=味噌汁}, "
            "{recipe_id=recipe_002, name=白米}]}"
        )
        result = parse_bedrock_parameter(python_dict, "meals")
        assert len(result["dinner"]) == 2
        assert result["dinner"][0]["name"] == "味噌汁"
        assert result["dinner"][1]["name"] == "白米"
