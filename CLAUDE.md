# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

AIを活用したロールプレイシナリオを通じて職場でのコミュニケーションスキルを練習するFlaskベースのWebアプリケーション。

## 主要機能

1. **シナリオロールプレイ**: 30種類以上の職場シナリオでAIと対話練習
2. **雑談練習モード**: 職場での適切な雑談スキルを向上
3. **会話観戦モード**: 2つのAIモデル間の会話を観察して学習
4. **学習履歴**: 進捗状況の追跡と過去の会話の振り返り

## 開発コマンド

```bash
# 仮想環境のセットアップと有効化
python -m venv venv
source venv/bin/activate  # Unix/macOS
venv\Scripts\activate     # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 開発ツール用

# アプリケーションの起動
python roleplay-chatbot-wepapp-main.py

# 開発ツール（requirements-dev.txtをインストール後）
black .                   # コードフォーマット
flake8                   # リンター実行
isort .                  # インポート順整理
mypy .                   # 型チェック
pytest                   # テスト実行（テストが作成されている場合）
```

## アーキテクチャ概要

### LLMプロバイダー統合
- **Google Gemini専用**: Gemini-1.5-proとGemini-1.5-flashをサポート
- **動的モデル選択**: `/api/models`エンドポイントで利用可能なGeminiモデルを取得
- **音声読み上げ**: Web Speech APIを使用したブラウザ内蔵の音声合成機能

### セッション管理
- **Flask-Session**: ユーザーごとの会話履歴とモデル選択を保持
- **柔軟な保存方式**: 
  - ファイルシステム（デフォルト）
  - Redis（スケーラブル環境向け、環境変数で設定可能）

### メモリ管理戦略
- **会話履歴**: 各モード（雑談、シナリオ、観戦）ごとに独立したメモリを保持
- **ストリーミング応答**: Server-Sent Events (SSE)を使用してリアルタイムでAI応答を配信

### シナリオシステム
- **YAML形式**: `scenarios/data/`ディレクトリにシナリオをYAMLファイルで管理
- **動的読み込み**: `scenarios/__init__.py`の`load_scenarios()`関数で起動時に全シナリオを読み込み
- **構造化データ**: 各シナリオには難易度、タグ、学習ポイント、フィードバックポイントを含む

## API設計

### 主要エンドポイント
- `GET /api/models`: 利用可能なAIモデルリストを返す
- `POST /api/chat`: 雑談モードでメッセージ送信（SSEストリーミング）
- `POST /api/scenario_chat`: シナリオモードでメッセージ送信（SSEストリーミング）
- `POST /api/watch/start`: 観戦モード開始
- `POST /api/watch/next`: 観戦モードで次の会話を生成
- `POST /api/scenario_feedback`: シナリオ練習のフィードバック取得
- `POST /api/chat_feedback`: 雑談練習のフィードバック取得

### ストリーミング実装
Server-Sent Events (SSE)を使用してAIの応答をリアルタイムで配信:
```python
def generate():
    for chunk in stream:
        yield f"data: {json.dumps({'content': chunk})}\n\n"
```

## 重要な実装詳細

### LLMプロバイダーの初期化
`roleplay-chatbot-wepapp-main.py`の`initialize_llm()`関数でGeminiモデルを初期化:
- Gemini: `ChatGoogleGenerativeAI`クラスを使用
- `create_gemini_llm()`関数で従来のモデルからの移行をサポート

### エラーハンドリング
- 各APIエンドポイントでtry-exceptブロックを使用
- Gemini API固有のエラーを適切に処理
- ユーザーフレンドリーなエラーメッセージを返す

### 環境変数
必須の環境変数（`.env`ファイルで管理）:
- `FLASK_SECRET_KEY`: セッション暗号化用
- `GOOGLE_API_KEY`: Google Gemini APIキー（必須）
- `SESSION_TYPE`: セッション保存方式（filesystem/redis）

## 開発時の注意点

1. **シナリオ追加時**: `scenarios/data/`に新しいYAMLファイルを作成し、既存の形式に従う
2. **音声読み上げ機能**: Web Speech APIを使用し、ブラウザ内で処理
3. **フロントエンド変更時**: `static/js/`内の対応するJavaScriptファイルを更新
4. **セッション関連の変更時**: Flask-Sessionの設定を確認し、互換性を保つ

## デバッグ情報

- Gemini APIの状態: Google Cloud Consoleで確認
- セッションデータ: `flask_session/`ディレクトリ（filesystemモード時）
- ログ出力: コンソールに直接出力（本番環境では適切なロギング設定を推奨）