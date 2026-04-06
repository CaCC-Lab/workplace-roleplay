# Bugfix: pytest warning 8件の解消

## Current Behavior（現在の動作）

pytest実行時に8件のwarningが発生する（2026-04-06確認）。

### 証拠

**1. PytestConfigWarning: Unknown config option: env (1件)**
- `pytest.ini` L26-28 で `env` オプションを使用しているが、`pytest-env` プラグインが未インストール
- `pip list | grep pytest-env` → 該当なし

**2. UserWarning: Convert_system_message_to_human will be deprecated! (5件)**
- `langchain_google_genai/chat_models.py:357` から発生
- 発生テスト: test_xss.py (2件), test_ab_routes.py (1件), test_scenario_routes_extended.py (2件)
- 外部ライブラリ内部のwarning、プロジェクトコードでは制御不可

**3. UserWarning: Using default SECRET_KEY in development (2件)**
- `pydantic/main.py:253` 経由で config のバリデーション時に発生
- 発生テスト: test_config.py (2件)
- テスト環境ではデフォルトSECRET_KEYが意図的に使用される設計

## Expected Behavior（期待する動作）

- pytest実行時にwarningが0件（0 warnings）
- 対応方針:
  1. `pytest.ini` から `env` セクションを削除し、`conftest.py` で `os.environ` 設定に移行
  2. langchain_google_genaiのwarningを `filterwarnings` で抑制
  3. SECRET_KEY開発環境warningを `filterwarnings` で抑制

## Unchanged Behavior（変更しない動作）

- テスト環境変数 `TESTING=1`, `FLASK_ENV=testing` は引き続き設定される
- `filterwarnings` の既存設定（DeprecationWarning, PendingDeprecationWarning の ignore）は維持
- テストの検証ロジック・テスト数に影響を与えない
- 実装コードは一切変更しない
