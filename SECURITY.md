# セキュリティ

このドキュメントでは、本プロジェクトのセキュリティ対策と脆弱性報告の方法について説明します。

## 🛡️ 実装済みセキュリティ対策

### 1. XSS（Cross-Site Scripting）対策
- **入力サニタイズ**: `SecurityUtils.sanitize_input()`による危険なタグ・属性の除去
- **出力エスケープ**: `SecurityUtils.escape_html()`によるHTML特殊文字のエスケープ
- **エラーメッセージの安全化**: 機密情報の除去と適切なエスケープ
- **テストカバレッジ**: 9個のXSSテストケース

### 2. CSP（Content Security Policy）対策
- **段階的実装**: Report-Only → Mixed → Strict の3段階
- **Nonceベースのスクリプト制御**: インラインスクリプトの安全な許可
- **違反レポート収集**: CSP違反の自動検出と分析
- **テストカバレッジ**: 26個のCSPテストケース

### 3. CSRF（Cross-Site Request Forgery）対策
- **暗号学的に安全なトークン**: 32文字の16進数ランダムトークン
- **自動トークン管理**: フロントエンド統合（`csrf-manager.js`）
- **セッションCookie強化**: SameSite、HttpOnly、Secure属性
- **テストカバレッジ**: 40個のCSRFテストケース

### 4. シークレットキー管理
- **本番環境での厳格な検証**: デフォルトキー拒否、最小長32文字
- **複雑性要件**: 単純パターンの検出と拒否
- **開発環境での警告**: 不適切なキー使用時の警告表示
- **テストカバレッジ**: 8個のシークレットキーテストケース

### 5. セッション管理
- **Flask-Session**: ファイルシステムまたはRedisベースのセッション
- **セッションタイムアウト**: 適切なセッション期限設定
- **セッション隔離**: ユーザー間の適切なデータ隔離

## 🔒 セキュリティ設定

### 環境変数
```bash
# 必須: 本番環境では32文字以上の強力なシークレットキー
FLASK_SECRET_KEY=your_strong_secret_key_here

# 推奨: セッション設定
SESSION_TYPE=filesystem  # または redis
SESSION_PERMANENT=false
PERMANENT_SESSION_LIFETIME=1800  # 30分
```

### セキュリティヘッダー
本アプリケーションは以下のセキュリティヘッダーを自動的に設定します：

- `Content-Security-Policy`: インラインスクリプト攻撃の防御
- `X-Content-Type-Options: nosniff`: MIMEタイプ判定攻撃の防御
- `X-Frame-Options: DENY`: クリックジャッキング攻撃の防御
- `X-XSS-Protection: 1; mode=block`: ブラウザXSS保護の有効化

## 🧪 セキュリティテスト

### テスト実行
```bash
# セキュリティテストのみ実行
python -m pytest tests/security/ -v

# 全テスト実行
python -m pytest -v
```

### テスト構成
- **Total Security Tests**: 102個
- **Test Results**: 189テスト通過、7スキップ
- **Coverage**: XSS、CSP、CSRF、Secret Key管理

## 🚨 脆弱性報告

### 報告方法
セキュリティ脆弱性を発見した場合は、以下の方法でご報告ください：

1. **問い合わせフォーム**: https://cacc-lab.net/otoiawase/
2. **GitHub Issues**: 公開されても問題ない軽微な問題のみ

### 報告時に含めるべき情報
- 脆弱性の詳細な説明
- 再現手順
- 影響範囲の評価
- 修正案（もしあれば）

### 対応プロセス
1. **24時間以内**: 受信確認
2. **72時間以内**: 初期評価とトリアージ
3. **重要度に応じて**: 修正とパッチリリース
   - **Critical**: 24時間以内
   - **High**: 1週間以内
   - **Medium**: 1ヶ月以内
   - **Low**: 次回定期リリース

## 🔧 開発者向けセキュリティガイド

### 新機能追加時の注意点
1. **入力検証**: すべての外部入力を適切に検証・サニタイズ
2. **出力エスケープ**: HTMLレスポンスは必ずエスケープ
3. **CSRF保護**: state-changing操作には必ずCSRF保護を追加
4. **テスト追加**: セキュリティテストを必ず追加

### コードレビューのチェックポイント
- [ ] 入力検証が適切に実装されているか
- [ ] 出力エスケープが行われているか
- [ ] 機密情報がログに出力されていないか
- [ ] CSRF保護が必要な箇所に実装されているか
- [ ] セキュリティテストが追加されているか

## 📋 セキュリティ監査

### 定期監査
- **コード監査**: 月次
- **依存関係チェック**: 週次
- **ペネトレーションテスト**: 四半期ごと

### 監査ツール
```bash
# 依存関係の脆弱性チェック
pip-audit

# セキュリティリンター
bandit -r .

# パッケージの既知の脆弱性
safety check
```

## 🛠️ セキュリティ関連ツール

### 開発環境
```bash
# セキュアキー生成
python scripts/generate_secret_key.py

# セキュリティユーティリティ
python -c "from config.security_utils import SecurityUtils; print(SecurityUtils.generate_secure_key())"
```

### 本番環境
- **HTTPS**: SSL/TLS証明書の適切な設定
- **Firewall**: 必要最小限のポートのみ開放
- **Access Control**: 管理画面への適切なアクセス制御

## 📚 参考資料

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [CSP Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

最終更新日: 2025年6月29日

このセキュリティドキュメントは、プロジェクトのセキュリティ対策の実装と維持に関する重要な情報を提供しています。ご質問やご提案がございましたら、お気軽にお問い合わせください。