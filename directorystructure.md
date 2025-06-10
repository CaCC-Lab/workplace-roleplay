# ディレクトリ構成

以下のディレクトリ構造に従って実装を行ってください：

```
/
├── static/                       # 静的ファイル
│   ├── css/                      # CSSファイル
│   └── js/                       # JavaScriptファイル
├── templates/                    # Flaskテンプレート
│   ├── index.html                # トップページ
│   ├── chat.html                 # 自由会話ページ
│   ├── scenarios_list.html       # シナリオ一覧ページ
│   ├── scenario.html             # シナリオ詳細ページ
│   ├── journal.html              # 会話記録ページ
│   └── watch.html                # 会話閲覧ページ
├── scenarios/                    # シナリオ関連
│   ├── __init__.py               # シナリオロード処理
│   └── data/                     # シナリオデータ
├── flask_session/                # Flaskセッションデータ
├── app.py                        # メインアプリケーション
├── requirements.txt              # 依存パッケージ
├── requirements-dev.txt          # 開発用依存パッケージ
├── .env                          # 環境変数設定
├── README.md                     # プロジェクト説明
├── technologystack.md            # 技術スタック定義
├── directorystructure.md         # ディレクトリ構造定義
├── .gitignore                    # Git除外設定
└── .git/                         # Gitリポジトリ
```

### 配置ルール
- テンプレートファイル → `templates/`
- 静的アセット(JS, CSS) → `static/`
- シナリオデータ → `scenarios/data/`
- メイン処理 → `app.py`

### 機能概要
- ローカルLLM (Ollama) とクラウドLLM (OpenAI, Gemini) の切り替え
- ユーザーごとの会話メモリ管理
- シナリオベースのロールプレイ機能
- リアルタイムストリーミングレスポンス
- 会話履歴の保存と表示
