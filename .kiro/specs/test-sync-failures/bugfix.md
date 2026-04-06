# Bugfix: テスト9件が実装変更に追従していない

## Current Behavior（現在の動作）

`pytest` 実行で9件のテストが失敗する（1455 passed, 9 failed）。

### 証拠（pytest出力 2026-04-06）

**カテゴリA: XSSテスト 3件** (`tests/security/test_xss.py`)
- `test_基本的なスクリプトタグの無害化`: assert 400 == 200
- `test_イベントハンドラの無害化`: assert 400 == 200
- `test_データURIスキームの処理`: assert 400 == 200
- 原因: `routes/chat_routes.py:86-88` の `SecurityUtils.validate_message()` がXSSペイロードを検出し `ValidationError`（400）を返す。テストは旧挙動（サニタイズして200で通過）を期待している。

**カテゴリB: extensionsテスト 2件** (`tests/test_core/test_extensions.py`)
- `test_configなしで初期化`: ValueError: Unrecognized value for SESSION_TYPE: null
- `test_config指定で初期化`: ValueError: Unrecognized value for SESSION_TYPE: null
- 原因: `core/extensions.py:42` の `Session(app)` がmockされておらず、Flask-Sessionが `SESSION_TYPE` 未設定で `ValueError` を発生。

**カテゴリC: chat_feedbackテスト 4件** (`tests/test_routes/test_chat_routes.py`)
- `test_フィードバックを正常に生成できる`: assert 400 == 200
- `test_履歴がない場合エラーを返す`: assert 400 == 404
- `test_レート制限エラーを処理する`: assert 400 == 429
- `test_その他のエラーを処理する`: assert 400 == 503
- 原因: `routes/chat_routes.py:292-293` で `chat_settings` のセッション存在チェックが追加された。テストがセッションに `chat_settings` を設定していないため、全て400で早期returnする。

## Expected Behavior（期待する動作）

- **カテゴリA**: XSSペイロードは `validate_message()` により400で拒否されるのが正しい動作。テストを400期待に修正する。
- **カテゴリB**: `Session(app)` をmockするか、`SESSION_TYPE` を正しく設定してテストが通る。
- **カテゴリC**: テストがセッションに `chat_settings` を設定し、各エンドポイントの本来のロジックをテストできる。
- 全1473テストが0 failuresで通過する。

## Unchanged Behavior（変更しない動作）

- `SecurityUtils.validate_message()` の挙動は変更しない（400拒否が正しい）
- `chat_settings` のセッション存在チェック（292-293行目）は変更しない
- `core/extensions.py` の `Session(app)` 呼び出しは変更しない
- 他の1455件のpassingテストに影響を与えない
- 実装コード（routes/, core/, services/）は一切変更しない
