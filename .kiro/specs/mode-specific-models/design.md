# Mode-Specific Models — Design (Phase B)

## アーキテクチャ

### 新規モジュール: `services/model_selector.py`

単一の関数 `resolve_model(mode, session_selected=None)` に優先順位ロジックを集約する。

```python
# services/model_selector.py
import os
from typing import Literal, Optional
from config import get_config

Mode = Literal["scenario", "chat", "watch", "feedback"]

_MODE_ENV_MAP = {
    "scenario": "SCENARIO_MODEL",
    "chat":     "CHAT_MODEL",
    "watch":    "WATCH_MODEL",
    "feedback": "FEEDBACK_MODEL",
}

def resolve_model(mode: Mode, session_selected: Optional[str] = None) -> str:
    """モード別モデル解決:
      1. session_selected（UI選択）があればそれを優先
      2. <MODE>_MODEL env があればそれを使用
      3. DEFAULT_MODEL にフォールバック
    """
    if session_selected:
        return session_selected
    env_key = _MODE_ENV_MAP[mode]
    env_value = (os.environ.get(env_key) or "").strip()
    if env_value:
        return env_value
    return get_config().DEFAULT_MODEL
```

### 設定クラス拡張 `config/config.py`

```python
# API設定（モード別）
SCENARIO_MODEL: Optional[str] = Field(default=None, alias="SCENARIO_MODEL")
CHAT_MODEL:     Optional[str] = Field(default=None, alias="CHAT_MODEL")
WATCH_MODEL:    Optional[str] = Field(default=None, alias="WATCH_MODEL")
FEEDBACK_MODEL: Optional[str] = Field(default=None, alias="FEEDBACK_MODEL")
```

`validate_model` と同じバリデータを上記4フィールドにも適用（`None` は許可）。

### ルートへの適用

**最小差分で実装**: 各ルートで `DEFAULT_MODEL` を参照している箇所を `resolve_model(mode, session_selected)` に置換する。

#### `routes/chat_routes.py` (chat モード)
```python
# before:
model_name = data.get("model", DEFAULT_MODEL)
# after:
model_name = resolve_model("chat", data.get("model"))
```

#### `routes/scenario_routes.py` (scenario / feedback モード)
```python
# 会話:
selected_model = resolve_model("scenario", data.get("model"))
# フィードバック:
selected_model = resolve_model("feedback", data.get("model"))
```

#### `routes/watch_routes.py` (watch モード)
```python
model_a = resolve_model("watch", data.get("model_a"))
```

### feedback_service の Gemini 前提を緩和

`services/feedback_service.py:148-163` が Gemini モデルリストのみで検証している。Phase B では **非 Gemini モデルはリスト検証をスキップして直接利用** する。

```python
if preferred_model:
    if preferred_model.startswith("ollama/"):
        # Ollama Cloud はリスト検証不要、直接利用
        model_name = preferred_model
    elif not preferred_model.startswith("gemini/"):
        normalized_model = f"gemini/{preferred_model}"
        ...
    else:
        # 既存の Gemini ロジック
        ...
```

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `services/model_selector.py` | **新規** - `resolve_model()` ヘルパー |
| `config/config.py` | `SCENARIO_MODEL` 等 4 フィールド追加 + バリデータ拡張 |
| `routes/chat_routes.py` | `resolve_model("chat", ...)` 使用 |
| `routes/scenario_routes.py` | `resolve_model("scenario"/"feedback", ...)` 使用 |
| `routes/watch_routes.py` | `resolve_model("watch", ...)` 使用 |
| `services/feedback_service.py` | Ollama モデル直接利用分岐 |
| `.env.example` | モード別モデル設定例を追加 |
| `README.md` | ハイブリッド構成例を追加 |
| `tests/test_services/test_model_selector.py` | **新規** - 優先順位テスト |
| `tests/test_services/test_feedback_service_*.py` | Ollama 経路テスト追加 |

## エラーハンドリング

`resolve_model` が返すモデル名は **既存の `initialize_llm` / `validate_model` で検証される**。未サポートモデルを env に設定した場合は config 読み込み時に `ValueError` が発生し、アプリ起動時点で検知できる。

## ロールバック

モード別 env を全て削除（または未設定のまま）すれば、`DEFAULT_MODEL` 単一運用に戻る。コード変更は env 優先チェックが 1 段増えるだけで、既存挙動を保つ。

## テスト戦略

1. **単体**: `resolve_model()` の優先順位
   - session_selected 指定あり → それが返る
   - env のみ → env が返る
   - 何も無し → DEFAULT_MODEL
2. **単体**: `config.Config` が4環境変数を受理・バリデート
3. **単体**: `feedback_service` の Ollama 直接利用分岐
4. **統合**: ルート4種で `resolve_model` が呼ばれること (mock)
5. **回帰**: 既存 1473 + Phase A 10 が全 PASS
