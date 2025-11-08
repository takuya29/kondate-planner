#!/usr/bin/env python3
"""
DynamoDBにサンプルデータを投入するスクリプト

使い方:
  python scripts/seed_data.py --recipes 20 --history 30
"""
import boto3
import argparse
from datetime import datetime, timedelta
import random

# DynamoDBクライアント
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')

# サンプルレシピデータ
SAMPLE_RECIPES = [
    {
        "name": "カレーライス",
        "category": "メイン",
        "cooking_time": 45,
        "ingredients": ["玉ねぎ", "にんじん", "じゃがいも", "豚肉", "カレールー"],
        "instructions": "野菜と肉を炒めて、水を加えて煮込み、カレールーを溶かす",
        "tags": ["和食", "定番"]
    },
    {
        "name": "親子丼",
        "category": "メイン",
        "cooking_time": 20,
        "ingredients": ["鶏もも肉", "玉ねぎ", "卵", "だし", "醤油", "みりん"],
        "instructions": "鶏肉と玉ねぎを煮て、溶き卵を加える",
        "tags": ["和食", "丼もの"]
    },
    {
        "name": "ハンバーグ",
        "category": "メイン",
        "cooking_time": 30,
        "ingredients": ["合いびき肉", "玉ねぎ", "パン粉", "卵", "デミグラスソース"],
        "instructions": "材料をこねて形を作り、焼く",
        "tags": ["洋食", "定番"]
    },
    {
        "name": "麻婆豆腐",
        "category": "メイン",
        "cooking_time": 25,
        "ingredients": ["豆腐", "豚ひき肉", "ネギ", "豆板醤", "醤油", "鶏がらスープ"],
        "instructions": "ひき肉を炒め、豆腐を加えて煮込む",
        "tags": ["中華", "辛い"]
    },
    {
        "name": "鮭の塩焼き",
        "category": "メイン",
        "cooking_time": 15,
        "ingredients": ["鮭", "塩"],
        "instructions": "鮭に塩を振って焼く",
        "tags": ["和食", "魚"]
    },
    {
        "name": "豚の生姜焼き",
        "category": "メイン",
        "cooking_time": 20,
        "ingredients": ["豚ロース", "玉ねぎ", "生姜", "醤油", "みりん"],
        "instructions": "豚肉と玉ねぎを炒め、タレを絡める",
        "tags": ["和食", "定番"]
    },
    {
        "name": "パスタカルボナーラ",
        "category": "メイン",
        "cooking_time": 20,
        "ingredients": ["パスタ", "ベーコン", "卵", "粉チーズ", "生クリーム"],
        "instructions": "パスタを茹で、ソースと絡める",
        "tags": ["洋食", "パスタ"]
    },
    {
        "name": "野菜炒め",
        "category": "副菜",
        "cooking_time": 15,
        "ingredients": ["キャベツ", "ピーマン", "にんじん", "豚肉", "塩胡椒"],
        "instructions": "野菜と豚肉を強火で炒める",
        "tags": ["中華", "簡単"]
    },
    {
        "name": "味噌汁",
        "category": "汁物",
        "cooking_time": 10,
        "ingredients": ["だし", "味噌", "豆腐", "わかめ", "ネギ"],
        "instructions": "だしを煮立て、具材を入れて味噌を溶く",
        "tags": ["和食", "定番"]
    },
    {
        "name": "卵焼き",
        "category": "副菜",
        "cooking_time": 10,
        "ingredients": ["卵", "だし", "砂糖", "醤油"],
        "instructions": "卵液を作り、巻きながら焼く",
        "tags": ["和食", "朝食"]
    },
    {
        "name": "トースト",
        "category": "朝食",
        "cooking_time": 5,
        "ingredients": ["食パン", "バター", "ジャム"],
        "instructions": "パンを焼いてバターやジャムを塗る",
        "tags": ["洋食", "簡単", "朝食"]
    },
    {
        "name": "納豆ご飯",
        "category": "朝食",
        "cooking_time": 5,
        "ingredients": ["ご飯", "納豆", "ネギ", "醤油"],
        "instructions": "納豆をかき混ぜてご飯にのせる",
        "tags": ["和食", "簡単", "朝食"]
    },
    {
        "name": "サラダ",
        "category": "副菜",
        "cooking_time": 10,
        "ingredients": ["レタス", "トマト", "きゅうり", "ドレッシング"],
        "instructions": "野菜を切って盛り付け、ドレッシングをかける",
        "tags": ["洋食", "サラダ"]
    },
    {
        "name": "焼き魚定食",
        "category": "メイン",
        "cooking_time": 20,
        "ingredients": ["アジ", "塩", "大根おろし", "レモン"],
        "instructions": "魚に塩を振って焼く",
        "tags": ["和食", "魚", "定食"]
    },
    {
        "name": "チャーハン",
        "category": "メイン",
        "cooking_time": 15,
        "ingredients": ["ご飯", "卵", "ハム", "ネギ", "醤油"],
        "instructions": "ご飯と具材を強火で炒める",
        "tags": ["中華", "簡単"]
    },
    {
        "name": "うどん",
        "category": "メイン",
        "cooking_time": 15,
        "ingredients": ["うどん", "だし", "ネギ", "天かす"],
        "instructions": "うどんを茹で、温かいだしをかける",
        "tags": ["和食", "麺類"]
    },
    {
        "name": "オムライス",
        "category": "メイン",
        "cooking_time": 25,
        "ingredients": ["ご飯", "鶏肉", "玉ねぎ", "卵", "ケチャップ"],
        "instructions": "チキンライスを作り、卵で包む",
        "tags": ["洋食", "定番"]
    },
    {
        "name": "肉じゃが",
        "category": "メイン",
        "cooking_time": 35,
        "ingredients": ["じゃがいも", "にんじん", "玉ねぎ", "牛肉", "醤油", "みりん"],
        "instructions": "材料を煮込む",
        "tags": ["和食", "定番", "煮物"]
    },
    {
        "name": "焼きそば",
        "category": "メイン",
        "cooking_time": 15,
        "ingredients": ["焼きそば麺", "キャベツ", "豚肉", "ソース"],
        "instructions": "麺と具材を炒めてソースで味付け",
        "tags": ["中華", "簡単"]
    },
    {
        "name": "餃子",
        "category": "副菜",
        "cooking_time": 30,
        "ingredients": ["餃子の皮", "豚ひき肉", "キャベツ", "ニラ", "にんにく"],
        "instructions": "具を包んで焼く",
        "tags": ["中華", "定番"]
    }
]


def create_recipes(table_name, count):
    """レシピデータを作成"""
    table = dynamodb.Table(table_name)
    created_count = 0

    recipes_to_create = SAMPLE_RECIPES[:count]

    for i, recipe_data in enumerate(recipes_to_create):
        recipe = {
            'recipe_id': f'recipe_{str(i+1).zfill(3)}',
            'name': recipe_data['name'],
            'category': recipe_data['category'],
            'cooking_time': recipe_data['cooking_time'],
            'ingredients': recipe_data['ingredients'],
            'instructions': recipe_data['instructions'],
            'tags': recipe_data['tags'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        try:
            table.put_item(Item=recipe)
            print(f"✓ レシピを作成: {recipe['name']}")
            created_count += 1
        except Exception as e:
            print(f"✗ レシピ作成エラー ({recipe['name']}): {str(e)}")

    return created_count


def create_history(table_name, recipes_table_name, days):
    """献立履歴データを作成"""
    table = dynamodb.Table(table_name)
    recipes_table = dynamodb.Table(recipes_table_name)

    # レシピ一覧を取得
    response = recipes_table.scan()
    recipes = response.get('Items', [])

    if not recipes:
        print("エラー: レシピが存在しません。先にレシピを作成してください。")
        return 0

    created_count = 0

    # 過去N日分の履歴を作成
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')

        # ランダムに複数のレシピを選択（各食事に1-3品）
        selected_recipes = random.sample(recipes, min(8, len(recipes)))

        # 朝食用（1-2品）
        breakfast_count = random.randint(1, 2)
        breakfast_recipes = []
        for j in range(breakfast_count):
            if j < len(selected_recipes):
                r = selected_recipes[j]
                breakfast_recipes.append({'recipe_id': r['recipe_id'], 'name': r['name']})

        # 昼食用（1-3品）
        lunch_count = random.randint(1, 3)
        lunch_recipes = []
        for j in range(lunch_count):
            idx = 2 + j
            if idx < len(selected_recipes):
                r = selected_recipes[idx]
                lunch_recipes.append({'recipe_id': r['recipe_id'], 'name': r['name']})

        # 夕食用（2-3品）
        dinner_count = random.randint(2, 3)
        dinner_recipes = []
        for j in range(dinner_count):
            idx = 5 + j
            if idx < len(selected_recipes):
                r = selected_recipes[idx]
                dinner_recipes.append({'recipe_id': r['recipe_id'], 'name': r['name']})

        # 全レシピIDを収集
        all_recipe_ids = []
        all_recipe_ids.extend([r['recipe_id'] for r in breakfast_recipes])
        all_recipe_ids.extend([r['recipe_id'] for r in lunch_recipes])
        all_recipe_ids.extend([r['recipe_id'] for r in dinner_recipes])

        history = {
            'date': date,
            'meals': {
                'breakfast': breakfast_recipes,
                'lunch': lunch_recipes,
                'dinner': dinner_recipes
            },
            'recipes': all_recipe_ids,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        try:
            table.put_item(Item=history)
            print(f"✓ 履歴を作成: {date}")
            created_count += 1
        except Exception as e:
            print(f"✗ 履歴作成エラー ({date}): {str(e)}")

    return created_count


def main():
    parser = argparse.ArgumentParser(description='DynamoDBにサンプルデータを投入')
    parser.add_argument('--recipes', type=int, default=20, help='作成するレシピの数（最大20）')
    parser.add_argument('--history', type=int, default=30, help='作成する履歴の日数')
    parser.add_argument('--recipes-table', default='kondate-recipes', help='レシピテーブル名')
    parser.add_argument('--history-table', default='kondate-menu-history', help='履歴テーブル名')

    args = parser.parse_args()

    print("=" * 60)
    print("献立プランナー - データ投入スクリプト")
    print("=" * 60)

    # レシピを作成
    print(f"\n[1/2] レシピを作成中... (最大{min(args.recipes, len(SAMPLE_RECIPES))}件)")
    recipe_count = create_recipes(args.recipes_table, min(args.recipes, len(SAMPLE_RECIPES)))
    print(f"レシピ作成完了: {recipe_count}件")

    # 献立履歴を作成
    print(f"\n[2/2] 献立履歴を作成中... ({args.history}日分)")
    history_count = create_history(args.history_table, args.recipes_table, args.history)
    print(f"献立履歴作成完了: {history_count}件")

    print("\n" + "=" * 60)
    print("データ投入完了!")
    print(f"  レシピ: {recipe_count}件")
    print(f"  献立履歴: {history_count}件")
    print("=" * 60)


if __name__ == '__main__':
    main()
