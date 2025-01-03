# 職場コミュニケーション練習アプリ

職場でのコミュニケーションスキルを安全に練習できるWebアプリケーションです。ローカルLLM（Ollama）とOpenAIのモデルを使用して、実際の職場で起こりうるシナリオをシミュレーションできます。

## 主な機能

- 🎭 シナリオベースのロールプレイ
- 💭 自由会話練習
- 📝 会話フィードバック
- 🔄 ローカル/クラウドLLMの切り替え
- 📊 学習ポイントの可視化

## 必要条件

- Python 3.8以上
- Ollama（ローカルLLM用）
- OpenAI API Key（OpenAIモデル用）

## セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/yourusername/workplace-communication-practice.git
cd workplace-communication-practice
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
`.env`ファイルを作成し、以下を設定：
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

3. ブラウザでアクセス
```
http://localhost:5000
```

## 開発者向け

開発用パッケージのインストール：
```bash
pip install -r requirements-dev.txt
```

## ライセンス

MITライセンス

