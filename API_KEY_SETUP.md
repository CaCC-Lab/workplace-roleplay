# 複数のGoogle APIキーの設定方法

## 概要

このアプリケーションは、複数のGoogle APIキーをローテーションして使用することで、無料枠の制限を効果的に活用できます。

## 設定方法

### 1. 環境変数の設定

`.env`ファイルに以下のように複数のAPIキーを設定します：

```env
# メインのAPIキー（必須）
GOOGLE_API_KEY=your_main_api_key_here

# 追加のAPIキー（オプション、最大9個まで）
GOOGLE_API_KEY_1=your_second_api_key_here
GOOGLE_API_KEY_2=your_third_api_key_here
GOOGLE_API_KEY_3=your_fourth_api_key_here
# ... GOOGLE_API_KEY_9まで設定可能
```

### 2. 複数のGoogleアカウントでAPIキーを作成

1. 各Googleアカウントで[Google AI Studio](https://aistudio.google.com/)にアクセス
2. 「Get API key」をクリック
3. 新しいAPIキーを作成
4. 各アカウントで作成したAPIキーを上記の環境変数に設定

### 3. APIキーの制限

- **無料枠**: 各APIキーあたり
  - 1分あたり15リクエスト
  - 1日あたり1,500リクエスト
  
- **3つのAPIキーを使用した場合**:
  - 1分あたり最大45リクエスト
  - 1日あたり最大4,500リクエスト

### 4. 動作確認

APIキーの状態を確認するには、以下のエンドポイントにアクセスします：

```bash
curl http://localhost:5001/api/key_status
```

レスポンス例：
```json
{
  "total_keys": 3,
  "keys": [
    {
      "index": 0,
      "key_suffix": "abc123",
      "usage_count": 150,
      "error_count": 0,
      "is_blocked": false,
      "blocked_until": null,
      "last_used": 1717123456.789
    },
    {
      "index": 1,
      "key_suffix": "def456",
      "usage_count": 120,
      "error_count": 1,
      "is_blocked": false,
      "blocked_until": null,
      "last_used": 1717123450.123
    }
  ]
}
```

## 機能詳細

### 自動ローテーション

- 使用回数が最も少ないAPIキーを自動的に選択
- レート制限エラーが発生したキーは60秒間ブロック
- 4秒間隔でリクエストを分散（15リクエスト/分の制限に対応）

### エラーハンドリング

- `429 Too Many Requests`エラーを検出して自動的に別のキーに切り替え
- ブロックされたキーは一定時間後に自動的に復活
- 全てのキーがブロックされた場合は、最も早く復活するキーを使用

### 使用状況の追跡

- 各キーの使用回数を記録
- エラー発生回数を追跡
- 最終使用時刻を記録

## セキュリティ上の注意

1. APIキーは絶対に公開リポジトリにコミットしないでください
2. `.env`ファイルは`.gitignore`に含まれていることを確認してください
3. 本番環境では環境変数を安全に管理してください

## トラブルシューティング

### エラー: "No available API keys"

全てのAPIキーがレート制限に達している可能性があります。以下を確認してください：

1. `/api/key_status`エンドポイントで各キーの状態を確認
2. ブロックされているキーがある場合は、`blocked_until`の時刻まで待機
3. 新しいAPIキーを追加することを検討

### エラー: "insufficient_quota"

該当のAPIキーの1日の上限に達しています。以下の対応が可能です：

1. 他のAPIキーがまだ利用可能か確認
2. 翌日（太平洋時間の午前0時）まで待機
3. 追加のGoogleアカウントでAPIキーを作成