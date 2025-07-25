# TODO.md - 開発実装計画

このファイルは、要件定義書に基づいて今後実装すべき機能をまとめたものです。
優先度：高（必須）、中（重要）、低（あれば良い）で分類しています。

## 📌 フェーズ1: 基盤機能（優先度：高）

### 1.1 セキュリティ・認証基盤
- [ ] **ユーザー認証システムの実装**
  - [ ] ユーザー登録・ログイン機能
  - [x] **セッション管理の強化**（2025年7月17日実装）
    - [x] Redis統合セッション管理
    - [x] 自動フォールバック機能（Redis→Filesystem）
    - [x] セッション監視API（/api/session/health, /api/session/info）
    - [x] 包括的テストスイート（249行のテストコード）
  - [ ] パスワードハッシュ化（bcrypt等）
  - [ ] JWT認証の実装（APIセキュリティ向上）

- [ ] **データセキュリティの強化**
  - [ ] HTTPS対応（SSL証明書の設定）
  - [ ] 会話データの暗号化保存
  - [ ] SQLインジェクション対策
  - [ ] **入力検証の強化**（CSRF完了後の次の優先タスク）
    - [ ] すべてのAPI入力の統一検証
    - [ ] SQLインジェクション対策の徹底
    - [ ] ファイルアップロード制限
    - [ ] レート制限の実装
  - [x] **XSS対策の実装**（基本実装完了 - 2025年6月29日）
    - [x] 入力値のサニタイズ（SecurityUtils.sanitize_input実装済み）
    - [x] 出力エスケープの徹底（SecurityUtils.escape_html実装済み）
  - [x] **CSP（Content Security Policy）対策の実装**（2025年6月29日実装）
    - [x] 段階的実装戦略（Report-Only → Mixed → Strict）
    - [x] CSPミドルウェアの作成（utils/csp_middleware.py）
    - [x] nonceベースのインラインスクリプト許可
    - [x] 違反レポート収集・分析機能
    - [x] 26個のテストケース追加（100%パス）
  - [x] **CSRF対策の実装**（2025年6月29日実装）
    - [x] CSRFTokenクラスの実装（SecurityUtils拡張）
    - [x] CSRFMiddlewareによるFlask統合
    - [x] 主要APIエンドポイントの保護（7エンドポイント）
    - [x] フロントエンド統合（csrf-manager.js）
    - [x] セッションCookie設定強化（SameSite, HttpOnly, Secure）
    - [x] 40個のCSRFテストケース追加（100%パス）
    - [x] **既存テストのCSRF対応**（2025年6月29日完了）
      - [x] 19個の失敗テストをすべて修正
      - [x] CSRFTestClientラッパーの作成（tests/helpers/csrf_helpers.py）
      - [x] test_app_integration.py（17テスト修正）
      - [x] test_xss.py（3テスト修正）
      - [x] test_xss_vulnerabilities.py（1テスト修正）
      - [x] ループ処理でのCSRFトークンリセット対応
      - [x] 全テスト結果：189テスト通過、7スキップ

- [x] **シークレットキー管理の強化**（2025年6月29日実装）
  - [x] 本番環境での検証強化
    - [x] デフォルトキーの拒否
    - [x] 最小長（32文字）の要求
    - [x] 単純パターンの検出
  - [x] 開発環境での警告表示
  - [x] セキュアキー生成ツール（scripts/generate_secret_key.py）
  - [x] セキュリティユーティリティ（config/security_utils.py）

### 1.2 データベース統合
- [ ] **SQLiteまたはPostgreSQLの導入**
  - [ ] ユーザーテーブル設計
  - [ ] 会話履歴テーブル設計
  - [ ] 学習進捗テーブル設計
  - [ ] マイグレーションスクリプト作成

### 1.3 会話メモリの永続化
- [ ] **ユーザー別会話履歴の保存**
  - [ ] DBへの会話履歴保存機能
  - [ ] 会話履歴の検索・フィルタリング
  - [ ] 会話のエクスポート機能（CSV/JSON）

## 📌 フェーズ2: コア機能強化（優先度：高〜中）

### 2.1 ロールプレイモード強化
- [ ] **リアルタイムフィードバック機能**
  - [ ] 会話中の即時アドバイス表示
  - [ ] 複数の回答案の提示
  - [ ] 「より良い表現」の提案機能

- [x] **長所・ポジティブフィードバックの強化**（2025年6月10日実装）
  - [x] ユーザーの強み分析機能
    - [x] 6つのコミュニケーションスキル項目の定義（共感力、明確な伝達力、傾聴力、適応力、前向きさ、プロフェッショナリズム）
    - [x] 会話履歴からのスキル分析
    - [x] トップ3の強み表示
  - [x] 成長グラフの表示
    - [x] レーダーチャートによる現在のスキル可視化
    - [x] 時系列グラフによる成長推移表示
    - [x] Chart.jsライブラリの統合
  - [x] 励ましメッセージの自動生成
    - [x] 成長パターンに基づくメッセージ生成
    - [x] パーソナライズされた励ましの追加
    - [x] 継続的な練習を促すメカニズム

- [ ] **職場のあなた再現シート統合**
  - [ ] シート入力フォームの作成
  - [ ] シート情報に基づくパーソナライズ
  - [ ] カスタムシナリオ生成機能

### 2.2 雑談・観戦モード強化
- [ ] **ユーザー介入機能（3者会話）**
  - [ ] 観戦中の「参加」ボタン実装
  - [ ] 3者会話のUIデザイン
  - [ ] 発言順序の管理ロジック

- [ ] **テーマプリセットの拡充**
  - [ ] カテゴリ別テーマ管理
  - [ ] ユーザー投稿テーマ機能
  - [ ] 人気テーマランキング

- [ ] **会話まとめ・要約機能**
  - [ ] 会話終了時の自動要約生成
  - [ ] キーポイントの抽出
  - [ ] 学習ポイントのハイライト

### 2.3 コンテンツモデレーション
- [ ] **不適切発言のフィルタリング**
  - [ ] NGワードリストの管理
  - [ ] AI発言の事前チェック
  - [ ] ユーザー通報機能

- [ ] **会話品質管理**
  - [ ] ループ検出（同じ話題の繰り返し）
  - [ ] 脱線防止メカニズム
  - [ ] 会話長さの自動調整

## 📌 フェーズ3: UI/UX改善（優先度：中）

### 3.1 ユーザビリティ向上
- [ ] **ダークモード対応**
  - [ ] テーマ切り替え機能
  - [ ] ユーザー設定の保存
  - [ ] システム設定との連動

- [ ] **レスポンシブデザイン改善**
  - [ ] モバイル対応の強化
  - [ ] タブレット最適化
  - [ ] タッチ操作の改善

- [ ] **アクセシビリティ向上**
  - [ ] フォントサイズ調整機能
  - [ ] 読み上げ機能対応
  - [ ] キーボードナビゲーション

### 3.2 チュートリアル・ヘルプ
- [ ] **初回利用者向けガイド**
  - [ ] インタラクティブチュートリアル
  - [ ] ツールチップの追加
  - [ ] FAQ・ヘルプページ

- [ ] **操作説明動画**
  - [ ] 各モードの使い方動画
  - [ ] ベストプラクティス紹介
  - [ ] トラブルシューティング

## 📌 フェーズ4: 高度な機能（優先度：中〜低）

### 4.1 グループ・セミナー機能
- [ ] **複数ユーザー同時利用**
  - [ ] ルーム作成・参加機能
  - [ ] 画面共有機能
  - [ ] インストラクターモード

- [ ] **グループフィードバック**
  - [ ] 参加者間の相互評価
  - [ ] グループ討議機能
  - [ ] 成果共有機能

### 4.2 分析・レポート機能
- [ ] **学習分析ダッシュボード**
  - [ ] 練習時間の統計
  - [ ] スキル向上の可視化
  - [ ] 弱点分析レポート

- [ ] **定期レポート生成**
  - [ ] 週次/月次レポート
  - [ ] PDF出力機能
  - [ ] メール配信機能

### 4.3 エクスポート・連携機能
- [ ] **データエクスポート**
  - [ ] 会話履歴のPDF出力
  - [ ] Markdown形式出力
  - [ ] 学習記録のCSV出力

- [ ] **外部サービス連携**
  - [ ] カレンダー連携（練習予定）
  - [ ] Slack/Teams通知
  - [ ] 学習管理システム（LMS）連携

## 📌 フェーズ5: 将来的な拡張（優先度：低）

### 5.1 音声機能
- [ ] **音声入力対応**
  - [ ] 音声認識（STT）統合
  - [ ] リアルタイム文字起こし
  - [ ] 音声コマンド対応

- [x] **音声出力対応**
  - [x] テキスト読み上げ（TTS）- Gemini TTS APIで実装済み（2025年6月6日）
    - [x] 参考プロジェクトからの実装移植完了
    - [x] 複数の音声タイプ（男性・女性・中性）のサポート
    - [x] WAV形式での高品質音声出力（24kHz、16ビット、モノラル）
    - [x] Web Speech APIによるフォールバック機能
    - [x] シナリオごとの固定音声設定（2025年6月9日）
      - [x] 役職・年齢・性別に応じた30種類の音声マッピング
      - [x] ロールプレイ中の音声一貫性を確保
      - [x] 雑談練習モードでのTTS対応
    - [x] **音声事前生成機能**（2025年6月10日）
      - [x] AI応答と同時に音声データを生成
      - [x] 生成済み音声のキャッシュ機能
      - [x] ボタンクリック時の即座再生
      - [x] メモリ管理（50個超で自動クリーンアップ）
      - [x] 視覚的フィードバック（準備完了インジケーター）
  - [x] 感情を込めた音声生成（音声スタイルの制御）- 部分的に実装済み
    - [x] 感情検出機能の実装
    - [x] プロンプトによる感情表現（同一音声で異なる感情を表現）
  - [ ] 多言語音声対応（現在は日本語のみ）

### 5.2 ビジュアル機能（新規提案：2025年6月9日）
- [x] **AIキャラクター画像生成**（部分的に実装済み - 2025年6月10日）
  - [x] Gemini Image Generation API (gemini-2.0-flash-preview-image-generation) の統合
  - [x] セリフに合わせた相手役の表情画像生成
  - [x] シナリオのキャラクター設定に基づいた詳細なプロンプト作成
  - [x] 感情検出結果を表情に反映（喜び、悲しみ、怒り、困惑など）
  - [x] 職場環境を背景とした画像生成
  - [x] 生成画像のキャッシュ機能（同じ感情・キャラクターの再利用）
  - [ ] **キャラクターの一貫性問題の解決**（現在無効化中）
    - [ ] 同一キャラクターの外見統一性の確保
    - [ ] より高度なプロンプトエンジニアリング
    - [ ] 代替アプローチの検討（事前生成画像セット等）
  
- [x] **画像表示機能の実装**（実装済み - 2025年6月10日）
  - [x] 会話画面への画像表示エリアの追加
  - [x] 画像の適切なサイズ調整とレイアウト
  - [x] 画像生成中のローディング表示
  - [x] 画像生成エラー時のフォールバック（デフォルト画像）
  
- [x] **画像生成プロンプトの最適化**（実装済み - 2025年6月10日）
  - [x] キャラクター設定（年齢、性別、役職）の視覚化
  - [x] 日本のビジネスシーンに適した服装・外見
  - [x] 表情と感情の対応マッピング
  - [x] シナリオごとの背景設定（会議室、オフィス、休憩室など）

### 5.3 ゲーミフィケーション
- [ ] **ポイント・バッジシステム**
  - [ ] 練習ポイントの付与
  - [ ] 実績バッジの獲得
  - [ ] レベルアップシステム

- [ ] **ランキング・競争要素**
  - [ ] 週間/月間ランキング
  - [ ] フレンド機能
  - [ ] チャレンジモード

### 5.4 AI機能の高度化
- [ ] **表情・感情分析**
  - [ ] Webカメラ統合
  - [ ] 表情認識
  - [ ] 感情フィードバック

- [ ] **マルチモーダル対応**
  - [ ] 画像を使った会話
  - [ ] ジェスチャー認識
  - [ ] VR/AR対応

## 🔧 技術的改善

### インフラ・運用
- [ ] **Docker化**
  - [ ] Dockerfileの作成
  - [ ] docker-compose設定
  - [ ] 開発環境の統一

- [ ] **CI/CD パイプライン**
  - [ ] GitHub Actions設定
  - [ ] 自動テスト実行
  - [ ] 自動デプロイ

- [ ] **監視・ログ管理**
  - [ ] エラー監視（Sentry等）
  - [ ] パフォーマンス監視
  - [ ] ログ集約・分析

### コード品質
- [ ] **テストカバレッジ向上**
  - [ ] ユニットテスト作成
  - [ ] 統合テスト作成
  - [ ] E2Eテスト実装

- [ ] **リファクタリング**
  - [ ] コードの構造化改善
  - [ ] 型ヒントの完全化
  - [ ] ドキュメント整備

## 📅 実装スケジュール案

### 短期（1-2ヶ月）
- フェーズ1の完了（セキュリティ基盤）
- フェーズ2.1の開始（ロールプレイ強化）

### 中期（3-6ヶ月）
- フェーズ2の完了
- フェーズ3の実装
- フェーズ4の一部着手

### 長期（6ヶ月以降）
- フェーズ4の完了
- フェーズ5の検討・部分実装
- 継続的な改善とメンテナンス

## 💡 注意事項

1. **優先順位の見直し**
   - ユーザーフィードバックに基づいて優先順位を定期的に見直す
   - 技術的な依存関係を考慮して実装順序を調整

2. **段階的リリース**
   - 機能ごとにフィーチャーフラグを使用
   - A/Bテストによる効果測定
   - 段階的なロールアウト

3. **パフォーマンス考慮**
   - 各機能実装時にパフォーマンステストを実施
   - スケーラビリティを考慮した設計

---

最終更新日: 2025年7月17日

## 📝 実装履歴

### 2025年7月17日

**🔄 Redis統合セッション管理の実装**
- **Docker Compose環境の構築**
  - 本番用Redisサービス（workplace-roleplay-redis）
  - テスト用Redisサービス（workplace-roleplay-redis-test）
  - ネットワーク分離とヘルスチェック設定
  - CodeRabbit推奨のセキュリティ改善（network isolation）

- **RedisSessionManagerクラスの実装**
  - 自動フォールバック機能（Redis→Filesystem）
  - エラーハンドリングの3要素形式（What/Why/How）
  - デコレータパターンによるフォールバック処理
  - 型ヒント改善（Optional使用）
  - 包括的な接続管理とヘルスチェック

- **Flask-Sessionとの統合**
  - app.pyでのRedis優先セッション管理
  - 環境に応じた設定切り替え（開発/本番）
  - セッション監視API実装
    - /api/session/health（健全性チェック）
    - /api/session/info（接続情報取得）
    - /api/session/clear（セッションクリア）

- **包括的なテストスイート作成**
  - 11個のRedisセッション統合テスト
  - Redis接続、データ永続化、並行性、有効期限の検証
  - フォールバック機能のテスト
  - CodeRabbit指摘によるテスト効率化（sleep時間短縮: 2s→0.2s）

- **開発ワークフロー改善**
  - 適切なGitワークフロー（feature branch → PR #1）
  - CodeRabbitレビュー対応（5つの改善点すべて実装）
  - マージコンフリクトの解決

### 2025年6月29日

**🎯 開発環境セットアップとPylanceエラー解決**
- **仮想環境の構築とパッケージ管理**
  - Python仮想環境の作成（venv）
  - 本番・開発依存関係の統合インストール
  - VSCode設定ファイル（.vscode/settings.json）の作成
  - 環境確認スクリプト（verify_environment.py）の作成
  - セットアップ自動化スクリプト（setup_dev_env.sh）の作成
  - Pylanceインポートエラー（Flask、pytest）の完全解決

**🔧 CSPミドルウェアのバグ修正**
- **CSP除外デコレータの修正**
  - `@csp_exempt`デコレータが正しく動作するよう修正
  - `_add_csp_header`メソッドでの`g.csp_exempt`チェック追加
- **違反数制限機能の修正**
  - メモリ保護機能が正しく動作するよう修正
  - 制限到達時の最古要素削除ロジックの改善

**🧪 テスト環境の完全整備**
- **全テスト成功の達成**
  - 196テスト中189テスト成功（7スキップは正常）
  - 失敗テストゼロの健全な状態を実現
  - CSPミドルウェア関連の2つの失敗テストを修正
  - テストカバレッジの維持・向上

**💾 開発ツールチェーンの完備**
- **コード品質ツールの統合**
  - Black（コードフォーマッター）
  - Flake8（リンター）
  - isort（インポート順序）
  - MyPy（型チェッカー）
  - pytest（テストフレームワーク）

**セキュリティ強化：シークレットキー管理**
- TDDアプローチによる実装（Red→Green→Refactor）
- 8つのセキュリティテストケースを追加（tests/security/test_secret_key.py）
- 本番環境での厳格な検証（32文字以上、複雑性要件）
- 開発環境での警告メカニズム
- セキュアキー生成ツールの作成
- 既存の104個のテストとの互換性維持

**セキュリティ強化：XSS対策**
- TDDアプローチによる実装
- 9つのXSSテストケースを追加（tests/security/test_xss.py）
- SecurityUtilsクラスが既に実装されていることを発見
- 入力サニタイズ（危険なタグ、イベントハンドラ、プロトコル除去）
- 出力エスケープ（HTML特殊文字の適切なエスケープ）
- エラーメッセージの安全な処理（機密情報の除去）
- モデル名バリデーションの修正（Geminiモデル名に対応）

**セキュリティ強化：CSP（Content Security Policy）対策**
- TDDアプローチによる包括的実装
- 26つのCSPテストケース追加（tests/test_csp_security.py、tests/test_csp_middleware.py）
- 段階的実装戦略（Phase 1: Report-Only → Phase 2: Mixed → Phase 3: Strict）
- CSPミドルウェアクラス（utils/csp_middleware.py）
- nonceベースのセキュアなインラインスクリプト許可機能
- 違反レポート自動収集・分析システム
- 実装ガイドと使用例の提供

**セキュリティ強化：CSRF（Cross-Site Request Forgery）対策**
- TDDアプローチによる包括的実装
- 40個のCSRFテストケース追加（tests/security/test_csrf.py、tests/test_csrf_integration.py）
- CSRFTokenクラス（utils/security.py拡張）- 暗号学的に安全なトークン生成
- CSRFMiddlewareによるFlask統合とデコレータベース保護
- 主要APIエンドポイント保護（7エンドポイント）
- フロントエンド統合（static/js/csrf-manager.js）- 自動トークン管理
- セッションCookie設定強化（SameSite, HttpOnly, Secure）
- CSRF違反ログ・監視システム

**🎉 プロジェクト状況総括**
- ✅ 開発環境セットアップ完了（仮想環境、VSCode設定）
- ✅ Pylanceエラー完全解決（Flask、pytest等のインポート問題）
- ✅ シークレットキー管理強化（8テスト追加）
- ✅ XSS対策実装（9テスト追加）  
- ✅ CSP対策実装（26テスト追加）
- ✅ CSRF対策実装（40テスト追加）
- ✅ 既存テスト全修正（19テスト対応）
- ✅ CSPミドルウェアバグ修正（2テスト修正）
- **合計**: 104個のセキュリティテスト追加、189テスト通過（7スキップ）
- **開発環境**: 完全整備、即座の開発開始可能
- **次のフェーズ**: セッション管理・入力検証強化

### 2025年6月11日
- **音声生成機能の改善とバグ修正**
  - 音声再生ボタンの停止機能修正
  - 統一TTS機能（tts-common.js）への完全移行
  - 音声生成の一貫性問題の解決
  - キャッシュ管理の改善
  - Web Speech APIフォールバック機能の統一

### 2025年6月10日
- **長所・ポジティブフィードバックの強化機能を実装**
  - 強み分析機能（strength_analyzer.py）
  - 強み分析ページ（/strength_analysis）
  - レーダーチャートと成長推移グラフ
  - 既存のフィードバック機能への統合
  - ホームページへの強み分析カードの追加