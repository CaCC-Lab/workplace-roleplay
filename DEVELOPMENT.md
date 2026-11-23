# 🔧 開発者ガイド

このドキュメントは、workplace-roleplayプロジェクトの開発に関する詳細な情報を提供します。

## 📋 目次

- [開発環境セットアップ](#開発環境セットアップ)
- [プロジェクト構造](#プロジェクト構造)
- [テスト戦略](#テスト戦略)
- [コード品質管理](#コード品質管理)
- [セキュリティ対策](#セキュリティ対策)
- [デバッグと問題解決](#デバッグと問題解決)

## 🚀 開発環境セットアップ

### 前提条件

- Python 3.10以上
- Git
- VSCode（推奨）
- Google Cloud API キー（Gemini API用）

### クイックスタート

```bash
# 1. リポジトリクローン
git clone https://github.com/CaCC-Lab/workplace-roleplay.git
cd workplace-roleplay

# 2. 自動セットアップ実行
chmod +x setup_dev_env.sh
./setup_dev_env.sh

# 3. 環境変数設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定

# 4. 環境確認
source venv/bin/activate
python verify_environment.py

# 5. アプリケーション起動
python app.py
```

### IDEセットアップ（VSCode）

プロジェクトには`.vscode/settings.json`が含まれており、以下の機能が自動設定されます：

- Python仮想環境の自動認識
- Pylanceによる型チェック
- 自動フォーマット（Black）
- リンター（Flake8、MyPy）
- テスト発見（pytest）

### 開発依存関係

```
# requirements-dev.txt
pytest>=8.1.1      # テストフレームワーク
black>=24.2.0       # コードフォーマッター
flake8>=7.0.0       # リンター
isort>=5.13.2       # インポート整理
mypy>=1.9.0         # 型チェッカー
pytest-flask>=1.3.0 # Flaskテスト拡張
pytest-cov>=4.0.0   # カバレッジ計測
```

## 🏗️ プロジェクト構造

```
workplace-roleplay/
├── 📱 app.py                    # メインアプリケーション
├── 🧠 strength_analyzer.py      # 強み分析エンジン
├── 🔑 api_key_manager.py        # APIキー管理
├── ⚙️ config.py                # 設定管理
├── 🛡️ errors.py                # エラーハンドリング
├── 📚 scenarios/                # シナリオ管理
│   ├── __init__.py
│   └── data/                    # YAMLシナリオファイル
├── 🔧 utils/                    # ユーティリティ
│   ├── security.py              # セキュリティ機能
│   ├── csp_middleware.py        # CSPミドルウェア
│   └── ...
├── 🧪 tests/                    # テストスイート
│   ├── security/                # セキュリティテスト
│   ├── helpers/                 # テストヘルパー
│   └── ...
├── 🎨 static/                   # フロントエンド
│   ├── js/                      # JavaScript
│   └── css/                     # スタイルシート
├── 🌐 templates/                # HTMLテンプレート
├── 🐳 scripts/                  # 開発スクリプト
├── 📄 .vscode/                  # VSCode設定
└── 📋 docs/                     # ドキュメント
```

### 主要モジュール

#### app.py - メインアプリケーション
- Flaskアプリケーションの初期化
- ルーティング定義
- LLM（Gemini）との統合
- セッション管理

#### strength_analyzer.py - 強み分析システム
- ユーザーのコミュニケーションスキル分析
- AIによるフィードバック生成
- データビジュアライゼーション

#### api_key_manager.py - APIキー管理
- 複数APIキーのローテーション
- レート制限対策
- エラー時の自動切り替え

#### utils/security.py - セキュリティ機能
- CSRF対策
- XSS防御
- 入力サニタイズ
- セッションセキュリティ

## 🧪 テスト戦略

### テスト構成

プロジェクトは**189個のテスト**で包括的にカバーされています：

```
tests/
├── security/                   # セキュリティテスト (83テスト)
│   ├── test_csrf.py            # CSRF対策 (23テスト)
│   ├── test_secret_key.py      # キー管理 (8テスト)
│   └── test_xss.py             # XSS対策 (12テスト)
├── test_api_key_manager.py     # APIキー管理 (16テスト)
├── test_app_integration.py     # 統合テスト (17テスト)
├── test_strength_analyzer.py   # 強み分析 (18テスト)
├── test_config.py              # 設定管理 (15テスト)
├── test_errors.py              # エラー処理 (15テスト)
├── test_csp_middleware.py      # CSP対策 (15テスト)
└── ...
```

### テスト実行

```bash
# 全テスト実行
pytest

# 詳細出力
pytest -v

# カバレッジ付き
pytest --cov=.

# 特定のテストのみ
pytest tests/security/
pytest tests/test_api_key_manager.py
pytest -k "test_csrf"

# 失敗時に停止
pytest -x

# 並列実行
pytest -n auto
```

### テスト作成ガイドライン

#### 1. TDD（テスト駆動開発）の実践

```python
# 1. RED: 失敗するテストを書く
def test_new_feature():
    with pytest.raises(NotImplementedError):
        new_feature()

# 2. GREEN: 最小限の実装
def new_feature():
    raise NotImplementedError()

# 3. REFACTOR: 改善・最適化
def new_feature():
    # 実際の実装
    return "result"
```

#### 2. テストの命名規則

```python
# ✅ 良い例：動作と期待値が明確
def test_api_key_manager_は_使用回数が最少のキーを返す():
    pass

def test_csrf_token_は_有効期限切れの場合例外を発生させる():
    pass

# ❌ 悪い例：何をテストするか不明
def test_manager():
    pass

def test_error():
    pass
```

#### 3. テストの構造

```python
def test_feature_description():
    # Arrange: テストデータの準備
    api_manager = APIKeyManager(['key1', 'key2'])
    
    # Act: テスト対象の実行
    result = api_manager.get_next_key()
    
    # Assert: 結果の検証
    assert result in ['key1', 'key2']
    assert api_manager.get_usage_count(result) == 1
```

### CSRFテストヘルパー

CSRF保護されたエンドポイントのテスト用ヘルパーが提供されています：

```python
from tests.helpers.csrf_helpers import CSRFTestClient

def test_protected_endpoint(client):
    csrf_client = CSRFTestClient(client)
    
    # CSRFトークンが自動で処理される
    response = csrf_client.post('/api/protected', 
                               json={'data': 'test'})
    assert response.status_code == 200
```

## 📏 コード品質管理

### 自動フォーマットとリンター

```bash
# コードフォーマット
black .                 # 自動フォーマット
black --check .         # フォーマット確認のみ

# リンティング
flake8                  # コード品質チェック
isort .                 # インポート順序整理
mypy .                  # 型チェック
```

### VSCode統合

設定済みの`.vscode/settings.json`により以下が自動実行されます：

- 保存時の自動フォーマット（Black）
- リアルタイムリンティング（Flake8）
- 型チェック（MyPy）
- インポート整理（isort）

### コーディング規約

#### Python

```python
# ✅ 型ヒントを使用
def process_data(data: Dict[str, Any]) -> List[str]:
    return [str(item) for item in data.values()]

# ✅ docstringを記述
def analyze_conversation(messages: List[dict]) -> dict:
    """
    会話データを分析して強みスコアを算出
    
    Args:
        messages: 会話メッセージのリスト
        
    Returns:
        スコア辞書 (共感力、傾聴力等)
    """
    pass

# ✅ 定数は大文字
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
```

#### JavaScript

```javascript
// ✅ 明確な変数名
const audioCache = new Map();
const maxCacheSize = 50;

// ✅ JSDoc形式のコメント
/**
 * 音声データをキャッシュから取得
 * @param {string} key キャッシュキー
 * @returns {Promise<AudioBuffer>} 音声データ
 */
async function getAudioFromCache(key) {
    return audioCache.get(key);
}
```

## 🛡️ セキュリティ対策

### 実装済みセキュリティ機能

#### 1. CSRF（Cross-Site Request Forgery）対策

```python
from utils.security import require_csrf

@app.route('/api/protected', methods=['POST'])
@require_csrf
def protected_endpoint():
    return jsonify({'status': 'success'})
```

#### 2. XSS（Cross-Site Scripting）対策

```python
from utils.security import SecurityUtils

# 入力のサニタイズ
clean_input = SecurityUtils.sanitize_input(user_input)

# 出力のエスケープ
safe_output = SecurityUtils.escape_html(content)
```

#### 3. CSP（Content Security Policy）

```python
from utils.csp_middleware import CSPMiddleware, csp_exempt

# 自動CSP適用
app = Flask(__name__)
csp = CSPMiddleware(app)

# 特定エンドポイントの除外
@app.route('/api/special')
@csp_exempt
def special_endpoint():
    return "CSP除外"
```

### セキュリティテスト

全セキュリティ機能は包括的にテストされています：

```bash
# セキュリティテストのみ実行
pytest tests/security/ -v

# 結果例：
# tests/security/test_csrf.py::TestCSRFToken::test_generate_token_format PASSED
# tests/security/test_csrf.py::TestCSRFSecurity::test_timing_attack_resistance PASSED
# tests/security/test_xss.py::TestXSSPrevention::test_基本的なスクリプトタグの無害化 PASSED
```

## 🐛 デバッグと問題解決

### 環境確認

問題が発生した場合、まず環境確認スクリプトを実行：

```bash
source venv/bin/activate
python verify_environment.py
```

出力例：
```
🚀 開発環境の動作確認を開始...
✅ 仮想環境を使用: /path/to/venv/bin/python
✅ flask: 3.1.1
✅ pytest: 8.4.1
🎉 すべての確認が成功しました！
```

### よくある問題と解決方法

#### 1. Pylanceインポートエラー

**症状**: `"インポート "flask" を解決できませんでした"`

**解決策**:
```bash
# VSCodeでPythonインタープリターを設定
# Ctrl+Shift+P → "Python: Select Interpreter"
# ./venv/bin/python を選択
```

#### 2. テスト失敗

**症状**: CSRF関連のテストが失敗

**解決策**:
```python
# CSRFTestClientを使用
from tests.helpers.csrf_helpers import CSRFTestClient

def test_api_endpoint(client):
    csrf_client = CSRFTestClient(client)
    response = csrf_client.post('/api/endpoint', json={})
```

#### 3. 音声生成エラー

**症状**: Gemini TTS APIエラー

**解決策**:
```bash
# 環境変数確認
echo $GOOGLE_API_KEY

# APIキーの有効性確認
python -c "
import google.generativeai as genai
genai.configure(api_key='your_key')
print('API key valid')
"
```

#### 4. セッションエラー

**症状**: セッションデータが保存されない

**解決策**:
```python
# Flask設定確認
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
```

### ログとデバッグ

#### デバッグモード

```bash
# 開発時のデバッグモード
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

#### ログレベル設定

```python
import logging

# デバッグレベルのログ
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 開発ワークフロー

### 新機能開発

1. **要件分析**: TODO.mdで要件を明確化
2. **TDDアプローチ**: 失敗するテストから開始
3. **実装**: 最小限の実装でテストを通す
4. **リファクタリング**: コード品質を向上
5. **統合テスト**: 他機能との連携を確認

### コミット前チェックリスト

```bash
# 1. コード品質チェック
black --check .
flake8
isort --check-only .
mypy .

# 2. テスト実行
pytest

# 3. 環境確認
python verify_environment.py

# 4. セキュリティテスト
pytest tests/security/

# ✅ すべて成功したらコミット
git add .
git commit -m "feature: 新機能の実装"
```

## 📚 関連ドキュメント

- [README.md](README.md) - プロジェクト概要
- [TODO.md](TODO.md) - 実装計画
- [CLAUDE.md](CLAUDE.md) - AI開発ガイド
- [技術仕様書](docs/) - 詳細技術文書

---

このガイドは定期的に更新されます。質問や提案がありましたら、Issueまたはプルリクエストでお知らせください。