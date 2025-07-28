# 徹底的リファクタリング計画

## 現状の問題点

### 1. アーキテクチャの問題
- **app.py が巨大** (2000行以上)
- **責任の分離不足**: ルーティング、ビジネスロジック、設定が混在
- **循環依存**: モジュール間の依存関係が複雑
- **グローバル変数の多用**: 状態管理が困難

### 2. コード品質の問題
- **14,497件のLint警告**
- **未使用インポート**: 633件
- **フォーマット不統一**: 199ファイル
- **重複コード**: 多数

### 3. セキュリティの問題
- **Werkzeug脆弱性**: バージョン3.0.4に既知の脆弱性
- **環境変数管理**: 不適切な設定管理
- **CSRF/XSS対策**: 不完全な実装

### 4. パフォーマンスの問題
- **同期的API呼び出し**: ブロッキング処理
- **キャッシュ不足**: 毎回同じデータを取得
- **N+1クエリ**: データベースアクセスの非効率

### 5. テストの問題
- **テスト実行不可**: インポートエラー
- **カバレッジ不明**: 測定されていない
- **E2Eテスト不足**: 主要機能のテスト欠如

## リファクタリング戦略

### Phase 1: 基盤整備（優先度: 最高）

#### 1.1 プロジェクト構造の再編成
```
workplace-roleplay/
├── src/                    # ソースコード
│   ├── __init__.py
│   ├── app.py             # Flask app factory
│   ├── config/            # 設定管理
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── api/               # APIエンドポイント
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── scenarios.py
│   │   └── models.py
│   ├── services/          # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── llm_service.py
│   │   ├── scenario_service.py
│   │   └── session_service.py
│   ├── models/            # データモデル
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── conversation.py
│   ├── utils/             # ユーティリティ
│   │   ├── __init__.py
│   │   ├── security.py
│   │   └── validators.py
│   └── static/            # 静的ファイル
│       └── templates/     # テンプレート
├── tests/                 # テスト
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/               # スクリプト
├── docs/                  # ドキュメント
└── requirements/          # 依存関係
    ├── base.txt
    ├── development.txt
    └── production.txt
```

#### 1.2 アプリケーションファクトリーパターン
```python
# src/app.py
def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 拡張機能の初期化
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Blueprintの登録
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
```

### Phase 2: コード品質改善（優先度: 高）

#### 2.1 自動フォーマット設定
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
extend-exclude = '''
/(
  flask_session
  | venv
  | node_modules
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,flask_session
```

#### 2.2 Pre-commitフック
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

### Phase 3: セキュリティ強化（優先度: 高）

#### 3.1 依存関係の更新
```txt
# requirements/base.txt
Flask==3.0.0
Flask-Login==0.6.3
Flask-Session==0.5.0
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.1  # 脆弱性修正版
python-dotenv==1.0.0
pydantic==2.5.3
```

#### 3.2 セキュリティミドルウェア
```python
# src/utils/security.py
class SecurityHeaders:
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.after_request(self.set_security_headers)
    
    def set_security_headers(self, response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response
```

### Phase 4: パフォーマンス最適化（優先度: 中）

#### 4.1 非同期処理
```python
# src/services/llm_service.py
import asyncio
from typing import Optional

class LLMService:
    def __init__(self):
        self._model_cache = {}
        self._cache_ttl = 3600
    
    async def get_models(self) -> list:
        """非同期でモデルリストを取得"""
        if self._is_cache_valid():
            return self._model_cache['models']
        
        try:
            models = await self._fetch_models_async()
            self._update_cache(models)
            return models
        except asyncio.TimeoutError:
            return self._get_default_models()
```

#### 4.2 キャッシング戦略
```python
# src/utils/cache.py
from functools import lru_cache, wraps
from datetime import datetime, timedelta

def timed_cache(seconds: int):
    def decorator(func):
        cache = {}
        cache_time = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = datetime.now()
            
            if key in cache and now - cache_time[key] < timedelta(seconds=seconds):
                return cache[key]
            
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = now
            return result
        
        return wrapper
    return decorator
```

### Phase 5: テスト基盤（優先度: 最高）

#### 5.1 テスト構造
```python
# tests/conftest.py
import pytest
from src.app import create_app
from src.models import db

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
```

#### 5.2 ユニットテスト例
```python
# tests/unit/test_llm_service.py
import pytest
from unittest.mock import Mock, patch
from src.services import LLMService

class TestLLMService:
    @pytest.fixture
    def llm_service(self):
        return LLMService()
    
    def test_get_models_with_cache(self, llm_service):
        # キャッシュがある場合のテスト
        llm_service._model_cache = {'models': ['test-model']}
        result = llm_service.get_models()
        assert result == ['test-model']
```

## 実装順序

1. **Week 1**: 基盤整備
   - プロジェクト構造の再編成
   - app.pyの分割
   - 設定管理の改善

2. **Week 2**: 品質改善
   - 自動フォーマットの適用
   - Lintエラーの修正
   - Pre-commitフックの設定

3. **Week 3**: セキュリティ
   - 依存関係の更新
   - セキュリティヘッダーの実装
   - 環境変数管理の改善

4. **Week 4**: パフォーマンス
   - 非同期処理の導入
   - キャッシングの実装
   - データベースクエリの最適化

5. **Week 5**: テスト
   - テスト基盤の構築
   - ユニットテストの作成
   - CI/CDパイプラインの設定

## 成功指標

- **コード品質**: Lintエラー 0件
- **テストカバレッジ**: 80%以上
- **パフォーマンス**: API応答時間 <500ms
- **セキュリティ**: 既知の脆弱性 0件
- **保守性**: 各モジュール <500行