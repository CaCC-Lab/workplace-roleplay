# 🗣️ 職場コミュニケーション練習アプリ

[![CI - Tests and Quality Checks](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/ci.yml/badge.svg)](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/ci.yml)
[![Deploy to Azure VM Production](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/deploy-production.yml/badge.svg)](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/deploy-production.yml)
[![Test Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)](https://github.com/CaCC-Lab/workplace-roleplay)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AIを活用したロールプレイシナリオを通じて、職場でのコミュニケーションスキルを安全に練習できるWebアプリケーションです。

## 📸 スクリーンショット

![アプリ画面](docs/screenshot.png)
*（スクリーンショットは後で追加）*

## ✨ 主要機能

### 🎭 シナリオロールプレイ
- **45種類以上の職場シナリオ**でAIと対話練習
- 難易度別（初級・中級・上級）のシナリオ構成
- リアルタイムのAIフィードバック
- 学習ポイントとフィードバックポイントの提示

### 💬 雑談練習モード
- 職場での適切な雑談スキルを向上
- 自然な会話の流れを学習
- AIによる会話のサポートとアドバイス

### 👀 会話観戦モード
- 2つのAIモデル間の会話を観察して学習
- 良いコミュニケーションの例を視覚的に理解
- 学習ポイントの自動解説

### 🏢 ハラスメント対策シナリオ
- 職場でのハラスメント防止・対応を学習
- 11種類の研修シナリオ
- デリケートな内容への配慮（同意画面あり）

### 📊 追加機能
- **学習履歴**: 進捗状況の追跡と過去の会話の振り返り
- **強み分析**: コミュニケーションスキルの可視化
- **ダークモード**: 目に優しい表示切り替え

## 🛠️ 技術スタック

### バックエンド
| 技術 | バージョン | 用途 |
|-----|----------|------|
| Python | 3.8+ | メイン言語 |
| Flask | 2.0+ | Webフレームワーク |
| Flask-Session | 最新 | セッション管理 |
| LangChain | 0.1+ | LLM統合 |

### フロントエンド
| 技術 | 用途 |
|-----|------|
| HTML/CSS/JavaScript | UI構築 |
| Jinja2 | テンプレートエンジン |
| Chart.js | グラフ表示 |
| Font Awesome | アイコン |

### AI/LLM
| 技術 | 用途 |
|-----|------|
| Google Gemini | メインAIモデル（gemini-2.5-flash等） |
| Gemini TTS API | 音声読み上げ（オプション） |
| Web Speech API | 音声合成フォールバック |

### インフラ
| 技術 | 用途 |
|-----|------|
| Azure VM | 本番環境ホスティング |
| Nginx | リバースプロキシ |
| Gunicorn | WSGIサーバー |
| GitHub Actions | CI/CD |

## 🚀 セットアップ

### 前提条件
- Python 3.8以上
- Google Cloud アカウント（Gemini API用）

### インストール手順

```bash
# 1. リポジトリをクローン
git clone https://github.com/CaCC-Lab/workplace-roleplay.git
cd workplace-roleplay

# 2. 仮想環境を作成・有効化
python -m venv venv
source venv/bin/activate  # Unix/macOS
# venv\Scripts\activate   # Windows

# 3. 依存パッケージをインストール
pip install -r requirements.txt

# 4. 環境変数を設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

### 環境変数の設定

`.env`ファイルに以下を設定:

```bash
# 必須
GOOGLE_API_KEY=your_google_api_key_here
FLASK_SECRET_KEY=your_secret_key_here

# オプション
SESSION_TYPE=filesystem
PORT=5000

# 機能フラグ（詳細は下記参照）
ENABLE_MODEL_SELECTION=false
ENABLE_TTS=false
ENABLE_LEARNING_HISTORY=false
ENABLE_STRENGTH_ANALYSIS=false

# デフォルトモデル
DEFAULT_MODEL=gemini/gemini-2.5-flash-lite
```

### 機能フラグの詳細

このアプリケーションは環境変数による機能フラグをサポートしており、特定の機能を有効/無効に切り替えることができます。

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `ENABLE_MODEL_SELECTION` | `false` | AIモデル選択UIの表示。`true`にするとユーザーがGeminiモデルを選択可能 |
| `ENABLE_TTS` | `false` | 音声読み上げ（Text-to-Speech）機能。`true`にするとAI応答の音声再生が可能 |
| `ENABLE_LEARNING_HISTORY` | `false` | 学習履歴機能。`true`にすると過去の会話履歴と進捗を表示 |
| `ENABLE_STRENGTH_ANALYSIS` | `false` | 強み分析機能。`true`にするとコミュニケーションスキルの分析結果を表示 |
| `DEFAULT_MODEL` | `gemini/gemini-2.5-flash-lite` | デフォルトで使用するAIモデル |

#### 機能フラグの使用例

```bash
# 全機能を有効化（開発・テスト用）
ENABLE_MODEL_SELECTION=true
ENABLE_TTS=true
ENABLE_LEARNING_HISTORY=true
ENABLE_STRENGTH_ANALYSIS=true

# 最小構成（本番推奨）
ENABLE_MODEL_SELECTION=false
ENABLE_TTS=false
ENABLE_LEARNING_HISTORY=false
ENABLE_STRENGTH_ANALYSIS=false
```

#### 機能フラグの動作

- **UIへの影響**: 機能フラグが`false`の場合、該当する機能のUI要素（ボタン、メニュー等）は非表示になります
- **APIへの影響**: 無効化された機能のAPIエンドポイントにアクセスすると、403エラーと「この機能は現在無効化されています」というメッセージが返されます
- **段階的リリース**: 新機能を段階的にリリースする際に活用できます

### アプリケーションの起動

```bash
# 開発サーバーを起動
python app.py

# ブラウザで http://localhost:5000 にアクセス
```

## 📁 ディレクトリ構成

```
workplace-roleplay/
├── app.py                    # メインアプリケーション
├── config/                   # 設定ファイル
│   ├── config.py            # アプリケーション設定
│   ├── feature_flags.py     # 機能フラグ管理
│   └── security_utils.py    # セキュリティユーティリティ
├── core/                     # コア機能
│   ├── error_handlers.py    # エラーハンドリング
│   ├── extensions.py        # Flask拡張
│   └── middleware.py        # ミドルウェア
├── routes/                   # APIルート
│   ├── chat_routes.py       # チャットAPI
│   ├── scenario_routes.py   # シナリオAPI
│   ├── watch_routes.py      # 観戦モードAPI
│   └── ...                  # その他のルート
├── services/                 # ビジネスロジック
│   ├── chat_service.py      # チャットサービス
│   ├── llm_service.py       # LLM統合
│   ├── scenario_service.py  # シナリオ管理
│   └── ...                  # その他のサービス
├── scenarios/                # シナリオデータ
│   ├── __init__.py          # シナリオローダー
│   ├── category_manager.py  # カテゴリ管理
│   └── data/                # YAMLシナリオファイル（45+件）
├── static/                   # 静的ファイル
│   ├── css/                 # スタイルシート
│   └── js/                  # JavaScript
├── templates/                # HTMLテンプレート
│   ├── index.html           # トップページ
│   ├── chat.html            # 雑談練習
│   ├── scenario.html        # シナリオ練習
│   ├── watch.html           # 会話観戦
│   └── ...                  # その他のテンプレート
├── tests/                    # テストコード
│   ├── test_routes/         # ルートテスト
│   ├── test_services/       # サービステスト
│   └── security/            # セキュリティテスト
├── utils/                    # ユーティリティ
│   ├── csp_middleware.py    # CSPミドルウェア
│   ├── security.py          # セキュリティ機能
│   └── ...                  # その他のユーティリティ
├── .github/workflows/        # GitHub Actions
│   ├── ci.yml               # CI設定
│   └── deploy-production.yml # デプロイ設定
├── requirements.txt          # 本番依存パッケージ
├── requirements-dev.txt      # 開発依存パッケージ
└── README.md                 # このファイル
```

## 🧪 開発

### 開発ツールのインストール

```bash
pip install -r requirements-dev.txt
```

### コード品質チェック

```bash
# コードフォーマット
black .

# リンター
flake8

# インポート順序
isort .

# 型チェック
mypy .
```

### テストの実行

```bash
# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=. --cov-report=html

# 特定のテストのみ
pytest tests/test_routes/ -v
```

### 現在のテストカバレッジ

| モジュール | カバレッジ |
|-----------|-----------|
| config/ | 93-100% |
| services/ | 95-100% |
| routes/ | 79-100% |
| utils/ | 92-100% |
| **総合** | **87%** |

## 🔐 セキュリティ

このアプリケーションは以下のセキュリティ対策を実装しています：

- ✅ **XSS対策**: 入力サニタイズと出力エスケープ
- ✅ **CSRF対策**: トークンベースの保護
- ✅ **CSP**: Content Security Policyヘッダー
- ✅ **セッション管理**: セキュアなCookie設定（SameSite, HttpOnly）
- ✅ **シークレット管理**: 本番環境での厳格な検証

## 🚢 デプロイ

### 自動デプロイ（推奨）

mainブランチへのプッシュで自動的にAzure VMにデプロイされます。

```bash
# mainにプッシュするとデプロイが開始
git push origin main
```

### 手動デプロイ

```bash
# SSHで本番サーバーに接続
ssh -i your_key.pem user@your_server

# アプリディレクトリへ移動
cd ~/workplace-roleplay

# 最新コードを取得
git pull origin main

# 依存パッケージを更新
source venv/bin/activate
pip install -r requirements.txt

# サービスを再起動
sudo systemctl restart workplace-roleplay
```

## 📝 API リファレンス

### チャット関連

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/chat` | POST | 雑談モードでメッセージ送信（SSE） |
| `/api/scenario_chat` | POST | シナリオモードでメッセージ送信（SSE） |
| `/api/chat_feedback` | POST | 雑談のフィードバック取得 |
| `/api/scenario_feedback` | POST | シナリオのフィードバック取得 |

### 観戦モード

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/watch/start` | POST | 観戦モード開始 |
| `/api/watch/next` | POST | 次の会話を生成 |

### シナリオ

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/scenarios` | GET | シナリオ一覧取得 |
| `/api/scenarios/<id>` | GET | シナリオ詳細取得 |

### システム

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/models` | GET | 利用可能なAIモデル一覧 |
| `/health` | GET | ヘルスチェック |

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'feat: add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

### コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/)に従ってください：

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント更新
- `refactor:` リファクタリング
- `test:` テスト追加・修正
- `chore:` その他の変更

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/CaCC-Lab/workplace-roleplay/issues)
- **ドキュメント**: [docs/](docs/)

---

**バージョン**: 2.0.0  
**最終更新**: 2025年12月3日  
**メンテナンス**: 活発にメンテナンス中
