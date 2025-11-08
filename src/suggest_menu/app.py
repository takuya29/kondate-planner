import json
import os
import boto3
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-1')

RECIPES_TABLE = os.environ['RECIPES_TABLE']
HISTORY_TABLE = os.environ['HISTORY_TABLE']
MODEL_ID = os.environ['BEDROCK_MODEL_ID']


def decimal_to_float(obj):
    """DynamoDB DecimalをPython標準型に変換"""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def get_all_recipes():
    """全レシピを取得"""
    table = dynamodb.Table(RECIPES_TABLE)
    response = table.scan()
    return decimal_to_float(response.get('Items', []))


def get_recent_history(days=30):
    """過去N日分の献立履歴を取得"""
    table = dynamodb.Table(HISTORY_TABLE)
    history = []

    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        response = table.get_item(Key={'date': date})
        if 'Item' in response:
            history.append(decimal_to_float(response['Item']))

    return history


def build_prompt(recipes, history, days):
    """Claude用のプロンプトを構築"""
    recipe_list = "\n".join([
        f"- {r['recipe_id']}: {r['name']} (カテゴリ: {r.get('category', '未分類')}, "
        f"調理時間: {r.get('cooking_time', '不明')}分)"
        for r in recipes
    ])

    recent_recipes = []
    for h in history:
        if 'recipes' in h:
            recent_recipes.extend(h['recipes'])

    recent_recipes_str = "、".join(set(recent_recipes[-20:])) if recent_recipes else "なし"

    prompt = f"""あなたは栄養と料理に詳しい献立プランナーです。
以下の条件で{days}日分の献立を提案してください。

# 利用可能なレシピ
{recipe_list}

# 最近作った料理（重複を避けるため）
{recent_recipes_str}

# 献立構成の基本ルール

## 朝食（breakfast）
- 1〜2品で構成
- 調理時間は短めに（合計15分以内を目安）
- 例: トースト + 卵焼き、納豆ご飯のみ、など

## 昼食（lunch）
- 1〜3品で構成
- 主食系がメインでも可
- 例: チャーハンのみ、カレーライス + サラダ、など

## 夕食（dinner）
- 2〜3品で構成
- メイン + 汁物 + 副菜のバランスが理想的
- 例: 鮭の塩焼き + 味噌汁 + サラダ

# 制約条件
- 各日3食（朝食、昼食、夕食）を提案
- 各食事は1〜3品のレシピで構成（メイン+汁物+副菜など）
- 最近作った料理はなるべく避ける
- 栄養バランスを考慮（野菜、タンパク質、炭水化物のバランス）
- 調理時間の長い料理ばかりにならないよう配慮
- 1日の中で同じレシピは使用しない
- カテゴリのバランスを考慮（メイン、副菜、汁物など）

# 出力形式
JSON形式で以下のように出力してください。各食事は必ず配列形式で、1つ以上のレシピオブジェクトを含めてください：
{{
  "menu_plan": [
    {{
      "date": "2025-11-07",
      "meals": {{
        "breakfast": [
          {{"recipe_id": "recipe_011", "name": "トースト"}},
          {{"recipe_id": "recipe_010", "name": "卵焼き"}}
        ],
        "lunch": [
          {{"recipe_id": "recipe_003", "name": "ハンバーグ"}},
          {{"recipe_id": "recipe_009", "name": "味噌汁"}},
          {{"recipe_id": "recipe_013", "name": "サラダ"}}
        ],
        "dinner": [
          {{"recipe_id": "recipe_005", "name": "鮭の塩焼き"}},
          {{"recipe_id": "recipe_009", "name": "味噌汁"}}
        ]
      }},
      "notes": "バランスの良い和食中心の献立"
    }}
  ],
  "summary": "{days}日間の献立提案の全体的な特徴や栄養バランスについて"
}}
"""
    return prompt


def call_bedrock(prompt):
    """Amazon Bedrockを呼び出して献立を生成"""
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(request_body)
    )

    response_body = json.loads(response['body'].read())
    content = response_body['content'][0]['text']

    # JSONを抽出（コードブロックがある場合に対応）
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()

    # JSON parsing with error handling
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        logger.error(f"Raw content from Bedrock: {content}")
        raise ValueError(f"Bedrock returned invalid JSON: {str(e)}")


def lambda_handler(event, context):
    """Lambda関数のメインハンドラー"""
    try:
        # リクエストボディを取得
        body = json.loads(event.get('body', '{}'))
        days = body.get('days', 3)  # デフォルト3日分

        if days not in [3, 7]:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'daysは3または7を指定してください'
                }, ensure_ascii=False)
            }

        # データ取得
        recipes = get_all_recipes()
        if not recipes:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'レシピが登録されていません'
                }, ensure_ascii=False)
            }

        history = get_recent_history()

        # プロンプト構築とBedrock呼び出し
        prompt = build_prompt(recipes, history, days)
        result = call_bedrock(prompt)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            }, ensure_ascii=False)
        }
