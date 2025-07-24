# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Celeryを使用したアチーブメントチェックの非同期化
  - 指数バックオフ付きリトライ機構（最大3回、60-240秒）
  - エラー分類（リトライ可能/永続的エラー）
  - analyticsキューでの効率的な処理

### Changed
- アチーブメントチェック処理をメインリクエストサイクルから分離
- APIレスポンス時間の大幅改善

### Fixed
- アチーブメントチェックによるAPIブロッキングの解消

## [1.4.0] - 2025-07-24

### Security
- 🚨 **緊急セキュリティ修正** (Hotfix Phase 1)
- CSRFトークンの有効期限チェック実装
- `generate_with_seed`関数の本番環境での無効化
- GETリクエストでの状態変更操作の修正

### Added
- Celeryタスクのリトライ機構
  - 指数バックオフとジッター機能
  - エラー分類とリトライ戦略
  - 詳細なログ記録とメトリクス

### Improved
- トランザクション管理の統一化
- N+1問題の解消
- SSEハートビートロジックの修正
- パフォーマンス最適化

### Dependencies
- langchain: 0.0.27 → 0.3.26 (セキュリティ脆弱性修正)
- langchain-core: → 0.3.69
- langchain-community: → 0.3.27
- langchain-google-genai: → 2.1.8

## [1.3.0] - 2025-07-22

### Added
- CSRF保護システム
- ユーザー成長記録システム
- 包括的なセキュリティ機能

### Improved
- ユーザー認証システムの強化
- セッション管理の改善

## [1.2.0] - 2025-07-19

### Added
- 音響機能のエラーハンドリング改善
- シナリオコンテンツの包括的品質改善
- 自己肯定感向上フォーカスのシナリオ再設計

### Improved
- 要件定義書に基づくシナリオ内容の改善

## [1.1.0] - 2025-07-18

### Added
- 包括的なセキュリティ機能とユーザー認証システム
- PostgreSQLデータベース統合

### Security
- セキュアな認証システムの実装
- データベースレベルでのセキュリティ強化

## [1.0.0] - 2025-07-17

### Added
- 初回リリース
- AIを活用した職場コミュニケーション練習機能
- シナリオベースのロールプレイ機能
- 雑談練習モード
- 会話観戦モード
- Google Gemini API統合
- 基本的なユーザーインターフェース

---

## リリース計画

### Phase 2: メンテナンスリリース (v1.5.0) - 計画中
- [ ] 現在のOPEN PRの統合 (#10, #11)
- [ ] 統合テストの実施
- [ ] ドキュメント更新
- [ ] リリースノート作成

### Phase 3: 継続的改善計画
- [ ] パフォーマンス監視システムの強化
- [ ] ユーザー体験の改善
- [ ] 新機能の計画的導入