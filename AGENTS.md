# Agents ドキュメント一覧

本ドキュメントでは、本リポジトリで提供されている主要な「Agent（AI駆動コンポーネント）」と、それを補足するAIエージェント向けガイドドキュメントをまとめています。

## 1. AIアシスタント向けガイドドキュメント
以下のドキュメントは、各種AIコードアシスタント（agent）が本プロジェクトを理解し、開発支援を行うための概要と手順を提供します。

| ドキュメント           | 対象AIアシスタント     | 説明                                                        |
|------------------------|------------------------|-------------------------------------------------------------|
| [GEMINI.md](GEMINI.md)     | Google Gemini Agent    | プロジェクト概要、主要機能、技術スタック、アーキテクチャなどをまとめた概要ドキュメント |
| [CLAUDE.md](CLAUDE.md)     | Claude Code Agent      | Claude Code (claude.ai/code) 向けの開発コマンド、API設計、アーキテクチャガイド    |

※ ChatGPT や Copilot 向けのガイドは未実装です。

## 2. エージェント機能一覧 (AI駆動コンポーネント)
本アプリケーション内では、以下の各エージェント機能がAPIエンドポイントや専用モジュールとして実装されています。

| Agent 名称             | 主な実装モジュール/ファイル              | 機能概要                                        | API/ルート                                                      |
|------------------------|------------------------------------------|-------------------------------------------------|------------------------------------------------------------------|
| Chat Agent             | `static/js/chat.js`<br>`app.py`           | 自由会話モード                                    | `GET /chat`, `POST /api/chat` (SSE)                             |
| Scenario Agent         | `scenarios/`<br>`static/js/scenario.js`  | YAMLシナリオに基づくロールプレイ会話                  | `GET /scenarios`, `GET /scenario`, `POST /api/scenario_chat` (SSE) |
| Watch Agent            | `static/js/watch.js`<br>`app.py`          | AI同士の会話観戦モード                            | `GET /watch`, `POST /api/watch/start`, `POST /api/watch/next` (SSE) |
| Feedback Agent         | `strength_analyzer.py`<br>`app.py`        | 会話練習後のフィードバック生成と可視化              | `POST /api/chat_feedback`, `POST /api/scenario_feedback`        |
| TTS Agent              | `static/js/tts-common.js`<br>`app.py`     | 音声合成 (Gemini TTS API, Web Speech API フォールバック) | `POST /api/tts`                                                  |
| API Key Manager Agent  | `api_key_manager.py`                    | Google APIキーの自動ローテーション管理              | `GET /api/key_status`                                           |
| LLM Initialization Agent | `app.py`                                | LLMモデル(Gemini/OpenAI/Local)の初期化・管理         | 関数: `create_gemini_llm()`, `initialize_llm()`                 |
| Configuration Agent    | `config/config.py`                      | 環境設定の読み込み・検証 (Pydantic Settings)        | 関数: `get_config()`, `get_cached_config()`                     |

## 3. その他の参照ドキュメント
- [API_KEY_SETUP.md](API_KEY_SETUP.md): Google APIキーの設定方法ガイド
- [TTS_API_GUIDE.md](TTS_API_GUIDE.md): Gemini TTS API 音声オプションと使用方法
- [azure-webapp-settings.md](azure-webapp-settings.md): Azure Web App デプロイ時の環境変数設定ガイド
- [TODO.md](TODO.md): 今後の実装タスク一覧
- [technologystack.md](technologystack.md): プロジェクトの技術スタック一覧
- [directorystructure.md](directorystructure.md): ディレクトリ構成ガイド