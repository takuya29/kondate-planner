"""Sample test data for use in tests."""

SAMPLE_RECIPES = [
    {
        "recipe_id": "recipe_001",
        "name": "トースト",
        "category": "主食",
        "cooking_time": 5,
        "ingredients": ["食パン", "バター"],
        "instructions": "パンを焼く",
        "tags": ["朝食", "簡単"],
    },
    {
        "recipe_id": "recipe_002",
        "name": "卵焼き",
        "category": "副菜",
        "cooking_time": 10,
        "ingredients": ["卵", "砂糖", "塩"],
        "instructions": "卵を焼く",
        "tags": ["朝食", "和食"],
    },
    {
        "recipe_id": "recipe_003",
        "name": "ハンバーグ",
        "category": "メイン",
        "cooking_time": 30,
        "ingredients": ["豚ひき肉", "玉ねぎ", "パン粉"],
        "instructions": "ハンバーグを焼く",
        "tags": ["洋食", "メイン"],
    },
    {
        "recipe_id": "recipe_004",
        "name": "味噌汁",
        "category": "汁物",
        "cooking_time": 10,
        "ingredients": ["味噌", "豆腐", "わかめ"],
        "instructions": "味噌汁を作る",
        "tags": ["和食", "汁物"],
    },
]

SAMPLE_HISTORY_ENTRIES = [
    {
        "date": "2025-11-08",
        "meals": {
            "breakfast": [
                {"recipe_id": "recipe_001", "name": "トースト"},
                {"recipe_id": "recipe_002", "name": "卵焼き"},
            ],
            "lunch": [
                {"recipe_id": "recipe_003", "name": "ハンバーグ"},
                {"recipe_id": "recipe_004", "name": "味噌汁"},
            ],
            "dinner": [
                {"recipe_id": "recipe_005", "name": "鮭の塩焼き"},
                {"recipe_id": "recipe_006", "name": "サラダ"},
            ],
        },
        "recipes": [
            "recipe_001",
            "recipe_002",
            "recipe_003",
            "recipe_004",
            "recipe_005",
            "recipe_006",
        ],
        "notes": "バランスの良い献立",
    },
    {
        "date": "2025-11-07",
        "meals": {
            "breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}],
            "lunch": [{"recipe_id": "recipe_007", "name": "カレーライス"}],
            "dinner": [
                {"recipe_id": "recipe_008", "name": "焼き魚"},
                {"recipe_id": "recipe_004", "name": "味噌汁"},
            ],
        },
        "recipes": ["recipe_001", "recipe_007", "recipe_008", "recipe_004"],
    },
]

# Invalid test data for edge cases
INVALID_RECIPE_MISSING_NAME = {"category": "メイン", "cooking_time": 30}

INVALID_RECIPE_MALFORMED = {
    "name": 123,  # Should be string
    "cooking_time": "invalid",  # Should be integer
}

INVALID_HISTORY_MISSING_DATE = {
    "meals": {"breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}]}
}

INVALID_HISTORY_BAD_DATE_FORMAT = {
    "date": "2025/11/08",  # Wrong format
    "meals": {"breakfast": [{"recipe_id": "recipe_001", "name": "トースト"}]},
}

INVALID_HISTORY_EMPTY_MEALS = {
    "date": "2025-11-08",
    "meals": {"breakfast": []},  # Empty array not allowed
}

INVALID_HISTORY_MISSING_RECIPE_FIELDS = {
    "date": "2025-11-08",
    "meals": {"breakfast": [{"recipe_id": "recipe_001"}]},  # Missing 'name'
}
