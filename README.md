# 職場コミュニケーション練習アプリ

このアプリケーションは、職場でのコミュニケーションスキルを安全に練習できる環境を提供します。AIとの対話を通じて、実際の職場で役立つコミュニケーション能力の向上を支援します。

## 🌟 主な機能

### 1. シナリオロールプレイ
- 実際の職場で起こりうる場面を再現
- AIと対話形式で練習
- 会話終了後にフィードバックを取得
- 練習履歴の記録と振り返り

### 2. 雑談練習モード
- ビジネスシーンでの自然な雑談を練習
- 相手や状況に応じた適切な会話
- 会話スキルに関する具体的なフィードバック
- 実践的なアドバイスの提供

### 3. LLM観戦モード
- 2つのAIモデルの会話をリアルタイムで観察
- 会話の進行をステップバイステップで確認
- 自然な会話の流れを学習
- 職場での適切なコミュニケーションを観察

## 🔧 技術スタック

- **バックエンド**: Python, Flask
- **フロントエンド**: HTML, CSS, JavaScript
- **AI/LLM**:
  - OpenAI GPT (GPT-3.5-turbo, GPT-4, GPT-4o-mini)
  - Google Gemini Pro
  - Ollama（ローカルLLM）

## 📦 必要要件

- Python 3.8以上
- OpenAI API Key（オプション）
- Google API Key（オプション）
- Ollama（ローカルLLMを使用する場合）

## 🚀 セットアップ

1. リポジトリのクローン
```bash
git clone [repository-url]
cd roleplay-chatbot-webapp
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # Unix系
venv\Scripts\activate     # Windows
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

5. アプリケーションの起動
```bash
python roleplay-chatbot-wepapp-main.py
```

## 💻 使い方

1. トップページでAIモデルを選択
   - OpenAI GPT
   - Google Gemini
   - ローカルLLM（Ollama）

2. 練習モードの選択
   - シナリオロールプレイ
   - 雑談練習
   - LLM観戦モード

3. 各モードでの練習
   - シナリオ：場面を選んでロールプレイ
   - 雑談：相手と状況を設定して自由に会話
   - 観戦：AIの会話を観察して学習

4. フィードバックの確認
   - 会話の分析
   - 具体的な改善点
   - 次回への実践アドバイス

## 🛠 開発者向け情報

### ディレクトリ構成
```
/
├── static/                       # 静的ファイル
│   ├── css/                      # CSSファイル
│   └── js/                       # JavaScriptファイル
├── templates/                    # Flaskテンプレート
├── scenarios/                    # シナリオ関連
│   ├── __init__.py               # シナリオロード処理
│   └── data/                     # シナリオデータ
├── roleplay-chatbot-wepapp-main.py # メインアプリケーション
```

### シナリオの追加方法
1. `scenarios/data/` ディレクトリに新しいYAMLファイルを作成
2. 既存のシナリオファイルを参考に、必要な情報を記述
3. アプリケーション再起動時に自動的にロードされます

### 開発用依存パッケージのインストール
```bash
pip install -r requirements-dev.txt
```

### ローカルLLM (Ollama) のセットアップ
1. [Ollama](https://ollama.ai/)をインストール
2. 以下のコマンドで必要なモデルをダウンロード:
```bash
ollama pull llama2
```
3. Ollamaサーバーを起動:
```bash
ollama serve
```

### デバッグモードでの実行
```bash
python roleplay-chatbot-wepapp-main.py
```
デフォルトでデバッグモードが有効になっており、コード変更時に自動で再起動します。

## 🔒 プライバシーとセキュリティ

- OpenAI/Google APIを使用する場合は、会話データが各サービスに送信されます
- ローカルLLM（Ollama）を使用する場合は、すべてのデータがローカルで処理されます
- セッションデータは一時的にサーバーに保存され、セッション終了時に削除されます

## 🤝 コントリビューション

バグ報告や機能改善の提案は、Issueやプルリクエストでお願いします。

## 📄 ライセンス

[MITライセンス](LICENSE)

## 👥 作者

[Your Name]

## 📝 注意事項

- このアプリケーションは学習・練習用です
- AIの応答は参考程度にお考えください
- 実際の職場での行動指針は、所属組織の方針に従ってください

