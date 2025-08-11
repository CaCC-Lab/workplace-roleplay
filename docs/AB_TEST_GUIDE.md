# A/Bテストガイド

## 概要

このドキュメントは、Workplace RoleplayアプリケーションのA/Bテスト機能について説明します。
既存システムに影響を与えずに、新しいサービス層を段階的にテスト・導入できます。

## 🚀 クイックスタート

### 1. 環境変数の設定

```bash
# .env.ab_testを.envにコピー
cp .env.ab_test .env

# 必要に応じて編集
vim .env
```

### 2. アプリケーション起動

```bash
python app.py
```

起動時に以下のメッセージが表示されれば成功：
```
✅ A/Bテストエンドポイントを登録しました (/api/v2/*)
```

### 3. 新エンドポイントのテスト

```bash
# ヘルスチェック
curl http://localhost:5001/api/v2/health

# 設定確認
curl http://localhost:5001/api/v2/config

# 新チャットAPI（v2）
curl -X POST http://localhost:5001/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは"}'
```

## 📊 エンドポイント一覧

### 既存エンドポイント（変更なし）
- `POST /api/chat` - 既存のチャットAPI
- `POST /api/scenario_chat` - 既存のシナリオAPI
- `POST /api/watch/start` - 既存の観戦モードAPI

### 新規エンドポイント（A/Bテスト用）
- `GET /api/v2/health` - ヘルスチェック
- `GET /api/v2/config` - 現在の設定表示
- `POST /api/v2/chat` - 新サービスを使用したチャット
- `POST /api/v2/chat/compare` - 新旧サービスの比較（開発用）

## 🔧 設定オプション

### SERVICE_MODE

| モード | 説明 | 用途 |
|--------|------|------|
| `legacy` | 既存実装のみ | 通常運用（デフォルト） |
| `parallel` | 並行稼働 | A/Bテスト |
| `canary` | カナリアリリース | 段階的移行 |
| `new` | 新実装のみ | 完全移行後 |

### フィーチャーフラグ

```bash
# 個別サービスの有効化
USE_NEW_CHAT_SERVICE=true     # チャットサービス
USE_NEW_SCENARIO_SERVICE=true  # シナリオサービス
USE_NEW_WATCH_SERVICE=true     # 観戦モード
```

### A/Bテスト設定

```bash
AB_TEST_ENABLED=true    # A/Bテスト有効化
AB_TEST_RATIO=0.1      # 10%のユーザーで新サービス
COMPARE_MODE=true      # 比較モード有効化
LOG_DIFFERENCES=true   # 差分ログ出力
```

## 🧪 比較エンドポイントの使用

### 新旧サービスの出力比較

```python
import requests

# 比較エンドポイント呼び出し
response = requests.post('http://localhost:5001/api/v2/chat/compare', 
    json={'message': 'テストメッセージ'}
)

result = response.json()
print(f"Legacy: {result['legacy']['response'][:100]}")
print(f"New: {result['new']['response'][:100]}")
print(f"同一: {result['comparison']['identical']}")
print(f"時間差: {result['comparison']['time_diff']}秒")
```

### 比較結果の構造

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "message": "入力メッセージ",
  "legacy": {
    "response": "旧サービスの応答",
    "length": 123,
    "time": 0.5
  },
  "new": {
    "response": "新サービスの応答",
    "length": 125,
    "time": 0.4
  },
  "comparison": {
    "identical": false,
    "time_diff": -0.1,
    "time_ratio": 0.8,
    "length_diff": 2
  },
  "total_time": 0.9
}
```

## 📈 段階的移行プロセス

### Phase 1: 開発環境でテスト（現在）
```bash
SERVICE_MODE=parallel
COMPARE_MODE=true
```

### Phase 2: カナリアリリース（10%）
```bash
SERVICE_MODE=canary
AB_TEST_RATIO=0.1
```

### Phase 3: 段階的拡大（50%）
```bash
SERVICE_MODE=canary
AB_TEST_RATIO=0.5
```

### Phase 4: 完全移行
```bash
SERVICE_MODE=new
```

## 🔍 モニタリング

### ログの確認
```bash
# 差分が検出された場合のログ
tail -f app.log | grep "A/B Test Difference"
```

### パフォーマンス比較
```python
# 自動テストスクリプト
python tests/test_ab_comparison.py
```

## ⚠️ 注意事項

1. **既存システムへの影響なし**: 新エンドポイントは `/api/v2/*` に配置され、既存の `/api/*` には一切影響しません

2. **ロールバック可能**: 問題が発生した場合は `SERVICE_MODE=legacy` に戻すだけです

3. **セッション共有**: 新旧サービスは同じFlask-Sessionを使用するため、セッションデータは共有されます

## 🧪 テスト実行

```bash
# A/Bテストのテスト実行
pytest tests/test_ab_comparison.py -v

# カバレッジ付き
pytest tests/test_ab_comparison.py --cov=routes.ab_test_routes --cov-report=html
```

## 🐛 トラブルシューティング

### ImportError: No module named 'routes.ab_test_routes'
```bash
# Pythonパスを確認
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 新エンドポイントが404
```bash
# Blueprintが登録されているか確認
python -c "from app import app; print(app.url_map)"
```

### セッションエラー
```bash
# Redis接続を確認（Redisを使用している場合）
redis-cli ping
```

## 📚 関連ドキュメント

- [SYSTEM_DESIGN_V3.md](./SYSTEM_DESIGN_V3.md) - システム設計書
- [services/README.md](../services/README.md) - サービス層の詳細
- [config/README.md](../config/README.md) - 設定管理の詳細