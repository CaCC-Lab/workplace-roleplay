# API ドキュメント

## 概要

このディレクトリには、職場コミュニケーション練習アプリのAPIドキュメントが含まれています。

## Swagger UI

アプリケーション起動後、以下のURLでSwagger UIにアクセスできます：

```
http://localhost:5000/api/docs/
```

## OpenAPI仕様

OpenAPI 3.0形式の仕様書は以下から取得できます：

- **YAML形式**: `/api/docs/openapi.yaml`
- **JSON形式**: `/api/docs/apispec.json`

## 主要なAPIエンドポイント

### 認証

このAPIはセッションベースの認証を使用します。POSTリクエストにはCSRFトークンが必要です。

1. `/api/csrf-token` からCSRFトークンを取得
2. `X-CSRF-Token` ヘッダーにトークンを設定してリクエスト

### エンドポイント一覧

| カテゴリ | エンドポイント | メソッド | 説明 |
|---------|---------------|----------|------|
| ヘルスチェック | `/health` | GET | アプリ稼働状態確認 |
| セッション | `/api/csrf-token` | GET | CSRFトークン取得 |
| モデル | `/api/models` | GET | 利用可能モデル一覧 |
| 雑談 | `/api/chat` | POST | メッセージ送信 |
| 雑談 | `/api/start_chat` | POST | セッション開始 |
| 雑談 | `/api/clear_history` | POST | 履歴クリア |
| 雑談 | `/api/chat_feedback` | POST | フィードバック取得 |
| シナリオ | `/api/scenarios` | GET | シナリオ一覧 |
| シナリオ | `/api/scenario_chat` | POST | メッセージ送信 |
| シナリオ | `/api/scenario_feedback` | POST | フィードバック取得 |
| 観戦 | `/api/watch/start` | POST | 観戦モード開始 |
| 観戦 | `/api/watch/next` | POST | 次の会話生成 |
| 強み分析 | `/api/strength/analyze` | POST | 強み分析実行 |

## リクエスト例

### 雑談メッセージ送信

```bash
# CSRFトークン取得
TOKEN=$(curl -s http://localhost:5000/api/csrf-token | jq -r '.csrf_token')

# メッセージ送信
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $TOKEN" \
  -d '{"message": "こんにちは、今日の天気はどうですか？"}'
```

### シナリオ一覧取得

```bash
curl http://localhost:5000/api/scenarios
```

## エラーレスポンス

エラー発生時は以下の形式でレスポンスが返されます：

```json
{
  "error": "エラーメッセージ",
  "error_id": "エラー追跡用ID"
}
```

## バージョン

- API Version: 2.0.0
- OpenAPI Specification: 3.0.3
