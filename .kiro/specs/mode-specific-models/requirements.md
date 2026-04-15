# Mode-Specific Models — Requirements (Phase B)

## 背景
Phase A で Ollama Cloud プロバイダを統合し、`DEFAULT_MODEL` 単一設定で全モード共通のモデルを利用できる状態になった。

しかし実用上は用途ごとに最適モデルが異なる:

| モード | 要求特性 | 推奨 |
|---|---|---|
| 雑談 | 軽快・低レイテンシ | Gemini Flash（無料枠で十分） |
| シナリオ | ロールプレイの一貫性・ニュアンス | Gemma 4 31B Cloud |
| 観戦 | 2つの異なる性格を演じ分け | 系統の異なる2モデル |
| フィードバック | 深い洞察・分析力 | Gemma 4 31B Cloud |

Phase B では **モード別にモデルを指定できる仕組み**を導入する。

## Functional Requirements

- **FR1**: 以下の環境変数でモード別モデルを指定可能
  - `SCENARIO_MODEL` — シナリオロールプレイ
  - `CHAT_MODEL` — 雑談
  - `WATCH_MODEL` — 観戦モード
  - `FEEDBACK_MODEL` — フィードバック生成

- **FR2**: モード別設定が未設定の場合、`DEFAULT_MODEL` にフォールバック

- **FR3**: ユーザーがUIで選択したモデル（`selected_model`）がある場合、それを最優先

- **FR4**: 優先順位は以下のとおり
  ```
  session.selected_model  >  <MODE>_MODEL env  >  DEFAULT_MODEL
  ```

- **FR5**: `feedback_service.try_multiple_models_for_prompt` は Ollama モデルを受理できる
  - 現状の Gemini 専用フィルタを「非 Gemini なら直接利用」で緩和

- **FR6**: モード別モデルも `config.validate_model` による検証を通過する

## Non-Functional Requirements

- **NFR1**: 既存テスト (1473 passed) を破壊しない
- **NFR2**: `DEFAULT_MODEL` のみ設定の現行運用は挙動変更なし（後方互換）
- **NFR3**: what/why/how エラー形式を踏襲
- **NFR4**: `.env.example` / README にセットアップ例を記載

## Out of Scope
- UI でのモード別モデル選択（Phase C 予定）
- モード以外の粒度（シナリオ個別・難易度別など）での振り分け
