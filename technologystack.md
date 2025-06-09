# 技術スタック

## コア技術
- Python: ^3.8.0
- Flask: ^2.0.0
- **AIモデル: Google Gemini専用**

## フロントエンド
- HTML/CSS/JavaScript (静的ファイル)
- Jinja2 (Flaskテンプレートエンジン)

## バックエンド
- Flask: ^2.0.0
- Flask-Session: 最新版
- LangChain: ^0.1.0
- LangChain-Core: ^0.1.0
- YAML: 最新版（シナリオデータ管理用）

## AIインテグレーション
- Google Generative AI: ^0.3.0 (Gemini-1.5-pro, Gemini-1.5-flash)
- Google GenAI: ^0.1.0 (Gemini TTS API - gemini-2.5-flash-preview-tts)
- Web Speech API: ブラウザ内蔵（音声合成用フォールバック）

## 開発ツール
- python-dotenv: 環境変数管理
- virtualenv: 仮想環境管理

---

# API バージョン管理
## 重要な制約事項
- Google Generative AIは最新バージョン（0.3.0以上）を使用
- Gemini APIのテキスト生成機能を活用
- テキスト読み上げ機能はGemini TTS API (gemini-2.5-flash-preview-tts)を使用
- フォールバックとしてブラウザのWeb Speech APIをサポート

## 実装規則
- 環境変数は.envファイルで管理（GOOGLE_API_KEYのみ必要）
- シナリオデータはYAMLファイルで管理（scenarios/dataディレクトリ）
- セッション管理はFlask-Sessionを使用（ファイルシステム方式）
