# Ollama Chat Web App

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.0-green)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Ollamaを使用したシンプルなWebチャットアプリケーション。ローカルで動作するLLMモデルとチャットができます。

<img width="800" alt="app_screenshot" src="docs/images/screenshot.png">

## ✨ 機能

- 🤖 複数のOllamaモデルに対応（llama2, codellama, mistral など）
- 🌐 シンプルで使いやすいWebインターフェース
- 💬 スムーズなチャット体験
- 📝 会話履歴の保持
- 🔄 モデルの動的切り替え

## 🔧 必要条件

- Python 3.8以上
- [Ollama](https://ollama.ai/)（ローカルにインストール済みであること）
- 推奨: 8GB以上のRAM

## 🚀 セットアップ

1. リポジトリをクローン
```bash
git clone https://github.com/CaCC-Lab/ollama-chatbot-webapp.git
cd ollama-chatbot-webapp
```

2. 必要なパッケージをインストール
```bash
pip install -r requirements.txt
```

3. Ollamaが起動していることを確認
```bash
ollama serve
```

4. アプリケーションを起動
```bash
python chat-app-main.py
```

5. ブラウザで以下のURLにアクセス
```
http://localhost:5000
```

## 💡 使用方法

1. プルダウンメニューから使用したいモデルを選択
   - 事前にOllamaでモデルをダウンロードしておく必要があります
   - 例: `ollama pull llama2`
2. チャットボックスにメッセージを入力
3. 送信ボタンをクリックまたはEnterキーを押して送信

## 📦 依存パッケージ

```text
flask==3.1.0
langchain==0.1.0
langchain-community==0.0.10
requests==2.31.0
```

## 📁 プロジェクト構造

```
ollama-chatbot-webapp/
├── README.md
├── requirements.txt
├── .gitignore
├── chat-app-main.py
└── templates/
    └── index.html
```

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

MITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) をご覧ください。

## 📧 連絡先

あなたのGitHubプロフィール: [@CaCC-Lab](https://github.com/CaCC-Lab)

プロジェクトリンク: [https://github.com/CaCC-Lab/ollama-chatbot-webapp](https://github.com/CaCC-Lab/ollama-chatbot-webapp)
