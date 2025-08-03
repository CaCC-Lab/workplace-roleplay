# Workplace Roleplay システム設計書 v3.0 - 軽量リファクタリング版

## 1. 概要

### 1.1 設計方針
本設計は、既存システムの**パフォーマンスとセキュリティを維持**しながら、コードの保守性と拡張性を向上させる軽量リファクタリングを提案します。

**基本原則**:
- ✅ データベースなし（パフォーマンス維持）
- ✅ ユーザー認証なし（個人情報を扱わない）
- ✅ 既存機能の完全保持（デグレード防止）
- ✅ 段階的移行（リスク最小化）

### 1.2 現状の課題と解決方針

**課題**:
- `app.py`（2447行）のモノリシック構造
- テストが困難
- 機能追加時の影響範囲が不明確

**解決方針**:
- サービス層による責務分離
- 既存の動作を完全に保持
- 段階的で安全な移行

## 2. システムアーキテクチャ

### 2.1 全体構成

```
現在の構成（変更なし）:
┌─────────────────┐
│   ブラウザ      │
└────────┬────────┘
         │
┌────────┴────────┐
│   Flask App     │
├─────────────────┤
│ Flask-Session   │ ← セッションベース（維持）
├─────────────────┤
│     Redis       │ ← キャッシュ（維持）
├─────────────────┤
│   Gemini API    │ ← LLM連携（維持）
└─────────────────┘

リファクタリング後の内部構造:
┌─────────────────────────────────┐
│         Flask App (main.py)      │
├─────────────────────────────────┤
│          Service Layer          │
│  ┌─────────┬─────────┬────────┐│
│  │ChatSvc  │ScenSvc  │WatchSvc││
│  └─────────┴─────────┴────────┘│
├─────────────────────────────────┤
│       Utility Functions         │
└─────────────────────────────────┘
```

### 2.2 ディレクトリ構造

```
workplace-roleplay/
├── app.py                    # 現状維持（段階的に機能を移行）
├── app_original_backup.py    # バックアップ（既に存在）
├── main.py                   # 新しいエントリーポイント（最終形）
│
├── services/                 # サービス層（新規）
│   ├── __init__.py
│   ├── chat_service.py      # チャット機能
│   ├── scenario_service.py  # シナリオ管理
│   ├── watch_service.py     # 観戦モード
│   ├── llm_service.py       # LLM連携
│   ├── session_service.py   # セッション管理
│   └── tts_service.py       # 音声合成
│
├── utils/                    # ユーティリティ（新規）
│   ├── __init__.py
│   ├── validators.py        # 入力検証
│   ├── formatters.py        # データ整形
│   └── constants.py         # 定数定義
│
├── tests/                    # 既存のテスト
├── scenarios/                # 既存のシナリオ
├── static/                   # 既存の静的ファイル
└── templates/                # 既存のテンプレート
```

## 3. サービス層設計

### 3.1 ChatService

```python
from flask import session
from typing import Dict, Any, AsyncGenerator
import json

class ChatService:
    """チャット機能を管理するサービス"""
    
    def __init__(self, llm_service, session_service):
        self.llm_service = llm_service
        self.session_service = session_service
    
    def initialize_chat_session(self) -> Dict[str, Any]:
        """チャットセッションの初期化（app.pyの既存ロジックを移植）"""
        if 'chat_history' not in session:
            session['chat_history'] = []
            session['chat_model'] = 'gemini-1.5-flash'
        
        return {
            'status': 'initialized',
            'model': session.get('chat_model'),
            'history_length': len(session.get('chat_history', []))
        }
    
    async def process_message(self, message: str) -> AsyncGenerator[str, None]:
        """メッセージ処理（ストリーミング対応）"""
        # 既存のapp.pyからロジックを移植
        chat_history = session.get('chat_history', [])
        
        # LLMにストリーミングで問い合わせ
        async for chunk in self.llm_service.stream_chat_response(
            message=message,
            history=chat_history,
            model=session.get('chat_model')
        ):
            yield chunk
        
        # 履歴を更新（既存の動作を維持）
        self._update_chat_history(message, accumulated_response)
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """チャット履歴の取得"""
        return session.get('chat_history', [])
    
    def clear_chat_history(self) -> Dict[str, Any]:
        """チャット履歴のクリア"""
        session['chat_history'] = []
        return {'status': 'cleared'}
```

### 3.2 LLMService

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import AsyncGenerator, List, Dict, Any
import os

class LLMService:
    """LLM連携を管理するサービス"""
    
    def __init__(self):
        self.models = {
            'gemini-1.5-flash': self._create_gemini_model('gemini-1.5-flash'),
            'gemini-1.5-pro': self._create_gemini_model('gemini-1.5-pro')
        }
        self.api_key_manager = APIKeyManager()  # 既存のキー管理
    
    def _create_gemini_model(self, model_name: str):
        """Geminiモデルの作成（既存のcreate_gemini_llm関数を移植）"""
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            google_api_key=self.api_key_manager.get_google_api_key(),
            streaming=True
        )
    
    async def stream_chat_response(
        self, 
        message: str, 
        history: List[Dict], 
        model: str
    ) -> AsyncGenerator[str, None]:
        """チャットレスポンスのストリーミング"""
        # 既存のストリーミングロジックを移植
        llm = self.models.get(model)
        
        # メッセージ履歴を構築
        messages = self._build_messages(history, message)
        
        # ストリーミングレスポンス
        async for chunk in llm.astream(messages):
            yield chunk.content
```

### 3.3 移行時の安全装置

```python
# app.py での段階的移行例

from services.chat_service import ChatService

# フィーチャーフラグ
USE_NEW_CHAT_SERVICE = False  # 本番環境では最初はFalse

# サービスの初期化
if USE_NEW_CHAT_SERVICE:
    chat_service = ChatService(llm_service, session_service)

@app.route('/api/chat', methods=['POST'])
async def chat():
    """チャットエンドポイント"""
    if USE_NEW_CHAT_SERVICE:
        # 新しいサービスを使用
        try:
            return await chat_service.process_message(request.json['message'])
        except Exception as e:
            # エラー時は旧実装にフォールバック
            app.logger.error(f"New service error: {e}")
            return legacy_chat_implementation()
    else:
        # 既存の実装を使用
        return legacy_chat_implementation()

def legacy_chat_implementation():
    """既存のチャット実装（app.pyの現在のコード）"""
    # 現在のapp.pyのコードをそのまま維持
    pass
```

## 4. マイグレーション計画

### 4.1 フェーズ1: 準備とテスト作成（3日）

**Day 1-2: 現状分析とテスト作成**
```bash
# 1. 現在の動作を記録
python create_baseline_tests.py

# 2. E2Eテストの作成
python -m pytest tests/e2e/test_current_behavior.py

# 3. APIレスポンスの記録
python record_api_responses.py
```

**Day 3: 環境準備**
```bash
# 1. ディレクトリ作成
mkdir -p services utils

# 2. 依存関係の確認
pip freeze > requirements_baseline.txt

# 3. バックアップの確認
cp app.py app_before_refactoring.py
```

### 4.2 フェーズ2: サービス層作成（1週間）

**優先順位（リスクが低い順）**:

1. **ユーティリティ関数の移行**（Day 1）
   - `get_voice_for_emotion()`
   - `escape_for_json()`
   - バリデーション関数

2. **LLMService**（Day 2-3）
   - API キー管理
   - モデル初期化
   - 既存のLLM関連関数

3. **SessionService**（Day 4）
   - セッション管理
   - メモリ管理

4. **ChatService**（Day 5-6）
   - チャット機能
   - 履歴管理

5. **ScenarioService**（Day 7）
   - シナリオ管理
   - フィードバック

### 4.3 フェーズ3: 段階的統合（1週間）

**統合プロセス**:

```python
# Step 1: サービスをインポート（app.pyは変更なし）
from services.chat_service import ChatService

# Step 2: A/Bテスト形式で導入
@app.route('/api/chat/v2', methods=['POST'])  # 新しいエンドポイント
async def chat_v2():
    return await chat_service.process_message(request.json)

# Step 3: 動作確認後、フィーチャーフラグで切り替え
USE_NEW_SERVICE = os.getenv('USE_NEW_SERVICE', 'false').lower() == 'true'

# Step 4: 問題なければ旧コードを削除
```

### 4.4 フェーズ4: クリーンアップ（3日）

1. **不要コードの削除**
2. **ドキュメント更新**
3. **パフォーマンステスト**
4. **最終確認**

## 5. テスト戦略

### 5.1 リグレッションテスト

```python
# tests/test_regression.py
class RegressionTest:
    """既存の動作を保証するテスト"""
    
    def setup_method(self):
        # 本番と同じ環境を構築
        self.app = create_app()
        self.client = self.app.test_client()
    
    def test_chat_response_format(self):
        """チャットレスポンスの形式が変わっていないことを確認"""
        response = self.client.post('/api/chat', json={
            'message': 'こんにちは'
        })
        
        # 既存のレスポンス形式を確認
        assert response.status_code == 200
        assert 'data:' in response.data.decode()  # SSE形式
    
    def test_session_persistence(self):
        """セッションが正しく保持されることを確認"""
        # 既存の動作を完全に再現
        pass
```

### 5.2 並行テスト

```python
# tests/test_parallel_comparison.py
def test_old_vs_new_service():
    """新旧サービスの出力が同一であることを確認"""
    
    # 同じ入力
    test_message = "テストメッセージ"
    
    # 旧実装の結果
    old_result = legacy_chat_implementation(test_message)
    
    # 新実装の結果
    new_result = chat_service.process_message(test_message)
    
    # 結果が同一であることを確認
    assert old_result == new_result
```

## 6. リスク管理

### 6.1 リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| セッション管理の不整合 | 高 | 既存のFlask-Session設定を完全に維持 |
| ストリーミングの動作変更 | 高 | SSE実装を1行も変更しない |
| メモリリーク | 中 | 既存のメモリ管理ロジックを維持 |
| パフォーマンス劣化 | 中 | 各段階でベンチマーク実施 |

### 6.2 ロールバック計画

```bash
# 即座にロールバック可能
git checkout app_original_backup.py
mv app_original_backup.py app.py
systemctl restart workplace-roleplay

# フィーチャーフラグでの切り替え
export USE_NEW_SERVICE=false
```

## 7. 成功基準

### 7.1 機能面
- ✅ すべての既存APIが同じレスポンスを返す
- ✅ セッション管理が従来通り動作
- ✅ ストリーミングが途切れない
- ✅ エラー率が増加しない

### 7.2 パフォーマンス面
- ✅ レスポンスタイムが劣化しない（±10%以内）
- ✅ メモリ使用量が増加しない
- ✅ CPU使用率が増加しない

### 7.3 保守性
- ✅ コードの行数が関数あたり100行以下
- ✅ テストカバレッジ80%以上
- ✅ 循環的複雑度10以下

## 8. まとめ

この設計により：

1. **リスクを最小化**: 段階的移行でいつでもロールバック可能
2. **パフォーマンス維持**: データベースなし、既存の高速動作を保持
3. **セキュリティ維持**: 個人情報を扱わない現在のモデルを継続
4. **保守性向上**: サービス層により責務が明確化
5. **テスト容易性**: 各サービスを独立してテスト可能

既存の機能を1つも壊すことなく、コードの品質を向上させることができます。