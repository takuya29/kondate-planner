# 献立作成補助ツール

AWS SAMを使った個人利用の献立提案アプリケーションです。Amazon Bedrock AgentとClaude Sonnet 4.5を使って、Slack経由で自然な会話形式で献立を提案します。

## 機能概要

- **Slack経由の対話型献立提案**: AWS Chatbotを通じてSlackから自然言語で献立をリクエスト
- **AI献立生成**: Bedrock Agentが過去の履歴を考慮してバランスの良い献立を提案
- **履歴管理**: 過去の献立を参照し、同じレシピの繰り返しを避ける
- **明示的な保存確認**: ユーザーが承認した献立のみを保存

## システムアーキテクチャ

### 全体構成

```mermaid
graph TB
    User[ユーザー<br/>Slack]

    subgraph AWS["AWS Cloud (ap-northeast-1)"]
        Chatbot[AWS Chatbot<br/>Slack統合]

        subgraph Bedrock["Amazon Bedrock"]
            Agent[Bedrock Agent<br/>kondate-menu-planner]
            Claude[Claude Sonnet 4.5<br/>Inference Profile]
        end

        LambdaLayer[Lambda Layer<br/>共通ライブラリ]

        subgraph Lambda["Action Lambda Functions"]
            GetRecipes[レシピ取得<br/>GetRecipesAction]
            GetHistory[履歴取得<br/>GetHistoryAction]
            SaveMenu[献立保存<br/>SaveMenuAction]
        end

        subgraph Storage["データストア"]
            RecipesDB[(DynamoDB<br/>kondate-recipes)]
            HistoryDB[(DynamoDB<br/>kondate-menu-history)]
        end

        S3[S3 Bucket<br/>OpenAPIスキーマ]
    end

    User -->|メッセージ| Chatbot
    Chatbot -->|会話| Agent

    Agent -->|推論| Claude
    Agent -->|アクション呼び出し| GetRecipes
    Agent -->|アクション呼び出し| GetHistory
    Agent -->|アクション呼び出し| SaveMenu

    Agent -.->|スキーマ参照| S3

    LambdaLayer --> GetRecipes
    LambdaLayer --> GetHistory
    LambdaLayer --> SaveMenu

    GetRecipes -->|Scan| RecipesDB
    GetHistory -->|GetItem| HistoryDB
    SaveMenu -->|PutItem| HistoryDB

    Chatbot -->|応答| User
```

AWS ChatbotがSlack統合を担当し、Bedrock Agentが自然言語理解とLambdaアクションの実行を統括します。

### 対話フロー例

```mermaid
sequenceDiagram
    participant User as ユーザー(Slack)
    participant Chatbot as AWS Chatbot
    participant Agent as Bedrock Agent
    participant GetRecipes as GetRecipesAction
    participant GetHistory as GetHistoryAction
    participant SaveMenu as SaveMenuAction
    participant RecipesDB as recipes テーブル
    participant HistoryDB as menu_history テーブル

    User->>Chatbot: @AWS 3日分の献立を提案して
    Chatbot->>Agent: ユーザーリクエスト

    Agent->>GetRecipes: get_recipes()
    GetRecipes->>RecipesDB: Scan
    RecipesDB-->>GetRecipes: 全レシピ
    GetRecipes-->>Agent: レシピリスト

    Agent->>GetHistory: get_history(days=30)
    GetHistory->>HistoryDB: 過去30日分取得
    HistoryDB-->>GetHistory: 献立履歴
    GetHistory-->>Agent: 履歴リスト

    Agent->>Agent: 献立プラン生成<br/>(Claude推論)
    Agent-->>Chatbot: 3日分の献立案
    Chatbot-->>User: 献立を表示<br/>「この献立で保存しますか?」

    User->>Chatbot: はい、保存して
    Chatbot->>Agent: 保存確認

    Agent->>SaveMenu: save_menu(date, meals)
    SaveMenu->>HistoryDB: PutItem
    HistoryDB-->>SaveMenu: 保存完了
    SaveMenu-->>Agent: 成功

    Agent-->>Chatbot: 保存完了メッセージ
    Chatbot-->>User: 「献立を保存しました」
```

## 技術スタック

- **Lambda**: Python 3.12, ARM64
- **Bedrock Agent**: Claude Sonnet 4.5 (Inference Profile)
- **AWS Chatbot**: Slack統合
- **DynamoDB**: 2テーブル（recipes, menu_history）
- **S3**: OpenAPIスキーマ保存
- **リージョン**: ap-northeast-1（東京）

## プロジェクト構成

```
kondate-planner/
├── template.yaml              # SAMテンプレート（OpenAPIスキーマ含む）
├── samconfig.toml             # デプロイ設定
├── AGENTS.md                  # アーキテクチャドキュメント（詳細）
├── CLAUDE.md -> AGENTS.md     # シンボリックリンク
├── src/
│   ├── agent_actions/         # Bedrock Agent用Lambda
│   │   ├── get_recipes/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   ├── get_history/
│   │   │   ├── app.py
│   │   │   └── requirements.txt
│   │   └── save_menu/
│   │       ├── app.py
│   │       └── requirements.txt
│   ├── layers/                # 共通Lambda Layer
│   │   └── common/
│   │       └── utils.py
│   └── schemas/               # OpenAPIスキーマ（参照用、実際はtemplate.yamlに埋め込み）
│       ├── get-recipes.yaml
│       ├── get-history.yaml
│       └── save-menu.yaml
├── scripts/
│   └── seed_data.py           # データ投入スクリプト
└── README.md
```

## セットアップ

### 前提条件

- AWS CLI設定済み
- AWS SAM CLI インストール済み
- Python 3.12
- Amazon Bedrockのモデルアクセス許可（Claude Sonnet 4.5）
- Slackワークスペース（AWS Chatbot連携用）

### 1. Bedrock モデルアクセスの有効化

AWSコンソールで以下を実行：
1. Amazon Bedrockコンソールを開く
2. 「Model access」に移動
3. 「Anthropic Claude Sonnet 4.5」のアクセスを有効化

### 2. Slackワークスペースの認証（初回のみ）

**重要**: デプロイ前に、Slackワークスペースを AWS Chatbot に認証する必要があります：

1. **AWS Chatbot Console** → **Configure new client**
2. **Slack** を選択
3. **Configure** をクリックしてSlackワークスペースを認証
4. 認証後、**Slack Workspace ID** をメモ（コンソールに表示されます）
5. **Slack Channel ID** を取得：
   - Slackでチャンネル名を右クリック
   - **Copy Link** を選択
   - URLの最後の部分がチャンネルID（例: `C12345ABCDE`）

### 3. ビルドとデプロイ

```bash
# ビルド
sam build

# デプロイ（Slack情報を含む）
sam deploy --parameter-overrides \
  SlackWorkspaceId=YOUR_WORKSPACE_ID \
  SlackChannelId=YOUR_CHANNEL_ID

# または、samconfig.toml に追加してから：
# parameter_overrides = "SlackWorkspaceId=XXX SlackChannelId=YYY"
sam deploy
```

**注意**: 公開リポジトリの場合、Slack IDを `samconfig.toml` にコミットしないでください。コマンドラインで指定するか、AWS Systems Manager Parameter Store を使用してください。

### 4. デプロイの確認

デプロイが完了すると、以下が自動的に作成されます：

- ✅ Bedrock Agent（`kondate-planner-agent`）
- ✅ Agent Alias（`production`）
- ✅ 3つのAction Lambda関数
- ✅ DynamoDBテーブル（recipes、menu-history）
- ✅ Developer Q Slack Channel設定
- ✅ IAMロールと権限

```bash
# デプロイ確認
aws cloudformation describe-stacks --stack-name kondate-planner \
  --query 'Stacks[0].Outputs[?OutputKey==`DeveloperQSlackChannelArn`].OutputValue' --output text
```

### 5. Bedrockエージェントの確認（オプション）

エージェントはCloudFormationで自動作成されますが、コンソールで確認できます：

1. **Amazon Bedrockコンソール** → **Agents**
2. `kondate-planner-agent` を選択
3. アクショングループが3つ設定されていることを確認
4. テストインターフェースで動作確認可能

**注意**: エージェント指示を変更する場合は `template.yaml` を編集し、再デプロイしてください。コンソールでの変更は次回デプロイ時に上書きされます。

~~### 4. Bedrock Agentの作成~~

~~AWSコンソールでBedrockエージェントを作成します。~~

~~#### 4-1. エージェントの基本設定~~

~~1. Amazon Bedrockコンソール → Agents → Create agent~~
~~2. **エージェント名**: `kondate-menu-planner`~~
~~3. **説明**: `日本料理の献立計画アシスタント`~~
~~4. **モデル**: `Claude Sonnet 4.5`~~
~~5. **IAMロール**: デプロイ時の出力 `BedrockAgentRoleArn` を使用~~

~~#### 4-2. エージェント指示の設定~~

### 6. サンプルデータの投入

```bash
# boto3をインストール（未インストールの場合）
pip install boto3

# サンプルデータ投入（レシピ20件、履歴30日分）
python scripts/seed_data.py --recipes 20 --history 30
```

### 7. Slackで動作確認

設定したSlackチャンネルで:

```
@AWS 3日分の献立を提案して
```

エージェントが以下を実行するはずです:
1. レシピを取得
2. 最近の履歴を取得
3. バランスの良い3日分の献立を生成
4. 保存前に確認を求める

## 使い方

### 献立の提案を受ける

```
@AWS 7日分の献立を提案してください
```

### 最近の献立を確認

```
@AWS 最近の献立を見せて
```

### 特定カテゴリのレシピを見る

```
@AWS 主菜のレシピを教えて
```

### 献立を保存

エージェントが献立を提案した後:

```
保存して
```

または

```
いいえ、もっと魚料理を増やして
```

## データベーススキーマ

### recipesテーブル

| フィールド | 型 | 説明 |
|-----------|-----|------|
| recipe_id | String (PK) | レシピID |
| name | String | レシピ名 |
| category | String | カテゴリ（主菜、副菜、汁物、主食、デザート） |
| cooking_time | Number | 調理時間（分） |
| ingredients | List | 材料リスト |
| recipe_url | String | レシピのURL |
| tags | List | タグリスト |
| created_at | String | 作成日時 |
| updated_at | String | 更新日時 |

### menu_historyテーブル

| フィールド | 型 | 説明 |
|-----------|-----|------|
| date | String (PK) | 日付（YYYY-MM-DD） |
| meals | Map | 食事情報。breakfast/lunch/dinnerの各配列にレシピオブジェクト（recipe_id, name）を含む |
| recipes | List | 使用したレシピIDのフラットリスト（重複排除用） |
| notes | String | メモ（オプション） |
| created_at | String | 作成日時 |
| updated_at | String | 更新日時 |

## ローカル開発とテスト

### Lambda関数を個別にテスト

```bash
# レシピ取得のテスト
echo '{"category": "主菜"}' | sam local invoke GetRecipesActionFunction

# 履歴取得のテスト
echo '{"days": 7}' | sam local invoke GetHistoryActionFunction

# 献立保存のテスト
echo '{
  "date": "2025-11-09",
  "meals": {
    "breakfast": [{"recipe_id": "abc", "name": "味噌汁"}],
    "lunch": [{"recipe_id": "def", "name": "カレー"}],
    "dinner": [{"recipe_id": "ghi", "name": "焼き魚"}]
  }
}' | sam local invoke SaveMenuActionFunction
```

注: ローカルテストにはAWSのDynamoDBテーブルが必要です（DynamoDB Localは未対応）

## トラブルシューティング

### エージェントがアクションを見つけられない

1. OpenAPIスキーマがS3に正しくアップロードされているか確認
2. エージェントのアクショングループ設定でスキーマパスが正しいか確認
3. エージェントを「Prepare」し直す

### Lambdaが呼び出されない

1. Lambda関数のリソースベースポリシーで `bedrock.amazonaws.com` からの呼び出しが許可されているか確認（SAMテンプレートで自動設定）
2. CloudWatch Logsでエラーを確認

### Bedrockモデルアクセスエラー

**エラー**: "The provided model identifier is invalid"

**対処法**:
- Claude Sonnet 4.5は **Inference Profile経由でのみ** 呼び出し可能
- 正しいモデルID: `jp.anthropic.claude-sonnet-4-5-20250929-v1:0`

**IAM権限**: 以下のすべてに対する権限が必要:
```yaml
Resource:
  - 'arn:aws:bedrock:ap-northeast-1:${AccountId}:inference-profile/jp.anthropic.claude-sonnet-4-5-20250929-v1:0'
  - 'arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0'
  - 'arn:aws:bedrock:ap-northeast-3::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0'
```

### AWS Chatbotが応答しない

1. Chatbot設定でBedrockエージェントが正しく選択されているか確認
2. ChatbotのIAMロールがエージェント呼び出し権限を持っているか確認
3. Slackチャンネルで `@AWS` メンションをつけているか確認

## デプロイチェックリスト

新しい環境にデプロイする際（すべて自動化済み）:

### 初回セットアップ
- [ ] Amazon Bedrockで Claude Sonnet 4.5 のモデルアクセスを有効化
- [ ] AWS Chatbot ConsoleでSlackワークスペースを認証
- [ ] Slack Workspace IDとChannel IDを取得

### デプロイ
- [ ] `sam build` を実行
- [ ] `sam deploy --parameter-overrides SlackWorkspaceId=XXX SlackChannelId=YYY` を実行
- [ ] デプロイ完了を確認（すべてのリソースが自動作成される）

### 動作確認
- [ ] Slackでテスト: `@AWS 3日分の献立を提案して`
- [ ] （オプション）Bedrockコンソールでエージェントを確認

### データ投入
- [ ] サンプルデータを投入: `python scripts/seed_data.py --recipes 20 --history 30`

**注意**: Bedrock Agent、アクショングループ、Slack設定はすべてCloudFormationで自動管理されます。手動設定は不要です。

## 今後の拡張予定

- レシピデータソースをDynamoDBからNotion APIに移行
- 大規模データセット向けのページネーション対応
- 複数週の献立計画サポート
- レシピ材料を使った栄養分析
- 食事制限や好みのサポート

## クリーンアップ

すべてのリソースを削除する場合:

```bash
# SAMスタックの削除
sam delete

# 手動作成したリソースも削除
# - Bedrock Agent（コンソールから）
# - AWS Chatbot設定（コンソールから）
```

## 参考リンク

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Amazon Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AWS Chatbot Documentation](https://docs.aws.amazon.com/chatbot/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)

## 詳細ドキュメント

アーキテクチャの詳細やLambda関数の実装詳細については、[AGENTS.md](./AGENTS.md) を参照してください。
