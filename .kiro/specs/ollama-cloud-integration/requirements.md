# Ollama Cloud Integration — Requirements

## 背景
現状の `DEFAULT_MODEL=gemini-2.5-flash-lite` は AA Intelligence Index で平均以下の性能評価を受けており、シナリオロールプレイ/フィードバック生成用途では品質不足が懸念される。Ollama Cloud の `gemma4:31b-cloud`（MMLU 85.2%, GPQA 84.3%, 140言語対応, $20定額）は品質・予算可読性の両面で有力な選択肢。

## スコープ（段階的導入）

### Phase A（本Spec範囲）
- **ミニマム統合**: Ollama Cloud を LLMService の追加プロバイダとして組み込む
- `DEFAULT_MODEL=ollama/gemma4:31b-cloud` のように env で切替可能にする
- 既存 Gemini 利用は一切変更しない
- UI 変更なし

### Phase B（本Spec範囲外・後続PR）
- モード別モデル指定（SCENARIO_MODEL / CHAT_MODEL / FEEDBACK_MODEL）

### Phase C（さらに後続）
- UI でのモデル選択拡張

## Functional Requirements

1. **FR1**: `DEFAULT_MODEL=ollama/<model_name>` で Ollama Cloud モデルを指定可能
2. **FR2**: `OLLAMA_API_KEY` 環境変数で Ollama Cloud 認証
3. **FR3**: `OLLAMA_BASE_URL` でエンドポイント上書き可能（デフォルト: `https://ollama.com/v1`）
4. **FR4**: ストリーミング応答（SSE）が従来どおり動作
5. **FR5**: 既存の Gemini 分岐は完全に保持（`gemini/` or `gemini-` プレフィックス）
6. **FR6**: `gemma4:31b-cloud` を少なくとも許可モデルリストに含める

## Non-Functional Requirements

1. **NFR1**: `OLLAMA_API_KEY` 未設定時は Ollama 系モデルの初期化で明確なエラーを返す
2. **NFR2**: 既存テスト（1464 passed）を破壊しない
3. **NFR3**: what/why/how 形式のエラーメッセージを保持

## Out of Scope

- モード別モデル指定（Phase B）
- UI でのモデル選択拡張（Phase C）
- Ollama local（`localhost:11434`）サポート — 必要になれば Phase C で検討
- Anthropic / OpenAI 等、他プロバイダ全般の統合
