AWSのSAMを使って献立作成補助ツールのAPIを開発したいです。
以下の構成でプロジェクトを作成してください：

# プロジェクト概要
- 個人利用の献立提案API
- レシピ約100件、献立履歴約100日分のデータを扱う
- Amazon Bedrock (Claude)を使って献立を提案

# 必要なファイル構成
kondate-planner/
├── template.yaml          # SAMテンプレート
├── samconfig.toml         # デプロイ設定
├── src/
│   ├── suggest_menu/      # 献立提案Lambda
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── get_recipes/       # レシピ一覧取得Lambda
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── create_recipe/     # レシピ作成Lambda
│   │   ├── app.py
│   │   └── requirements.txt
│   └── save_history/      # 献立履歴保存Lambda
│       ├── app.py
│       └── requirements.txt
├── scripts/
│   └── seed_data.py       # データ投入スクリプト
└── README.md

# 主な機能
1. POST /suggest - 献立提案（3日分または7日分）
2. GET /recipes - レシピ一覧取得
3. POST /recipes - レシピ作成
4. POST /history - 献立履歴保存
5. GET /history - 献立履歴取得

# 技術スタック
- Lambda (Python 3.12)
- API Gateway
- DynamoDB (2テーブル: recipes, menu_history)
- Amazon Bedrock (Claude Sonnet 4.5)
- リージョン: ap-northeast-1

プロジェクトを作成して、まずは基本的な構造を整えてください。
その後、ローカルでテストできるようにしましょう。
