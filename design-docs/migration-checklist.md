# 🚀 FastAPI移行チェックリスト & 緊急対応プロシージャ

## 📋 段階別実装チェックリスト

### Phase 1: 基盤構築 (Week 1-4)

#### 🔧 技術基盤
- [ ] **Redis強化**
  - [ ] Redis Cluster構成検討
  - [ ] AIレスポンスキャッシュ実装 (`ai_cache:{hash}`)
  - [ ] TTSオーディオキャッシュ (`tts_cache:{text_hash}`)
  - [ ] セッション高速化 (`user_session:{user_id}`)
  - [ ] キャッシュ有効期限設定 (TTL管理)

- [ ] **API Gateway導入**
  - [ ] Nginx設定ファイル作成
  - [ ] ヘルスチェックエンドポイント (`/health`)
  - [ ] ロードバランサー設定
  - [ ] SSL証明書設定
  - [ ] レート制限設定

```nginx
# nginx.conf 例
upstream flask_backend {
    server 127.0.0.1:5000;
}

upstream fastapi_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    location /api/v1/ {
        proxy_pass http://flask_backend;
    }
    location /api/v2/ {
        proxy_pass http://fastapi_backend;
    }
}
```

- [ ] **JWT認証システム**
  - [ ] JWT署名キー設定 (HSA256/RS256選択)
  - [ ] トークン有効期限設定 (15分推奨)
  - [ ] リフレッシュトークン実装
  - [ ] Flask-Session並行運用設定

```python
# JWT設定例
JWT_CONFIG = {
    "SECRET_KEY": os.getenv("JWT_SECRET"),  # 必須
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 15,
    "REFRESH_TOKEN_EXPIRE_DAYS": 7
}
```

#### 🔒 セキュリティ設定
- [ ] **CSP (Content Security Policy)**
  - [ ] API Gateway層でのCSP一元管理
  - [ ] nonce値生成・検証
  - [ ] フロントエンドとの連携確認

- [ ] **CSRF対策継続**
  - [ ] Flask側CSRF継続
  - [ ] FastAPI側JWT認証確認
  - [ ] 移行期の二重チェック

- [ ] **データ暗号化 (ALE)**
  - [ ] sensitive dataの特定
  - [ ] 暗号化キー管理 (Google Secret Manager)
  - [ ] DB暗号化カラム設定

```python
# 暗号化実装例
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

#### 📊 監視基盤
- [ ] **OpenTelemetry導入**
  - [ ] FastAPI自動計装設定
  - [ ] カスタムメトリクス定義
  - [ ] トレース設定

- [ ] **Prometheus + Grafana**
  - [ ] メトリクス収集設定
  - [ ] アラートルール作成
  - [ ] ダッシュボード作成

```yaml
# prometheus.yml例
scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

### Phase 2: コア機能移行 (Week 5-8)

#### 🚀 FastAPI実装
- [ ] **チャットエンドポイント** (`/api/v2/chat`)
  - [ ] 非同期SSE実装
  - [ ] Gemini API統合 (Pro/Flash動的選択)
  - [ ] エラーハンドリング強化
  - [ ] パフォーマンステスト実行

```python
# 実装チェックポイント
@app.post("/api/v2/chat", response_class=StreamingResponse)
async def chat_stream(request: ChatRequest):
    # ✅ Pydantic validation
    # ✅ JWT authentication 
    # ✅ Rate limiting
    # ✅ Error handling
    # ✅ Streaming response
    # ✅ Background tasks
    pass
```

- [ ] **シナリオロールプレイ** (`/api/v2/scenario`)
  - [ ] 非同期処理実装
  - [ ] シナリオキャッシュ活用
  - [ ] リアルタイムフィードバック
  - [ ] 並行セッション対応

- [ ] **観戦モード** (`/api/v2/watch`)
  - [ ] AI間対話制御
  - [ ] ユーザー介入機能
  - [ ] WebSocket検討

#### 📊 データ移行
- [ ] **透過的セッション移行**
  - [ ] Flask session読み込みロジック
  - [ ] データ構造変換処理
  - [ ] エラーハンドリング・ログ
  - [ ] 移行状況監視

```python
# 移行テストコマンド
async def test_migration():
    # Flask セッション作成
    flask_session = create_test_flask_session()
    
    # 移行実行
    new_user_id = await migrate_flask_session(flask_session.id)
    
    # 検証
    assert new_user_id is not None
    new_session = await get_user_session(new_user_id)
    assert new_session.chat_history == expected_history
```

---

### Phase 3: UX向上 (Week 9-12)

#### 💫 HTMX統合
- [ ] **動的UI実装**
  - [ ] hx-post属性追加
  - [ ] hx-target指定
  - [ ] フォーム送信改善
  - [ ] エラー表示強化

```html
<!-- HTMX実装例 -->
<form hx-post="/api/v2/chat" 
      hx-target="#chat-response" 
      hx-indicator="#loading">
    <input name="message" required>
    <button type="submit">送信</button>
</form>
<div id="loading" class="htmx-indicator">送信中...</div>
<div id="chat-response"></div>
```

#### 🧠 AI機能強化
- [ ] **コンテキスト保持向上**
  - [ ] 長期記憶実装
  - [ ] 関連性スコア計算
  - [ ] 要約機能実装

- [ ] **感情分析フィードバック**
  - [ ] 感情スコア計算
  - [ ] リアルタイム表示
  - [ ] アドバイス生成

---

### Phase 4: スケール・最適化 (Week 13-16)

#### ☁️ GKE移行
- [ ] **Kubernetes設定**
  - [ ] Deployment YAML作成
  - [ ] Service設定
  - [ ] Ingress設定
  - [ ] ConfigMap/Secret管理

```yaml
# deployment.yaml例
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workplace-roleplay
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: fastapi
        image: gcr.io/project/workplace-roleplay:latest
        ports:
        - containerPort: 8000
        env:
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: secret
```

- [ ] **KEDA自動スケーリング**
  - [ ] ScaledObject設定
  - [ ] Redis Queue監視
  - [ ] CPU/Memory閾値設定

#### 📈 高度監視
- [ ] **ビジネスメトリクス**
  - [ ] ユーザー満足度追跡
  - [ ] 機能利用率測定
  - [ ] エラー率監視

---

## 🚨 緊急時対応プロシージャ

### レベル1: 軽微な問題 (5分以内対応)

#### パフォーマンス劣化
```bash
# 症状: レスポンス時間増加
# 1. メトリクス確認
curl http://localhost:8000/api/v2/metrics

# 2. Redis確認  
redis-cli ping
redis-cli info memory

# 3. ログ確認
kubectl logs deployment/workplace-roleplay --tail=100
```

**対応手順:**
1. Redis接続確認
2. キャッシュクリア
3. 不要セッション削除
4. アプリケーション再起動

### レベル2: 機能停止 (30秒以内対応)

#### 認証システム障害
```bash
# 症状: JWT認証失敗
# 緊急フォールバック (Flask-Session使用)
kubectl patch deployment workplace-roleplay -p '{"spec":{"template":{"spec":{"containers":[{"name":"fastapi","env":[{"name":"FALLBACK_AUTH","value":"flask_session"}]}]}}}}'
```

**対応手順:**
1. JWT署名検証無効化
2. Flask-Session認証有効化  
3. セッションストア確認
4. 認証ログ分析

#### AI API障害
```bash
# 症状: Gemini API 503/429エラー
# フォールバック: 複数APIキー切り替え
kubectl set env deployment/workplace-roleplay GOOGLE_API_KEY_FALLBACK=backup_key
```

**対応手順:**
1. APIキーローテーション
2. レートリミット確認
3. 簡易応答モード切り替え
4. ユーザー通知表示

### レベル3: サービス全停止 (即座対応)

#### 完全ロールバック (30秒)
```bash
# 全トラフィックをFlaskに戻す
kubectl patch ingress main-ingress -p '{
  "spec": {
    "rules": [{
      "http": {
        "paths": [{
          "path": "/",
          "backend": {
            "service": {
              "name": "flask-service"
            }
          }
        }]
      }
    }]
  }
}'

# 確認
curl -I http://your-domain.com/api/health
```

**緊急連絡先:**
- システム管理者: [連絡先]
- バックエンド責任者: [連絡先]
- インフラ担当: [連絡先]

---

## 📞 エスカレーション基準

### 自動エスカレーション
- エラー率 > 5% (5分継続)
- レスポンス時間 > 5秒 (P95, 3分継続)
- ヘルスチェック失敗 (1分継続)

### 手動エスカレーション判断
- セキュリティインシデント疑い
- データ消失の可能性  
- 予期しない大量アクセス

---

## ✅ 移行完了チェックリスト

### 技術的完了条件
- [ ] 全エンドポイントのFastAPI移行
- [ ] パフォーマンス目標達成 (レスポンス時間50%短縮)
- [ ] エラー率 < 0.1%を1週間継続
- [ ] ロードテスト合格 (同時接続数10倍)

### ビジネス完了条件
- [ ] ユーザー離脱率変化 < 2%
- [ ] 機能利用率 前月比維持
- [ ] サポート問い合わせ増加 < 10%

### 運用完了条件
- [ ] 監視・アラート設定完了
- [ ] ドキュメント整備完了
- [ ] チーム研修実施完了
- [ ] 緊急対応訓練実施完了

---

## 📊 移行後評価 (1ヶ月後)

### KPI評価
- パフォーマンス改善率: __%
- エラー率: __%  
- ユーザー満足度: __/10
- 開発速度向上: __%

### 学習事項
- 技術的課題:
- プロセス改善点:
- 次回移行への提言:

---

*🤖 Generated with 5AI Collaborative Process*  
*Co-Authored-By: Claude 4, Gemini 2.5, Qwen3-Coder, GPT-5, Cursor*

**最終更新**: 2024年12月 | **担当**: DevOps Team