# 職場コミュニケーション練習アプリ

このアプリケーションは、職場でのコミュニケーションスキルを安全に練習できる環境を提供します。AIとの対話を通じて、実際の職場で役立つコミュニケーション能力の向上を支援します。

## 🌟 主な機能

### 1. シナリオロールプレイ 📝
- 30種類以上の実践的な職場シナリオを収録
- シナリオの難易度別分類（初級〜上級）
- AIと対話形式でリアルな状況を練習
- 会話終了後に詳細なフィードバックを取得
- 練習履歴の記録と振り返り
- **音声読み上げ機能**（2025年6月9日追加）
  - AIの応答を自然な音声で再生
  - シナリオごとに役職・年齢・性別に応じた固定音声を使用
  - ロールプレイ中は一貫した音声で没入感を維持

### 2. 雑談練習モード 💬
- 職場での適切な雑談スキルを向上
- 相手（同僚・先輩・上司など）や状況に応じた会話練習
- 会話スキルに関する具体的なフィードバック
- 実践的なアドバイスの提供
- **音声読み上げ対応**：AIの応答を音声で聞くことが可能

### 3. 会話観戦モード 👥
- 2つのAIモデル間の会話をリアルタイムで観察
- 会話の進行をステップバイステップで確認
- 自然な会話の流れと職場での適切なコミュニケーションを学習
- 異なるAIモデルの組み合わせで多様な会話パターンを観察

### 4. 学習記録・分析機能 📊
- 練習した会話の履歴を保存
- シナリオごとの進捗状況を記録
- 練習時間の自動計測
- 学習の振り返りと改善点の分析

### 5. キャラクター画像生成機能 🎨（現在一時無効化中）
- Google Gemini Image Generation APIによるキャラクター画像生成
- 感情に応じた表情の動的変更
- キャラクターの一貫性を保つための詳細なプロンプト制御
- 役職や年齢に応じた適切な外見の生成
- **注**: 現在、技術的な制約により一時的に無効化されています

## 🧠 対応AIモデル

### Google Gemini専用
- **Gemini-1.5-pro**: 高精度な応答を提供
- **Gemini-1.5-flash**: 高速な応答を提供

### 音声読み上げ機能（2025年6月9日実装）
- Gemini TTS API (gemini-2.5-flash-preview-tts)を使用した高品質な音声合成
- **30種類の多様な音声タイプ**から状況に応じて自動選択：
  - **女性音声（11種）**: Kore（標準的）、Aoede（明るい）、Callirrhoe（おおらか）、Leda（優しい）、Algieba（温かい）、Autonoe（明るい）、Despina（陽気）、Erinome（柔らかい）、Laomedeia（流暢）、Pulcherrima（美しい）、Vindemiatrix（上品）
  - **男性音声（15種）**: Orus（会社的）、Alnilam（プロフェッショナル）、Charon（深みのある）、Fenrir（力強い）、Iapetus（威厳のある）、Algenib（親しみやすい）、Rasalgethi（独特で印象的）、Achernar（明瞭）、Achird（フレンドリー）、Gacrux（安定感のある）、Zubenelgenubi（バランスの取れた）、Sadachbia（知的）、Sadaltager（知識豊富）、Sulafat（エネルギッシュ）、Enceladus（落ち着いた）
  - **中性音声（4種）**: Puck（元気）、Zephyr（明るい）、Umbriel（神秘的）、Schedar（均等）
- **シナリオに応じた固定音声機能**：
  - 各シナリオのキャラクター設定（役職・年齢・性別）に基づいて音声を自動割り当て
  - ロールプレイ中は同一音声を維持し、一貫性と没入感を確保
  - 感情表現はプロンプトで制御（同じ声で異なる感情を表現）
- WAV形式（24kHz、16ビット、モノラル）での高品質音声出力
- フォールバックとしてWeb Speech APIをサポート

## 💻 動作環境

- Python 3.8以上
- Flask 2.0以上
- インターネット接続（Google Gemini APIの利用に必須）
- モダンブラウザ（音声読み上げ機能にはWeb Speech API対応ブラウザが必要）

## 🚀 セットアップ

1. リポジトリのクローン
```bash
git clone https://github.com/CaCC-Lab/roleplay-chatbot-wepapp.git
cd roleplay-chatbot-wepapp
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

6. ブラウザで以下のURLにアクセス
```
http://localhost:5001
```

## 📝 環境変数の設定例

```
# 基本設定
FLASK_SECRET_KEY=your_secret_key_here
GOOGLE_API_KEY=AI...   # Google APIキー（必須）
                       # 以下の機能で使用されます：
                       # - Gemini AIモデル（会話応答）
                       # - Gemini TTS API（音声読み上げ）
                       # - Gemini Image Generation API（画像生成、現在無効化中）

# セッション設定
SESSION_TYPE=filesystem
# SESSION_FILE_DIR=./flask_session  # セッションファイルの保存場所（オプション）

# Redisセッション（オプション、高負荷環境向け）
# SESSION_TYPE=redis
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=your_password
# REDIS_DB=0
```

## 📚 機能詳細

### シナリオロールプレイ機能
- 初級：基本的なコミュニケーションスキル向け
- 中級：より複雑な状況や対人関係向け
- 上級：難しい交渉や緊張状況向け

### フィードバック機能
- 話し方の適切さの評価
- 質問や確認の的確さの分析
- 改善点の具体的な提案
- 次回練習時の注目ポイント提示

### Gemini専用設計
- Google Gemini APIを使用した高品質な日本語応答
- モデルの特性を活かした自然な会話練習
- Gemini TTS APIによる高品質な音声読み上げ機能

### 音声合成機能の特徴
- **30種類の多様な音声タイプ**: 年齢、性別、役職に応じた自然な音声を自動選択
- **シナリオ固定音声**: 各シナリオで一貫した音声を使用し、没入感を維持
- **感情表現**: 同じ音声で異なる感情（喜び、困惑、疲れなど）を表現
- **高品質音声**: WAV形式（24kHz、16ビット、モノラル）での出力
- **フォールバック機能**: Gemini TTS APIが利用できない場合はWeb Speech APIに自動切り替え

## 🛠 開発者向け情報

### ディレクトリ構成
```
/
├── static/                       # 静的ファイル
│   ├── css/                      # CSSファイル
│   └── js/                       # JavaScriptファイル
│       ├── chat.js               # 雑談モード用JS
│       ├── journal.js            # 学習記録用JS
│       ├── model-selection.js    # モデル選択用JS
│       ├── scenario.js           # シナリオモード用JS
│       ├── scenarios_list.js     # シナリオ一覧用JS
│       └── watch.js              # 観戦モード用JS
├── templates/                    # Flaskテンプレート
│   ├── chat.html                 # 雑談モードページ
│   ├── index.html                # トップページ
│   ├── journal.html              # 学習記録ページ
│   ├── scenario.html             # シナリオページ
│   ├── scenarios_list.html       # シナリオ一覧ページ
│   └── watch.html                # 観戦モードページ
├── scenarios/                    # シナリオ関連
│   ├── __init__.py               # シナリオロード処理
│   └── data/                     # シナリオデータ（YAMLファイル）
├── flask_session/                # セッションデータ保存場所
├── roleplay-chatbot-wepapp-main.py # メインアプリケーション
├── requirements.txt              # 依存パッケージ
├── requirements-dev.txt          # 開発用依存パッケージ
└── azure-webapp-settings.md      # Azureデプロイガイド
```

### 開発用依存パッケージ
```bash
pip install -r requirements-dev.txt
```

以下の開発ツールが導入されます：
- pytest: テスト実行
- black: コードフォーマッタ
- flake8: リンター
- isort: インポート順整理
- mypy: 型チェッカー

### シナリオの追加方法
1. `scenarios/data/` ディレクトリに新しいYAMLファイルを作成（例：`scenarioXX.yaml`）
2. 以下の形式でシナリオ情報を記述：
```yaml
title: シナリオのタイトル
description: シナリオの詳細説明
difficulty: 初級/中級/上級
tags:
  - タグ1
  - タグ2
role_info: AIは〇〇役、あなたは××
character_setting:
  personality: キャラクターの性格
  speaking_style: 話し方の特徴
  situation: 現在の状況
  initial_approach: 最初の声かけ
learning_points:
  - 学習ポイント1
  - 学習ポイント2
feedback_points:
  - フィードバックの観点1
  - フィードバックの観点2
```

## 🚀 Azureへのデプロイ

Azure Web Appへのデプロイ方法については、`azure-webapp-settings.md`を参照してください。主な設定内容：

1. 必要な環境変数の設定
2. セッションの保存方法（ファイルシステムまたはRedis）
3. アプリケーション設定の構成方法

## 🔒 プライバシーとセキュリティ

- Google Gemini APIを使用する場合、会話データはGoogleのサービスに送信されます
- 音声読み上げ機能はGemini TTS APIを使用し、テキストのみがGoogleに送信されます
- 画像生成機能（現在無効化中）はGemini Image Generation APIを使用し、キャラクター描写のプロンプトがGoogleに送信されます
- セッションデータは一時的にサーバーに保存され、セッション終了後に自動削除されます
- APIキーは環境変数で管理し、ソースコードには含まれません

## 📄 ライセンス

[MITライセンス](LICENSE)

## 📝 注意事項

- このアプリケーションは学習・練習用途を想定しています
- AIの応答は参考程度にお考えください
- 実際の職場での行動指針は、所属組織の方針に従ってください
- セキュリティの観点から、本番環境では適切なセッション管理（Redis推奨）を行ってください

## 🔒 セッション設定

アプリケーションはデフォルトでローカルファイルシステムにセッションデータを保存します。環境変数で設定を変更できます：

### ファイルシステムセッション（デフォルト）
```
SESSION_TYPE=filesystem
SESSION_FILE_DIR=/path/to/session/files  # オプション
```

### Redisセッション（スケーラブルな環境向け）
```
SESSION_TYPE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password  # 必要な場合
REDIS_DB=0
```

## Azure Web Appへのデプロイ

Azure Web Appにデプロイする場合は、`azure-webapp-settings.md`を参照してください。

