# 🎯 AI職場コミュニケーショントレーナー

<div align="center">
  
  **職場でのコミュニケーションスキルを、AIとの対話で安全に練習できるWebアプリケーション**
  
  🔗 **[デモサイトで体験する](https://workplace-roleplay.cacc-lab.net/)**
  
  [![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![Google Gemini](https://img.shields.io/badge/Google%20Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
  
</div>

---

## 🚀 プロジェクト概要

このプロジェクトは、多くの人が抱える「職場でのコミュニケーションへの不安」を解決するために開発しました。

**解決したい課題：**
- 新入社員や転職者が感じる職場での会話への不安
- 難しい状況（クレーム対応、交渉など）の練習機会の不足
- 実際の場面でトライ＆エラーすることのリスク

**ソリューション：**
最新のAI技術（Google Gemini）を活用し、リアルな職場シナリオで何度でも練習できる環境を提供。30種類以上のシナリオと高度な音声合成機能により、没入感のある練習体験を実現しました。

## 💡 主要機能

<table>
<tr>
<td width="50%" valign="top">

### 🎭 シナリオロールプレイ
**30種類以上の実践的シナリオ**
- 初級：基本的な報連相、依頼の仕方
- 中級：クレーム対応、交渉術
- 上級：難しい人間関係、緊急事態対応

**特徴的な実装：**
- YAMLベースのシナリオ管理システム
- キャラクター設定に基づく自動音声割り当て
- 会話後の詳細なフィードバック生成

</td>
<td width="50%" valign="top">

### 🗣️ 高度な音声合成機能
**30種類の多様な音声タイプ**
- 女性11種、男性15種、中性4種
- 役職・年齢・性別に応じた自動選択
- 感情表現（喜び、困惑、疲れ等）に対応

**技術的工夫：**
- 音声データの事前生成＆キャッシング
- メモリ効率を考慮した自動クリーンアップ
- Web Speech APIへの自動フォールバック

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 💬 雑談練習モード
**状況に応じた会話練習**
- 同僚との日常会話
- 上司との適切なコミュニケーション
- 初対面での会話

**AIによる分析：**
- 話題選択の適切さ
- 敬語使いの正確性
- 会話の流れの自然さ

</td>
<td width="50%" valign="top">

### 📊 強み分析システム
**6つのスキル項目を可視化**
- 共感力、明確な伝達力、傾聴力
- 適応力、前向きさ、プロフェッショナリズム

**データビジュアライゼーション：**
- レーダーチャートで現在の強みを表示
- 時系列グラフで成長を追跡
- パーソナライズされた励ましメッセージ

</td>
</tr>
</table>

### 🎯 その他の特徴的機能
- **会話観戦モード**: 2つのAIモデル間の模範会話を観察学習
- **学習履歴管理**: すべての練習記録を保存し、振り返り可能
- **リアルタイムストリーミング**: Server-Sent Eventsによる低遅延な会話体験

## 🛠️ 技術スタック

### バックエンド
- **Flask 2.0+**: 軽量で柔軟なWebフレームワーク
- **LangChain**: AIモデルとの対話管理、メモリ管理
- **Flask-Session**: セッション管理（ファイルシステム/Redis対応）
- **Redis**: スケーラブルなセッション管理（自動フォールバック機能付き）
- **PyYAML**: シナリオデータの管理

### AI/機械学習
- **Google Gemini API**: 
  - gemini-1.5-pro（高精度応答）
  - gemini-1.5-flash（高速応答）
- **Gemini TTS API**: 30種類の音声による高品質な音声合成
- **LangChain Memory**: 会話履歴の管理

### フロントエンド
- **純粋なJavaScript**: フレームワーク非依存の実装
- **Chart.js**: 強み分析のデータビジュアライゼーション
- **Server-Sent Events**: リアルタイム通信
- **Web Speech API**: 音声合成のフォールバック

## 🏗️ アーキテクチャと実装の工夫

### システムアーキテクチャ

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   フロントエンド  │────▶│  Flask Server    │────▶│ Google Gemini   │
│  (JavaScript)   │ SSE │                  │ API │     API         │
│                 │◀────│  - Session管理    │◀────│                 │
└─────────────────┘     │  - ルーティング    │     └─────────────────┘
                       │  - エラーハンドル   │              │
                       └──────────────────┘              │
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐     ┌─────────────────┐
                       │                  │     │                 │
                       │  Redis Session   │     │  Gemini TTS     │
                       │ (Fallback: File) │     │     API         │
                       │                  │     │                 │
                       └──────────────────┘     └─────────────────┘
```

### 主要な技術的実装

#### 1. **統一TTS管理システム**
```javascript
// tts-common.js - 全ページで一貫した音声制御
class TTSManager {
    constructor() {
        this.audioCache = new Map();
        this.maxCacheSize = 50;
        this.currentAudio = null;
    }
    // 音声の事前生成とキャッシング
    // メモリ効率を考慮した自動クリーンアップ
}
```

#### 2. **LangChainによる高度な会話管理**
```python
# 各モードで独立したメモリを保持
memory_chat = ConversationBufferMemory(memory_key="chat_history")
memory_scenario = ConversationBufferMemory(memory_key="chat_history")
memory_watch = ConversationBufferMemory(memory_key="chat_history")
```

#### 3. **APIキーローテーションシステム**
```python
# api_key_manager.py - レート制限対策
class APIKeyManager:
    def get_next_key(self):
        # 使用状況に基づいて最適なキーを選択
        # エラー時の自動クールダウン
```

#### 4. **非同期音声生成**
- AI応答と並行して音声データを生成
- Base64エンコードでクライアントに送信
- ユーザーアクション時に即座に再生可能

#### 5. **Redis統合セッション管理**
```python
# redis_manager.py - 自動フォールバック機能
class RedisSessionManager:
    def __init__(self, fallback_enabled=True):
        # Redis接続失敗時は自動的にファイルシステムへ
        # エラーメッセージは3要素形式（What/Why/How）
```

## 🎨 開発プロセスと課題解決

### 直面した技術的課題と解決策

#### 1. **音声合成の遅延問題**
**課題**: AI応答生成後に音声を生成すると、ユーザーが音声再生ボタンを押すまでに遅延が発生

**解決策**: 
- AI応答のストリーミング中に並行して音声データを生成
- Base64エンコードされた音声データをレスポンスに含める
- クライアント側でキャッシュし、即座に再生可能に

#### 2. **キャラクター音声の一貫性**
**課題**: シナリオ中で同じキャラクターの音声が変わってしまう

**解決策**:
- シナリオごとに音声IDを固定化
- キャラクター設定（役職・年齢・性別）から適切な音声を自動選択
- セッション中は同一音声を維持

#### 3. **メモリ管理とスケーラビリティ**
**課題**: 音声データのキャッシュによるメモリ圧迫

**解決策**:
- LRU（Least Recently Used）方式でキャッシュサイズを制限
- 自動クリーンアップ機能の実装
- Redisセッションによるスケールアウトの対応

## 📈 成果と学び

### 技術的成果
- **30種類以上のシナリオ**: 実践的な職場状況をカバー
- **高度な音声合成**: 30種類の音声で没入感のある体験を実現
- **リアルタイム通信**: SSEによる低遅延な会話体験
- **柔軟なアーキテクチャ**: 開発環境から本番環境まで対応

### 得られた知見
1. **AIプロンプトエンジニアリング**: キャラクターの一貫性を保つためのプロンプト設計
2. **非同期処理の重要性**: ユーザー体験を損なわない並行処理の実装
3. **フォールバック戦略**: APIの障害に備えた代替手段の準備
4. **メモリ効率**: 限られたリソースでの最適化技術

## 🚀 開発状況と品質保証

### 🔒 セキュリティ対策（完了済み）
- ✅ **XSS（Cross-Site Scripting）対策**: 入力サニタイズと出力エスケープ
- ✅ **CSP（Content Security Policy）**: インラインスクリプト攻撃の防御
- ✅ **CSRF（Cross-Site Request Forgery）対策**: トークンベース認証
- ✅ **シークレットキー管理**: 本番環境での厳格な検証
- ✅ **セッション管理強化**: Redis統合と自動フォールバック機能
- ✅ **包括的テストスイート**: 115個のセキュリティテスト（200テスト通過）

### 🧪 開発環境と品質管理
- ✅ **完全な開発環境セットアップ**: 仮想環境、VSCode統合、パッケージ管理
- ✅ **TDD（テスト駆動開発）**: 200テスト成功、7スキップ（100%パス率）
- ✅ **コード品質ツール**: Black（フォーマッター）、Flake8（リンター）、MyPy（型チェック）
- ✅ **統合テスト**: API、セキュリティ、機能テストを網羅
- ✅ **Pylanceサポート**: IDEによる完全な型推論とエラー検出

### 📊 技術メトリクス（2025年7月17日現在）
- **テストカバレッジ**: 200テスト（115個のセキュリティテスト含む）
- **コード品質**: ゼロのリンターエラー、統一されたコードスタイル
- **セキュリティレベル**: 企業レベルのセキュリティ対策実装済み
- **開発効率**: 即座の開発開始可能な完全セットアップ

### 🔄 今後の展望

#### 次の優先タスク
- ✅ **セッション管理強化**: Redis統合による安全で効率的なセッション処理（完了）
- **データベース統合**: PostgreSQLによるデータ永続化
- **認証システム**: ユーザー登録とログイン機能
- **入力検証の強化**: すべてのAPI入力の統一検証とレート制限

#### 中長期的な機能拡張
- **ユーザー認証システム**: 個人の学習履歴を永続的に保存
- **音声入力対応**: より自然な会話練習の実現
- **リアルタイムフィードバック**: 会話中のアドバイス機能
- **グループ練習機能**: 複数人でのロールプレイ対応
- **ゲーミフィケーション**: バッジやランキングシステム

#### 技術的改善計画
- **コード構造改善**: Flask Blueprintsによるモジュール分割
- **データベース統合**: 永続的なデータ管理システム
- **CI/CDパイプライン**: GitHub Actionsによる自動化
- **Docker化**: 一貫した開発・本番環境

## 💻 クイックスタート

### 前提条件
- Python 3.8以上
- Google Cloud アカウント（Gemini API用）
- Redis（オプション - セッション管理の高速化）

### セットアップ

#### 🚀 自動セットアップ（推奨）
```bash
# 1. クローン
git clone https://github.com/CaCC-Lab/workplace-roleplay.git
cd workplace-roleplay

# 2. 自動セットアップスクリプトを実行
chmod +x setup_dev_env.sh
./setup_dev_env.sh

# 3. 環境変数設定
cp .env.example .env
# .envファイルを編集してGOOGLE_API_KEYを設定

# 4. Redis起動（オプション）
docker-compose up -d redis

# 5. 環境確認
source venv/bin/activate
python verify_environment.py

# 6. 起動
python app.py
```

#### 🔧 手動セットアップ
```bash
# 1. 仮想環境作成
python -m venv venv
source venv/bin/activate  # Unix/macOS
# または venv\Scripts\activate  # Windows

# 2. 依存関係インストール
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 開発ツール

# 3. 環境変数設定
cp .env.example .env
# .envファイルを編集

# 4. 起動
python app.py
```

#### 🧪 開発者向けツール
```bash
# コード品質チェック
black .                   # コードフォーマット
flake8                   # リンター
isort .                  # インポート整理
mypy .                   # 型チェック

# テスト実行
pytest                   # 全テスト実行
pytest tests/security/   # セキュリティテストのみ
pytest -v               # 詳細表示
```

アプリケーションは `http://localhost:5001` で起動します。

### 必須環境変数
```
GOOGLE_API_KEY=your_google_api_key  # Gemini API用
FLASK_SECRET_KEY=your_secret_key    # セッション暗号化用
REDIS_HOST=localhost                # Redis接続（オプション）
REDIS_PORT=6379                     # Redisポート（オプション）
```

## 📁 プロジェクト構成

```
workplace-roleplay/
├── 📱 app.py                    # メインアプリケーション
├── 🧠 strength_analyzer.py      # 強み分析エンジン
├── 🔑 api_key_manager.py        # APIキー管理システム
├── 🔄 utils/                    # ユーティリティモジュール
│   └── redis_manager.py         # Redis統合セッション管理
├── 📚 scenarios/                # シナリオ管理
│   └── data/                    # 30種類のYAMLシナリオ
├── 🎨 static/                   # フロントエンド
│   ├── js/                      # 機能別JavaScript
│   └── css/                     # スタイルシート
├── 🌐 templates/                # HTMLテンプレート
├── 🧪 tests/                    # テストスイート
└── 🐳 docker-compose.yml        # Redis環境構築
```

## 🏆 プロジェクトのハイライト

- **実装規模**: 約5,000行のコード（Python + JavaScript）
- **AIモデル統合**: Google Gemini API（会話・音声・画像生成）
- **パフォーマンス**: SSEによる低遅延ストリーミング（< 100ms）
- **スケーラビリティ**: Redis対応によるマルチインスタンス運用可能
- **メモリ効率**: LRUキャッシュによる効率的なリソース管理
- **セッション管理**: Redis統合と自動フォールバック機能
- **包括的テスト**: 200のテストケースで品質保証

## 📝 ライセンスとコントリビューション

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。

### 開発への参加
- Issue報告やプルリクエストを歓迎します
- 開発ガイドラインは[CONTRIBUTING.md](CONTRIBUTING.md)を参照

## 🤝 連絡先

プロジェクトに関するお問い合わせや提案がございましたら、以下までご連絡ください：

**開発者**: CaCC-Lab
**問い合わせ先**: https://cacc-lab.net/otoiawase/

---

<div align="center">
  
  **Built with ❤️ using Flask and Google Gemini**
  
  このプロジェクトは、AIを活用して誰もが安心して職場コミュニケーションを学べる環境を提供することを目指しています。
  
</div>

