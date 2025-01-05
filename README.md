# 職場コミュニケーション練習アプリ

職場でのコミュニケーションスキルを安全に練習できるWebアプリケーションです。ローカルLLM（Ollama）とOpenAIのモデルを使用して、実際の職場で起こりうるシナリオをシミュレーションできます。

## 主な機能

- 🎭 シナリオベースのロールプレイ練習
  - 上司との急な依頼への対応
  - 同僚との作業分担の調整
  - その他職場での一般的なシチュエーション
- 💭 自由会話練習モード
- 📝 詳細なフィードバック機能
- 🔄 複数のAIモデル対応
  - OpenAI GPTシリーズ
  - ローカルLLM（Ollama経由）
- 📊 学習履歴の記録と振り返り

## 必要条件

- Python 3.8以上
- Ollama（ローカルLLM実行用）
- OpenAI APIキー（OpenAIモデル使用時）

## インストール方法

1. リポジトリのクローン
```bash
git clone https://github.com/yourusername/roleplay-chatbot-webapp.git
cd roleplay-chatbot-webapp
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
# Windowsの場合
.\venv\Scripts\activate
# macOS/Linuxの場合
source venv/bin/activate
```

3. 必要なパッケージのインストール
```bash
pip install -r requirements.txt
```

注意: Google Gemini APIを使用する場合は、以下のパッケージが正しくインストールされていることを確認してください：
- google-generativeai
- langchain-google-genai

4. 環境変数の設定
- `.env`ファイルを作成し、必要なAPIキーを設定します。
```
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key  # Gemini API用
```

## 機能の使い方

### シナリオ練習
1. トップページから「シナリオを選ぶ」をクリック
2. 練習したいシナリオを選択
3. AIとロールプレイを実施
4. 会話終了後にフィードバックを取得

### 自由会話練習
1. トップページから「会話を始める」をクリック
2. 使用するAIモデルを選択
3. 自由にAIと会話練習

### 学習履歴
- 「学習履歴を見る」から過去の練習内容を確認可能
- フィードバック内容の振り返りが可能

## 開発者向け情報

開発用パッケージのインストール：
```bash
pip install -r requirements-dev.txt
```

## 使用している主な技術

- Flask: Webアプリケーションフレームワーク
- LangChain: LLMとの対話管理
- OpenAI API: GPTモデルの利用
- Google Gemini API: Geminiモデルの利用
- Ollama: ローカルLLMの実行

## ライセンス

本プロジェクトはMITライセンスの下で公開されています。

## 注意事項

- このアプリケーションは学習・練習用です
- 実際の職場での判断は、状況に応じて適切に行ってください
- APIキーは適切に管理し、公開しないようご注意ください

## Google Gemini APIの設定

1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. APIキーを生成
3. `.env`ファイルに`GOOGLE_API_KEY=your_key_here`として設定

注意: Gemini APIキーは「AI」で始まる必要があります。

