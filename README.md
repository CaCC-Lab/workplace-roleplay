# 🗣️ 職場コミュニケーション練習アプリ

[![CI - Tests and Quality Checks](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/ci.yml/badge.svg)](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/ci.yml)
[![Deploy to Azure VM Production](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/deploy-production.yml/badge.svg)](https://github.com/CaCC-Lab/workplace-roleplay/actions/workflows/deploy-production.yml)
[![Test Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen.svg)](https://github.com/CaCC-Lab/workplace-roleplay)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AIを活用したロールプレイシナリオを通じて、職場でのコミュニケーションスキルを安全に練習できるWebアプリケーションです。

## ✨ 主要機能

### 🎭 シナリオロールプレイ
- **45種類以上の職場シナリオ**でAIと対話練習
- 難易度別（初級・中級・上級）のシナリオ構成
- リアルタイムのAIフィードバック
- 学習ポイントとフィードバックポイントの提示

### 💬 雑談練習モード
- 職場での適切な雑談スキルを向上
- 自然な会話の流れを学習
- **コンテンツモデレーション**: NGワードフィルタ、ループ検出、脱線防止
- **リアルタイムフィードバック**: 会話中に即時アドバイスとより良い表現の提案

### 👀 会話観戦モード
- 2つのAIモデル間の会話を観察して学習
- **インタラクティブクイズ**: 5回の会話ごとにコンテキストベースの3-4択クイズを出題
- **3者会話**: 観戦中に「参加」して3者間の会話に移行可能

### 🏢 ハラスメント対策シナリオ
- 職場でのハラスメント防止・対応を学習
- 11種類の研修シナリオ
- デリケートな内容への配慮（同意画面あり）

### 🏆 ゲーミフィケーション
- **スキルXP**: 6軸（共感力・明確さ・傾聴力・適応力・前向きさ・プロ意識）でXPを蓄積
- **成長グラフ**: 個人ベスト、週次比較、直近10回平均で成長を可視化
- **シナリオアンロック**: 初級→中級→上級を段階的に解放
- **デイリー/ウィークリークエスト**: 軽い学習目標で継続モチベーション維持
- **バッジシステム**: 継続性・多様性・改善度の3カテゴリ9種類のバッジ

### 📊 学習分析・エクスポート
- **学習分析ダッシュボード**: 練習統計、6軸スキル進捗、弱点レポート、週次サマリー
- **会話まとめ・要約**: LLMによるsummary/key_points/learning_pointsの自動生成
- **データエクスポート**: 会話履歴のCSV/JSONダウンロード、学習レポート生成

### 📖 チュートリアル・ヘルプ
- **初回訪問時のステップガイド**: オーバーレイで操作方法を案内（次へ/スキップ）
- 3モード対応（シナリオ・雑談・観戦）
- 進捗管理（完了ステップの記録）
- FAQ

### 📱 レスポンシブデザイン
- モバイル（480px）/ タブレット（768px）/ デスクトップ（1024px）対応
- タッチフレンドリーなUI（入力フォーム最小44px高さ）
- 全画面に `responsive.css` 適用済み

### 🔊 音声機能
- **音声読み上げ**: Gemini TTS APIによる高品質音声出力
- **多言語対応**: 日本語・英語・中国語・韓国語等
- **音声事前生成**: AI応答と同時に音声データを生成、ボタンクリック時に即座再生

### 🎨 キャラクター画像
- AIキャラクター画像生成（Gemini Image Generation API）
- プロフィールハッシュベースのキャッシュで外見の一貫性を確保
- 感情別の表情変化

## 🖥️ 画面一覧

| URL | 画面 | 主要機能 |
|-----|------|---------|
| `/` | トップページ | モード選択、ゲーミフィケーションダッシュボードへのリンク |
| `/chat` | 雑談練習 | AI対話、モデレーション、リアルタイムフィードバック、要約ボタン |
| `/scenario` | シナリオ練習 | AI対話、フィードバック、ゲーミフィケーションフック |
| `/watch` | 会話観戦 | AI同士の対話観察、クイズモーダル、3者会話参加/退出 |
| `/gamification` | ダッシュボード | XPバー、クエスト、バッジ、成長チャート、分析、エクスポート |
| `/scenarios` | シナリオ一覧 | カテゴリ別表示、アンロック状態 |
| `/strength` | 強み分析 | レーダーチャート、6軸スキル可視化 |
| `/journal` | 学習ジャーナル | 学習履歴の振り返り |

### フロントエンドJS構成

| ファイル | 対象画面 | 機能 |
|---------|---------|------|
| `gamification-dashboard.js` | /gamification | XP・クエスト・バッジ・成長チャート（Chart.js）・分析・エクスポート |
| `chat-enhancements.js` | /chat, /scenario | リアルタイムフィードバック表示、モデレーション警告、要約カード |
| `watch-quiz.js` | /watch | クイズモーダル（選択肢・回答・結果）、正答率サマリー |
| `three-way.js` | /watch | 3者会話参加/退出ボタン、メッセージ入力 |
| `tutorial-overlay.js` | 全画面 | 初回訪問ステップガイド、進捗記録 |
| `csrf-manager.js` | 全画面 | CSRF トークン自動付与（25エンドポイント保護） |

## 🛠️ 技術スタック

### バックエンド
| 技術 | バージョン | 用途 |
|-----|----------|------|
| Python | 3.8+ | メイン言語 |
| Flask | 2.0+ | Webフレームワーク |
| Flask-Session | 最新 | セッション管理 |
| LangChain | 0.x | LLM統合 |
| vibelogger | 0.1+ | AI-Nativeロギング |

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
| Gemini Image API | キャラクター画像生成 |
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

### 機能フラグ

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `ENABLE_MODEL_SELECTION` | `false` | AIモデル選択UIの表示 |
| `ENABLE_TTS` | `false` | 音声読み上げ機能 |
| `ENABLE_LEARNING_HISTORY` | `false` | 学習履歴機能 |
| `ENABLE_STRENGTH_ANALYSIS` | `false` | 強み分析機能 |
| `DEFAULT_MODEL` | `gemini/gemini-2.5-flash-lite` | デフォルトAIモデル |

### アプリケーションの起動

```bash
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
│   └── middleware.py        # ミドルウェア（CSRF等）
├── routes/                   # APIルート
│   ├── chat_routes.py       # チャットAPI
│   ├── scenario_routes.py   # シナリオAPI
│   ├── watch_routes.py      # 観戦モードAPI
│   ├── gamification_routes.py # ゲーミフィケーションAPI
│   ├── quiz_routes.py       # 観戦クイズAPI
│   ├── summary_routes.py    # 会話要約API
│   ├── analytics_routes.py  # 学習分析API
│   ├── export_routes.py     # データエクスポートAPI
│   ├── tutorial_routes.py   # チュートリアルAPI
│   ├── three_way_routes.py  # 3者会話API
│   └── ...                  # その他のルート
├── services/                 # ビジネスロジック
│   ├── chat_service.py      # チャットサービス
│   ├── llm_service.py       # LLM統合
│   ├── scenario_service.py  # シナリオ管理
│   ├── gamification_service.py    # XP・成長グラフ
│   ├── user_data_service.py       # ユーザーデータ永続化
│   ├── quest_service.py           # クエスト管理
│   ├── badge_service.py           # バッジシステム
│   ├── unlock_service.py          # シナリオアンロック
│   ├── quiz_service.py            # 観戦クイズ
│   ├── summary_service.py         # 会話要約
│   ├── moderation_service.py      # コンテンツモデレーション
│   ├── realtime_feedback_service.py # リアルタイムフィードバック
│   ├── analytics_service.py       # 学習分析
│   ├── export_service.py          # データエクスポート
│   ├── tutorial_service.py        # チュートリアル
│   ├── three_way_service.py       # 3者会話
│   ├── multilingual_tts_service.py # 多言語TTS
│   ├── character_image_service.py  # キャラクター画像
│   ├── gamification_hooks.py      # 既存ルート→ゲーミフィケーション統合
│   ├── gamification_constants.py  # 共有定数
│   ├── gamification_vibelogger.py # ゲーミフィケーションログ
│   └── ...                        # その他のサービス
├── scenarios/                # シナリオデータ
│   ├── __init__.py          # シナリオローダー
│   └── data/                # YAMLシナリオファイル（45+件）
├── static/                   # 静的ファイル
│   ├── css/                 # スタイルシート
│   │   ├── style.css        # メインスタイル
│   │   ├── modern.css       # モダンUI
│   │   ├── dark-mode.css    # ダークモード
│   │   └── responsive.css   # レスポンシブ対応
│   └── js/                  # JavaScript
├── templates/                # HTMLテンプレート
├── tests/                    # テストコード（120+件）
│   ├── test_services/       # サービステスト
│   ├── test_routes/         # ルートテスト
│   └── security/            # セキュリティテスト
├── utils/                    # ユーティリティ
├── .kiro/                    # Kiro Spec（Living Spec）
│   ├── specs/gamification/  # ゲーミフィケーション仕様
│   └── steering/            # 基盤Steering
├── .github/workflows/        # GitHub Actions
├── requirements.txt          # 本番依存パッケージ
├── requirements-dev.txt      # 開発依存パッケージ
└── README.md                 # このファイル
```

## 📝 API リファレンス

### チャット関連

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/chat` | POST | 雑談モードでメッセージ送信（モデレーション+リアルタイムFB付き） |
| `/api/scenario_chat` | POST | シナリオモードでメッセージ送信 |
| `/api/chat_feedback` | POST | 雑談のフィードバック取得（+ゲーミフィケーションフック） |
| `/api/scenario_feedback` | POST | シナリオのフィードバック取得（+ゲーミフィケーションフック） |

### 観戦モード

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/watch/start` | POST | 観戦モード開始 |
| `/api/watch/next` | POST | 次の会話を生成（+クイズ自動出題） |

### 3者会話

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/three-way/join` | POST | 観戦モードから3者会話に参加 |
| `/api/three-way/message` | POST | ユーザー発言を追加 |
| `/api/three-way/leave` | POST | 3者会話を退出して観戦に戻る |

### ゲーミフィケーション

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/gamification/dashboard` | GET | ダッシュボード（XP・クエスト・バッジ概要） |
| `/api/gamification/growth` | GET | 成長グラフデータ |
| `/api/gamification/quests` | GET | アクティブクエスト一覧 |
| `/api/gamification/badges` | GET | バッジ一覧 |
| `/api/gamification/unlock-status` | GET | シナリオアンロック状態 |

### クイズ

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/quiz/generate` | POST | クイズ生成 |
| `/api/quiz/answer` | POST | クイズ回答・評価 |
| `/api/quiz/summary` | GET | セッション正答率サマリー |

### 学習分析

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/analytics/practice-stats` | GET | 練習統計 |
| `/api/analytics/skill-progress` | GET | 6軸スキル進捗 |
| `/api/analytics/weakness` | GET | 弱点レポート |
| `/api/analytics/weekly-summary` | GET | 週次サマリー |

### 会話要約

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/summary/generate` | POST | 会話要約生成（summary/key_points/learning_points） |

### データエクスポート

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/export/csv` | POST | 会話履歴CSVダウンロード |
| `/api/export/json` | POST | 会話履歴JSONダウンロード |
| `/api/export/report` | GET | 学習レポート |

### チュートリアル

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/tutorial/steps` | GET | チュートリアルステップ（?mode=scenario\|chat\|watch） |
| `/api/tutorial/progress` | GET | ユーザー進捗 |
| `/api/tutorial/complete` | POST | ステップ完了マーク |
| `/api/tutorial/faq` | GET | FAQ一覧 |
| `/api/tutorial/first-visit` | GET | 初回訪問チェック |

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

## 🧪 開発

### 開発ツールのインストール

```bash
pip install -r requirements-dev.txt
```

### コード品質チェック

```bash
black .        # コードフォーマット
flake8         # リンター
isort .        # インポート順序
mypy .         # 型チェック
```

### テストの実行

```bash
# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=. --cov-report=html

# ゲーミフィケーション関連のみ
pytest tests/test_services/ -k "gamification or quest or badge or unlock or quiz or xp" -v

# 新規サービスのみ
pytest tests/test_services/test_summary_service.py tests/test_services/test_moderation_service.py tests/test_services/test_analytics_service.py -v
```

## 🔐 セキュリティ

- ✅ **XSS対策**: 入力サニタイズと出力エスケープ
- ✅ **CSRF対策**: トークンベースの保護
- ✅ **CSP**: Content Security Policyヘッダー
- ✅ **セッション管理**: セキュアなCookie設定（SameSite, HttpOnly）
- ✅ **シークレット管理**: 本番環境での厳格な検証
- ✅ **入力検証**: メッセージ長制限、シナリオID検証、レート制限
- ✅ **コンテンツモデレーション**: NGワードフィルタ、ループ検出

## 🚢 デプロイ

### 自動デプロイ（推奨）

mainブランチへのプッシュで自動的にAzure VMにデプロイされます。

```bash
git push origin main
```

### 手動デプロイ

```bash
ssh -i your_key.pem user@your_server
cd ~/workplace-roleplay
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart workplace-roleplay
```

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

**バージョン**: 3.1.0
**最終更新**: 2026年4月3日
**メンテナンス**: 活発にメンテナンス中
