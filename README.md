# ロールプレイチャットボット

FlaskベースのWebアプリケーションで、ローカルLLM（Ollama）とOpenAIのモデルを切り替えて使用できるチャットボットです。

## 機能

- ローカルLLM（Ollama）とOpenAIのモデルを切り替え可能
- 会話履歴の保持と管理
- 会話履歴のクリア機能
- モデル一覧の動的取得
- シンプルなWebインターフェース

## 必要条件

- Python 3.8以上
- Ollama（ローカルLLM用）
- OpenAI API Key（OpenAIモデル用）

## セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/your-username/roleplay-chatbot-webapp.git
cd roleplay-chatbot-webapp
```

2. 仮想環境の作成と有効化
```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windowsの場合
.\venv\Scripts\activate
# Linux/Macの場合
source venv/bin/activate
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
`.env`ファイルをプロジェクトのルートディレクトリに作成し、以下の内容を追加：
```
OPENAI_API_KEY=your-api-key-here
```

## 実行方法

1. Ollamaサーバーの起動（別ターミナルで）
```bash
ollama serve
```

2. アプリケーションの起動
```bash
python roleplay-chatbot-wepapp-main.py
```

3. ブラウザで以下のURLにアクセス
```
http://localhost:5000
```

## 開発環境のセットアップ

開発用の追加パッケージをインストール：
```bash
pip install -r requirements-dev.txt
```

## 注意事項

- 本番環境での使用時は、適切なセキュリティ対策を実施してください
- OpenAIのAPIキーは安全に管理してください
- 会話履歴はセッションに保存されます
- デフォルトではローカルホストでの実行のみ想定しています

## ライセンス

[MITライセンス](LICENSE)

