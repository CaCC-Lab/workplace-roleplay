# Ollama Cloud Integration — Design (Phase A)

## アーキテクチャ概要

Ollama Cloud は **OpenAI 互換 API** を提供する。`langchain-openai` の `ChatOpenAI` を `base_url=https://ollama.com/v1` で初期化すれば LangChain ライフサイクルに透過的に乗せられる。

```
LLMService.initialize_llm(model_name)
├─ startswith("ollama/") → create_ollama_llm()  [NEW]
│   └─ ChatOpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY, streaming=True)
└─ それ以外                  → create_gemini_llm() [既存]
    └─ ChatGoogleGenerativeAI(...)
```

## 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `requirements.txt` | `langchain-openai>=0.1.0,<1.0.0` 追加 |
| `config/config.py` | `OLLAMA_API_KEY`, `OLLAMA_BASE_URL` フィールド追加 / `validate_model` に `ollama/*` パターン追加 |
| `services/llm_service.py` | `create_ollama_llm()` 新設 / `initialize_llm()` 分岐 |
| `.env.example` | Ollama 設定セクション追加 |
| `README.md` | Ollama Cloud セットアップ手順追加 |

## 実装詳細

### `services/llm_service.py`

```python
from langchain_openai import ChatOpenAI  # NEW

class LLMService:
    OLLAMA_DEFAULT_BASE_URL = "https://ollama.com/v1"

    def create_ollama_llm(self, model_name: str):
        api_key = os.environ.get("OLLAMA_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "OLLAMA_API_KEY is not set. "
                "Get one at https://ollama.com/settings/keys and add to .env"
            )
        base_url = os.environ.get("OLLAMA_BASE_URL", self.OLLAMA_DEFAULT_BASE_URL).strip()
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=self.default_temperature,
            streaming=True,
        )

    def initialize_llm(self, model_name: str):
        if model_name.startswith("ollama/"):
            ollama_model = model_name.replace("ollama/", "", 1)
            return self.create_ollama_llm(ollama_model)
        # 既存 Gemini 経路
        if model_name.startswith("gemini/"):
            model_name = model_name.replace("gemini/", "", 1)
        return self.create_gemini_llm(model_name)
```

### `config/config.py` の validate_model 拡張

`ollama/<name>:<tag>` パターンを許可（例: `ollama/gemma4:31b-cloud`, `ollama/qwen2.5:72b-cloud`）。

```python
ollama_pattern = re.compile(r"^ollama/[a-z0-9_.\-]+(:[a-z0-9_.\-]+)?$")
if ollama_pattern.match(v):
    return v
```

`OLLAMA_API_KEY`, `OLLAMA_BASE_URL` は Optional フィールドとして追加（未設定でも Gemini 単独運用は継続可能）。

## エラーハンドリング

`what/why/how` 形式を踏襲：

- **what**: `OLLAMA_API_KEY is not set`
- **why**: Ollama Cloud モデル (`ollama/*`) の初期化には API キーが必須
- **how**: https://ollama.com/settings/keys で発行し `.env` の `OLLAMA_API_KEY=` に設定

## ストリーミング互換性

`ChatOpenAI(streaming=True).astream()` は LangChain の `BaseChatModel` インターフェースで `ChatGoogleGenerativeAI` と同じ。`stream_chat_response()` 側は無変更で動作する。

## テスト戦略

1. **単体**: `create_ollama_llm()` のキー未設定時エラー、正常初期化、モデル名正規化
2. **単体**: `initialize_llm()` の分岐（ollama/ prefix → ChatOpenAI 経路）
3. **単体**: `validate_model` の `ollama/*` パターン許可
4. **回帰**: 既存 Gemini 経路のテストが通ること
5. **動作確認**: 実際に `OLLAMA_API_KEY` を設定してローカルで chat エンドポイント疎通

## ロールバック

`.env` の `DEFAULT_MODEL` を Gemini に戻すだけで完全ロールバック可能。コード変更は Gemini 経路を一切触らないため副作用なし。
