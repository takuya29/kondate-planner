#!/usr/bin/env python3
"""
Notionデータソースから データを取得してDynamoDBに投入するスクリプト (v2)
ユーザーのNotionデータベース構造に合わせてカスタマイズ済み

使い方:
  python scripts/migrate_from_notion_v2.py
"""
import boto3
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict

try:
    from dotenv import load_dotenv
    from notion_client import Client
except ImportError:
    print("Error: 必要なパッケージがインストールされていません")
    print("インストールコマンド: pip install -r scripts/requirements.txt")
    sys.exit(1)

# .env.localファイルを読み込む
env_path = Path(__file__).parent / '.env.local'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✓ 環境変数を読み込みました: {env_path}\n")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# DynamoDBクライアント
dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")


class NotionDataSourceMigrator:
    """Notionデータソースから DynamoDBへのデータ移行を管理するクラス"""

    def __init__(self, notion_api_key: str):
        self.notion = Client(auth=notion_api_key)
        self.recipe_id_map = {}  # Notion page ID → DynamoDB recipe_id のマッピング

    def fetch_pages_from_data_source(self, data_source_id: str) -> List[Dict]:
        """データソースIDに属するすべてのページを取得"""
        logger.info(f"データソースからページを取得中: {data_source_id}")

        # データソースIDをフォーマット
        if '-' not in data_source_id and len(data_source_id) == 32:
            data_source_id = f"{data_source_id[0:8]}-{data_source_id[8:12]}-{data_source_id[12:16]}-{data_source_id[16:20]}-{data_source_id[20:32]}"

        all_pages = []
        has_more = True
        start_cursor = None

        try:
            while has_more:
                # すべてのページを検索
                query_params = {
                    "filter": {"property": "object", "value": "page"},
                    "page_size": 100
                }
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response = self.notion.search(**query_params)

                # このデータソースに属するページのみフィルター
                for page in response.get('results', []):
                    parent = page.get('parent', {})
                    if parent.get('type') == 'data_source_id' and parent.get('data_source_id') == data_source_id:
                        all_pages.append(page)

                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')

            logger.info(f"✓ {len(all_pages)} 件のページを取得しました")
            return all_pages

        except Exception as e:
            logger.error(f"✗ ページ取得エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def parse_recipe(self, page: Dict) -> Optional[Dict[str, Any]]:
        """
        Notionレシピページを DynamoDB形式に変換

        Notion構造:
        - Name (title) → name
        - 分類 (select) → category
        - 材料 (multi_select) → ingredients
        - URL (url) → recipe_url
        """
        try:
            props = page["properties"]
            page_id = page["id"]

            # 名前 (title)
            name = self._get_title(props.get("Name"))
            if not name:
                logger.warning(f"レシピ名が見つかりません: {page_id}")
                return None

            # recipe_idを生成 (ページIDの短縮版)
            recipe_id = f"recipe_{page_id.replace('-', '')[:12]}"

            # ページIDとrecipe_idのマッピングを保存
            self.recipe_id_map[page_id] = recipe_id

            # 分類 (select)
            category = self._get_select(props.get("分類")) or "その他"

            # 材料 (multi_select)
            ingredients = self._get_multi_select(props.get("材料"))

            # URL (url)
            recipe_url = self._get_url(props.get("URL")) or ""

            # タグは空配列
            tags = []

            # 調理時間はデフォルト0
            cooking_time = 0

            return {
                "recipe_id": recipe_id,
                "name": name,
                "category": category,
                "cooking_time": cooking_time,
                "ingredients": ingredients,
                "recipe_url": recipe_url,
                "tags": tags,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"✗ レシピ解析エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def parse_meal_plan(self, pages: List[Dict]) -> List[Dict[str, Any]]:
        """
        Notion献立ページ群をDynamoDB形式に変換

        Notion構造:
        - Date (date) → date
        - meal (select) → breakfast/lunch/dinner の識別
        - recipes (relation) → 関連するレシピページ
        - memo (title) → notes
        """
        # 日付ごとにグループ化
        meals_by_date = defaultdict(lambda: {"breakfast": [], "lunch": [], "dinner": []})

        for page in pages:
            try:
                props = page["properties"]

                # 日付取得
                date = self._get_date(props.get("Date"))
                if not date:
                    logger.warning(f"日付が見つかりません: {page['id']}")
                    continue

                # 食事タイプ (meal select)
                meal_type = self._get_select(props.get("meal"))
                if not meal_type:
                    logger.warning(f"食事タイプが見つかりません: {page['id']} (日付: {date})")
                    continue

                # 食事タイプを正規化 (朝食/昼食/夕食 → breakfast/lunch/dinner)
                meal_key = self._normalize_meal_type(meal_type)
                if not meal_key:
                    logger.warning(f"不明な食事タイプ: {meal_type}")
                    continue

                # 関連レシピ (relation)
                recipe_relations = self._get_relation(props.get("recipes"))

                # レシピ情報を取得
                recipe_items = []
                for recipe_page_id in recipe_relations:
                    # マップからrecipe_idを取得
                    recipe_id = self.recipe_id_map.get(recipe_page_id)
                    if recipe_id:
                        # レシピ名を取得するためにページを取得
                        try:
                            recipe_page = self.notion.pages.retrieve(page_id=recipe_page_id)
                            recipe_name = self._get_title(recipe_page["properties"].get("Name"))
                            if recipe_name:
                                recipe_items.append({
                                    "recipe_id": recipe_id,
                                    "name": recipe_name
                                })
                        except Exception as e:
                            logger.warning(f"レシピページ取得エラー: {recipe_page_id} - {str(e)}")

                # この日付の食事に追加
                meals_by_date[date][meal_key].extend(recipe_items)

            except Exception as e:
                logger.error(f"✗ 献立解析エラー: {str(e)}")
                import traceback
                traceback.print_exc()

        # DynamoDB形式に変換
        history_items = []
        for date, meals in meals_by_date.items():
            # 全レシピIDを収集
            all_recipe_ids = []
            for meal_recipes in meals.values():
                all_recipe_ids.extend([r["recipe_id"] for r in meal_recipes])

            history_items.append({
                "date": date,
                "meals": meals,
                "recipes": all_recipe_ids,
                "notes": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            })

        return history_items

    # ヘルパーメソッド

    def _get_title(self, prop: Optional[Dict]) -> str:
        """タイトルプロパティから値を取得"""
        if not prop or prop.get("type") != "title":
            return ""
        title_list = prop.get("title", [])
        return "".join([t.get("plain_text", "") for t in title_list])

    def _get_select(self, prop: Optional[Dict]) -> Optional[str]:
        """セレクトプロパティから値を取得"""
        if not prop or prop.get("type") != "select":
            return None
        select_obj = prop.get("select")
        return select_obj.get("name") if select_obj else None

    def _get_multi_select(self, prop: Optional[Dict]) -> List[str]:
        """マルチセレクトプロパティから値を取得"""
        if not prop or prop.get("type") != "multi_select":
            return []
        multi_select_list = prop.get("multi_select", [])
        return [item.get("name") for item in multi_select_list if item.get("name")]

    def _get_url(self, prop: Optional[Dict]) -> Optional[str]:
        """URLプロパティから値を取得"""
        if not prop or prop.get("type") != "url":
            return None
        return prop.get("url")

    def _get_date(self, prop: Optional[Dict]) -> Optional[str]:
        """dateプロパティから値を取得（YYYY-MM-DD形式）"""
        if not prop or prop.get("type") != "date":
            return None
        date_obj = prop.get("date")
        if not date_obj:
            return None
        return date_obj.get("start")  # YYYY-MM-DD形式

    def _get_relation(self, prop: Optional[Dict]) -> List[str]:
        """relationプロパティからページIDのリストを取得"""
        if not prop or prop.get("type") != "relation":
            return []
        relation_list = prop.get("relation", [])
        return [item.get("id") for item in relation_list if item.get("id")]

    def _normalize_meal_type(self, meal_type: str) -> Optional[str]:
        """食事タイプを正規化"""
        meal_type_lower = meal_type.lower()

        if "朝" in meal_type or "breakfast" in meal_type_lower:
            return "breakfast"
        elif "昼" in meal_type or "lunch" in meal_type_lower:
            return "lunch"
        elif "夕" in meal_type or "夜" in meal_type or "dinner" in meal_type_lower:
            return "dinner"
        else:
            return None


def insert_recipes_to_dynamodb(recipes: List[Dict], table_name: str) -> int:
    """レシピをDynamoDBに挿入"""
    table = dynamodb.Table(table_name)
    created_count = 0

    for recipe in recipes:
        try:
            table.put_item(Item=recipe)
            logger.info(f"✓ レシピを挿入: {recipe['name']}")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ レシピ挿入エラー ({recipe['name']}): {str(e)}")

    return created_count


def insert_history_to_dynamodb(history_items: List[Dict], table_name: str) -> int:
    """献立履歴をDynamoDBに挿入"""
    table = dynamodb.Table(table_name)
    created_count = 0

    for history in history_items:
        try:
            table.put_item(Item=history)
            logger.info(f"✓ 献立履歴を挿入: {history['date']}")
            created_count += 1
        except Exception as e:
            logger.error(f"✗ 献立履歴挿入エラー ({history['date']}): {str(e)}")

    return created_count


def main():
    notion_key = os.getenv("NOTION_API_KEY")
    recipes_ds_id = os.getenv("NOTION_RECIPES_DB_ID")
    history_ds_id = os.getenv("NOTION_HISTORY_DB_ID")

    if not notion_key:
        logger.error("エラー: NOTION_API_KEY が設定されていません")
        sys.exit(1)

    if not recipes_ds_id or not history_ds_id:
        logger.error("エラー: データソースIDが設定されていません")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Notion → DynamoDB データ移行スクリプト v2")
    logger.info("=" * 60)

    migrator = NotionDataSourceMigrator(notion_key)

    # レシピを移行
    logger.info("\n[1/2] レシピを移行中...")
    recipe_pages = migrator.fetch_pages_from_data_source(recipes_ds_id)

    recipes = []
    for page in recipe_pages:
        recipe = migrator.parse_recipe(page)
        if recipe:
            recipes.append(recipe)

    recipe_count = 0
    if recipes:
        recipe_count = insert_recipes_to_dynamodb(recipes, "kondate-recipes")
        logger.info(f"レシピ移行完了: {recipe_count}件")

    # 献立履歴を移行
    logger.info(f"\n[2/2] 献立履歴を移行中...")
    history_pages = migrator.fetch_pages_from_data_source(history_ds_id)
    history_items = migrator.parse_meal_plan(history_pages)

    history_count = 0
    if history_items:
        history_count = insert_history_to_dynamodb(history_items, "kondate-menu-history")
        logger.info(f"献立履歴移行完了: {history_count}件")

    logger.info("\n" + "=" * 60)
    logger.info("データ移行完了!")
    logger.info(f"  レシピ: {recipe_count}件")
    logger.info(f"  献立履歴: {history_count}件")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
