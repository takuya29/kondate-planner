#!/usr/bin/env python3
"""
DynamoDBテーブルのすべてのデータを削除するスクリプト

使い方:
  python scripts/clear_dynamodb_data.py --all           # 両方のテーブルをクリア
  python scripts/clear_dynamodb_data.py --recipes       # レシピテーブルのみクリア
  python scripts/clear_dynamodb_data.py --history       # 献立履歴テーブルのみクリア
"""
import argparse
import boto3
import logging
import sys
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# DynamoDB configuration
REGION = "ap-northeast-1"
RECIPES_TABLE = "kondate-recipes"
HISTORY_TABLE = "kondate-menu-history"

dynamodb = boto3.resource("dynamodb", region_name=REGION)


def clear_table(table_name: str, key_name: str) -> int:
    """
    指定されたDynamoDBテーブルのすべてのアイテムを削除

    Args:
        table_name: テーブル名
        key_name: パーティションキーの名前

    Returns:
        削除したアイテム数
    """
    table = dynamodb.Table(table_name)
    deleted_count = 0

    try:
        logger.info(f"'{table_name}' テーブルからデータを削除中...")

        # Scan all items
        # Use ExpressionAttributeNames to handle reserved keywords like 'date'
        response = table.scan(
            ProjectionExpression="#key",
            ExpressionAttributeNames={"#key": key_name}
        )
        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(
                ProjectionExpression="#key",
                ExpressionAttributeNames={"#key": key_name},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        if not items:
            logger.info(f"  テーブルは既に空です")
            return 0

        logger.info(f"  {len(items)} 件のアイテムを削除します...")

        # Delete each item
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={key_name: item[key_name]})
                deleted_count += 1

        logger.info(f"✓ {deleted_count} 件のアイテムを削除しました")
        return deleted_count

    except Exception as e:
        logger.error(f"✗ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return deleted_count


def confirm_deletion(tables: List[str]) -> bool:
    """
    削除操作の確認を求める

    Args:
        tables: 削除対象のテーブル名リスト

    Returns:
        ユーザーが確認した場合True
    """
    logger.warning("=" * 60)
    logger.warning("警告: この操作は取り消せません!")
    logger.warning("=" * 60)
    logger.warning("\n以下のテーブルのすべてのデータが削除されます:")
    for table in tables:
        logger.warning(f"  - {table}")

    response = input("\n本当に削除しますか? (yes/no): ")
    return response.lower() in ["yes", "y"]


def main():
    parser = argparse.ArgumentParser(
        description="DynamoDBテーブルのすべてのデータを削除します"
    )
    parser.add_argument(
        "--all", action="store_true", help="すべてのテーブルをクリア"
    )
    parser.add_argument(
        "--recipes", action="store_true", help="レシピテーブルのみクリア"
    )
    parser.add_argument(
        "--history", action="store_true", help="献立履歴テーブルのみクリア"
    )
    parser.add_argument(
        "--force", action="store_true", help="確認をスキップして強制的に削除"
    )

    args = parser.parse_args()

    # Determine which tables to clear
    tables_to_clear = []
    if args.all:
        tables_to_clear = [
            (RECIPES_TABLE, "name"),
            (HISTORY_TABLE, "date"),
        ]
    else:
        if args.recipes:
            tables_to_clear.append((RECIPES_TABLE, "name"))
        if args.history:
            tables_to_clear.append((HISTORY_TABLE, "date"))

    if not tables_to_clear:
        logger.error("エラー: --all, --recipes, または --history を指定してください")
        parser.print_help()
        sys.exit(1)

    # Confirm deletion
    table_names = [table[0] for table in tables_to_clear]
    if not args.force:
        if not confirm_deletion(table_names):
            logger.info("\n操作をキャンセルしました")
            sys.exit(0)

    # Clear tables
    logger.info("\n" + "=" * 60)
    logger.info("データ削除を開始します")
    logger.info("=" * 60 + "\n")

    total_deleted = 0
    for table_name, key_name in tables_to_clear:
        deleted = clear_table(table_name, key_name)
        total_deleted += deleted

    logger.info("\n" + "=" * 60)
    logger.info("削除完了!")
    logger.info(f"合計: {total_deleted} 件のアイテムを削除しました")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
