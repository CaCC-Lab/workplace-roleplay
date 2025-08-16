# 🚀 Workplace Roleplay - Azure VM デプロイメントガイド

## 📋 概要

このドキュメントでは、GitHub ActionsとAzure VMを使用した自動デプロイメントのセットアップと管理方法を説明します。

## 🏗️ アーキテクチャ

```
GitHub Repository → GitHub Actions → Azure VM (Ubuntu 22.04)
                         ↓
                    SSH Deployment
                         ↓
                 Nginx → Flask App (Systemd)
```

## 🔧 初期セットアップ

### 1. Azure VM準備

VMにSSH接続して初期セットアップスクリプトを実行：

```bash
# リポジトリをクローン
git clone https://github.com/CaCC-Lab/workplace-roleplay.git
cd workplace-roleplay

# セットアップスクリプトを実行
chmod +x deployment/setup-vm.sh
./deployment/setup-vm.sh
```

### 2. 環境変数設定

`/home/ryu/.env.production`を編集して必要な環境変数を設定：

```bash
nano /home/ryu/.env.production
```

必須項目：
- `FLASK_SECRET_KEY`: セッション暗号化用のシークレットキー
- `GOOGLE_API_KEY`: Google Gemini APIキー

### 3. GitHub Secrets設定

GitHubリポジトリの Settings → Secrets and variables → Actions で以下を設定：

| Secret名 | 説明 | 取得方法 |
|----------|------|----------|
| `AZURE_VM_SSH_KEY` | VM接続用のSSH秘密鍵 | `cat ~/.ssh/id_rsa` (ローカル) |

### 4. SSL証明書設定

Let's Encryptを使用してSSL証明書を自動取得：

```bash
sudo certbot --nginx -d workplace-roleplay.cacc-lab.net \
  --non-interactive --agree-tos --email admin@cacc-lab.net
```

## 🚀 デプロイメント

### 自動デプロイ

mainブランチへのpushで自動的にデプロイが実行されます：

```bash
git push origin main
```

### 手動デプロイ

GitHub Actions画面から手動実行も可能：
1. Actions タブを開く
2. "Deploy to Azure VM Production" ワークフローを選択
3. "Run workflow" をクリック

## 📊 モニタリング

### アプリケーションログ

```bash
# リアルタイムログ表示
sudo journalctl -u workplace-roleplay -f

# 過去のログ確認
sudo journalctl -u workplace-roleplay --since "1 hour ago"
```

### Nginxログ

```bash
# アクセスログ
tail -f /var/log/nginx/workplace-roleplay.access.log

# エラーログ
tail -f /var/log/nginx/workplace-roleplay.error.log
```

### ヘルスチェック

```bash
# ローカルから
curl http://localhost:5000/health

# 外部から
curl https://workplace-roleplay.cacc-lab.net/health
```

## 🔧 トラブルシューティング

### サービスが起動しない

```bash
# サービスステータス確認
sudo systemctl status workplace-roleplay

# 設定ファイル確認
sudo systemctl cat workplace-roleplay

# サービス再起動
sudo systemctl restart workplace-roleplay
```

### Nginxエラー

```bash
# 設定テスト
sudo nginx -t

# Nginx再起動
sudo systemctl restart nginx
```

### デプロイメント失敗

1. GitHub Actions のログを確認
2. SSH接続を手動でテスト：
   ```bash
   ssh ryu@workplace-roleplay.cacc-lab.net
   ```
3. 権限確認：
   ```bash
   ls -la /home/ryu/workplace-roleplay
   ```

### ロールバック

自動バックアップから復元：

```bash
# バックアップ一覧確認
ls -la /home/ryu/workplace-roleplay.backup.*

# 最新のバックアップから復元
latest_backup=$(ls -t /home/ryu/workplace-roleplay.backup.* | head -1)
sudo rm -rf /home/ryu/workplace-roleplay
sudo mv $latest_backup /home/ryu/workplace-roleplay
sudo systemctl restart workplace-roleplay
```

## 🔒 セキュリティ

### ファイアウォール設定

```bash
# 現在のルール確認
sudo ufw status verbose

# ポート追加（必要な場合）
sudo ufw allow 8080/tcp
```

### SSH鍵の更新

```bash
# 新しい鍵ペア生成
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_vm_key

# 公開鍵をVMに追加
ssh-copy-id -i ~/.ssh/azure_vm_key.pub ryu@workplace-roleplay.cacc-lab.net

# GitHub Secretを更新
cat ~/.ssh/azure_vm_key  # この内容をGitHub Secretsに設定
```

## 📈 パフォーマンス最適化

### Nginx最適化

`/etc/nginx/sites-available/workplace-roleplay`を編集：

```nginx
# Worker接続数増加
events {
    worker_connections 2048;
}

# Gzip圧縮有効化
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

### Flask最適化

Production環境では Gunicorn の使用を推奨：

```bash
# Gunicornインストール
pip install gunicorn

# サービスファイル更新
ExecStart=/home/ryu/workplace-roleplay/venv/bin/gunicorn \
  -w 4 -b 127.0.0.1:5000 app:app
```

## 🔄 定期メンテナンス

### 週次タスク

- [ ] バックアップファイルの整理
- [ ] ログファイルのローテーション確認
- [ ] セキュリティアップデートの確認

### 月次タスク

- [ ] SSL証明書の有効期限確認
- [ ] システムリソース使用状況の確認
- [ ] 依存パッケージのアップデート

### コマンド例

```bash
# システムアップデート
sudo apt update && sudo apt upgrade

# SSL証明書更新（自動更新設定）
sudo certbot renew --dry-run

# ディスク使用量確認
df -h
du -sh /home/ryu/workplace-roleplay*
```

## 📞 サポート

問題が解決しない場合は、以下の情報と共に報告してください：

1. エラーメッセージ全文
2. 実行したコマンド
3. `sudo journalctl -u workplace-roleplay -n 100` の出力
4. GitHub Actions のログURL

---

**Last Updated**: 2024-12-27
**Version**: 1.0.0