# 技術スタック

## コア技術
- Python: ^3.8.0
- Flask: ^2.0.0
- **AIモデル: 複数（OpenAI、Google Gemini、Ollama）**

## フロントエンド
- HTML/CSS/JavaScript (静的ファイル)
- Jinja2 (Flaskテンプレートエンジン)

## バックエンド
- Flask: ^2.0.0
- Flask-Session: 最新版
- LangChain: ^0.1.0
- LangChain-Core: ^0.1.0
- LangChain-Community: ^0.0.10
- YAML: 最新版（シナリオデータ管理用）

## AIインテグレーション
- OpenAI API: ^1.0.0 (GPT-3.5-turbo, GPT-4, GPT-4o-mini)
- Google Generative AI: ^0.3.0 (Gemini Pro)
- Ollama: 最新版（ローカルLLMサポート）

## 開発ツール
- python-dotenv: 環境変数管理
- virtualenv: 仮想環境管理

---

# API バージョン管理
## 重要な制約事項
- OpenAIクライアントは最新バージョン（1.0.0以上）を使用
- Google Generative AIは最新バージョン（0.3.0以上）を使用
- LLMプロバイダーの構成は変更する場合は互換性の検証が必要

## 実装規則
- 環境変数は.envファイルで管理
- シナリオデータはYAMLファイルで管理（scenarios/dataディレクトリ）
- セッション管理はFlask-Sessionを使用（ファイルシステム方式）
