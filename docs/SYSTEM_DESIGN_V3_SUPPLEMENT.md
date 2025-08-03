# Workplace Roleplay システム設計書 v3.0 - 補足資料

## 1. セッション管理の詳細

### 1.1 既存のFlask-Session設定の維持

```python
# 現在の設定を完全に保持
app.config['SESSION_TYPE'] = 'filesystem'  # または 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'workplace_roleplay:'
app.config['SESSION_FILE_DIR'] = './flask_session'

# Redisを使用する場合
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
```

### 1.2 セッションデータ構造

```python
# セッションに保存されるデータ（変更なし）
session_data = {
    'chat_history': [
        {'role': 'user', 'content': 'こんにちは'},
        {'role': 'assistant', 'content': 'こんにちは！'}
    ],
    'scenario_history': {...},
    'watch_history': {...},
    'current_scenario': 'scenario_id',
    'chat_model': 'gemini-1.5-flash',
    'selected_voice': 'kore',
    'preferences': {
        'auto_voice': True,
        'language': 'ja'
    }
}
```

### 1.3 SessionServiceの実装詳細

```python
from flask import session
from typing import Dict, Any, Optional
import json
from datetime import datetime

class SessionService:
    """セッション管理を担当するサービス"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.session_timeout = 3600  # 1時間
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """セッションデータの取得（既存の動作を維持）"""
        return session.get(key, default)
    
    def set_session_data(self, key: str, value: Any) -> None:
        """セッションデータの設定"""
        session[key] = value
        session.permanent = True  # セッションの有効期限を延長
    
    def clear_session_data(self, key: str = None) -> None:
        """セッションデータのクリア"""
        if key:
            session.pop(key, None)
        else:
            session.clear()
    
    def get_conversation_memory(self, conversation_type: str) -> list:
        """会話履歴の取得（既存のget_conversation_memory関数を移植）"""
        memory_key = f"{conversation_type}_history"
        return self.get_session_data(memory_key, [])
    
    def update_conversation_memory(
        self, 
        conversation_type: str, 
        messages: list,
        max_messages: int = 50
    ) -> None:
        """会話履歴の更新（メモリ制限付き）"""
        memory_key = f"{conversation_type}_history"
        
        # 最新のメッセージのみ保持（メモリ節約）
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        
        self.set_session_data(memory_key, messages)
    
    def export_session_data(self) -> Dict[str, Any]:
        """セッションデータのエクスポート（デバッグ用）"""
        return {
            'session_id': session.get('_id'),
            'data': dict(session),
            'timestamp': datetime.utcnow().isoformat()
        }
```

## 2. 安全なリファクタリング手法

### 2.1 Shadow Testing（影の並行テスト）

```python
# app.py での実装例
from services.chat_service import ChatService
import logging
import traceback

class ShadowTester:
    """新旧実装を並行実行して結果を比較"""
    
    def __init__(self):
        self.logger = logging.getLogger('shadow_test')
        self.comparison_results = []
    
    async def shadow_test_chat(self, message: str, session_data: dict):
        """チャット機能の影テスト"""
        try:
            # 1. 既存の実装を実行
            old_result = await legacy_chat_implementation(message, session_data)
            
            # 2. 新しい実装を実行（エラーが起きても本番には影響なし）
            try:
                new_result = await chat_service.process_message(message)
                
                # 3. 結果を比較
                self._compare_results(old_result, new_result, context={
                    'function': 'chat',
                    'message': message[:50] + '...',
                    'timestamp': datetime.utcnow()
                })
            except Exception as e:
                self.logger.error(f"Shadow test failed: {e}")
                self.logger.error(traceback.format_exc())
            
            # 4. 本番では旧実装の結果を返す
            return old_result
            
        except Exception as e:
            self.logger.error(f"Legacy implementation failed: {e}")
            raise
    
    def _compare_results(self, old_result, new_result, context):
        """結果の比較とレポート"""
        differences = []
        
        # レスポンス形式の比較
        if type(old_result) != type(new_result):
            differences.append({
                'type': 'type_mismatch',
                'old': type(old_result).__name__,
                'new': type(new_result).__name__
            })
        
        # 内容の比較（文字列の場合）
        if isinstance(old_result, str) and isinstance(new_result, str):
            if old_result != new_result:
                # 軽微な違い（空白など）は無視
                if old_result.strip() != new_result.strip():
                    differences.append({
                        'type': 'content_mismatch',
                        'sample': {
                            'old': old_result[:100],
                            'new': new_result[:100]
                        }
                    })
        
        # 結果を記録
        if differences:
            self.comparison_results.append({
                'context': context,
                'differences': differences
            })
            self.logger.warning(f"Differences found: {differences}")
        else:
            self.logger.info("Shadow test passed - results match")
```

### 2.2 段階的切り替え戦略

```python
# config.py
class MigrationConfig:
    """移行の進行状況を管理"""
    
    # フィーチャーフラグ（段階的に有効化）
    FEATURES = {
        'use_new_utils': True,        # Phase 1: ユーティリティ（完了）
        'use_new_llm': True,         # Phase 2: LLMサービス（完了）
        'use_new_session': False,    # Phase 3: セッション（テスト中）
        'use_new_chat': False,       # Phase 4: チャット（未着手）
        'use_new_scenario': False,   # Phase 5: シナリオ（未着手）
        'use_new_watch': False,      # Phase 6: 観戦（未着手）
    }
    
    # トラフィック比率（カナリアリリース）
    CANARY_PERCENTAGE = {
        'chat': 0,      # 0% → 10% → 50% → 100%
        'scenario': 0,
        'watch': 0
    }
    
    @staticmethod
    def should_use_new_service(feature: str, user_session_id: str = None) -> bool:
        """新サービスを使用するかどうかを決定"""
        if not MigrationConfig.FEATURES.get(f'use_new_{feature}', False):
            return False
        
        # カナリアリリースの場合
        if user_session_id and feature in MigrationConfig.CANARY_PERCENTAGE:
            percentage = MigrationConfig.CANARY_PERCENTAGE[feature]
            if percentage < 100:
                # セッションIDのハッシュ値で決定（同じユーザーは常に同じ結果）
                hash_value = int(hashlib.md5(user_session_id.encode()).hexdigest(), 16)
                return (hash_value % 100) < percentage
        
        return True
```

### 2.3 エラーハンドリングとフォールバック

```python
from functools import wraps
import time

def safe_migration(legacy_func):
    """安全な移行のためのデコレータ"""
    def decorator(new_func):
        @wraps(new_func)
        async def wrapper(*args, **kwargs):
            feature_name = new_func.__name__.replace('_v2', '')
            
            # 新サービスを使用するかチェック
            if not MigrationConfig.should_use_new_service(feature_name):
                return await legacy_func(*args, **kwargs)
            
            # 新サービスを試行
            start_time = time.time()
            try:
                result = await new_func(*args, **kwargs)
                
                # パフォーマンス計測
                elapsed = time.time() - start_time
                if elapsed > 1.0:  # 1秒以上かかった場合は警告
                    logging.warning(f"Slow response in {feature_name}: {elapsed:.2f}s")
                
                return result
                
            except Exception as e:
                # エラーログを記録
                logging.error(f"Error in new {feature_name}: {e}")
                logging.error(traceback.format_exc())
                
                # メトリクスを記録
                error_counter.inc(feature=feature_name)
                
                # レガシー実装にフォールバック
                logging.info(f"Falling back to legacy {feature_name}")
                return await legacy_func(*args, **kwargs)
        
        return wrapper
    return decorator

# 使用例
@app.route('/api/chat', methods=['POST'])
@safe_migration(legacy_chat_handler)
async def chat_handler_v2():
    """新しいチャットハンドラー"""
    return await chat_service.process_message(request.json)
```

## 3. テスト戦略の具体例

### 3.1 ゴールデンテスト（既存動作の記録）

```python
# tests/golden/record_golden_responses.py
import json
import asyncio
from datetime import datetime

class GoldenTestRecorder:
    """現在の動作を「正解」として記録"""
    
    def __init__(self, app):
        self.app = app
        self.client = app.test_client()
        self.test_cases = []
    
    async def record_all_endpoints(self):
        """全エンドポイントの動作を記録"""
        
        # 1. チャット機能
        await self.record_chat_scenarios()
        
        # 2. シナリオ機能
        await self.record_scenario_flows()
        
        # 3. 観戦モード
        await self.record_watch_mode()
        
        # 結果を保存
        self.save_golden_data()
    
    async def record_chat_scenarios(self):
        """チャット機能の様々なパターンを記録"""
        test_patterns = [
            {
                'name': 'simple_greeting',
                'messages': ['こんにちは'],
                'expected_session_keys': ['chat_history']
            },
            {
                'name': 'multi_turn_conversation',
                'messages': [
                    'こんにちは',
                    '今日の天気はどうですか？',
                    'ありがとう'
                ],
                'expected_session_keys': ['chat_history']
            },
            {
                'name': 'model_switching',
                'messages': ['テスト'],
                'model': 'gemini-1.5-pro',
                'expected_session_keys': ['chat_history', 'chat_model']
            }
        ]
        
        for pattern in test_patterns:
            result = await self.execute_chat_test(pattern)
            self.test_cases.append({
                'endpoint': '/api/chat',
                'pattern': pattern,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def save_golden_data(self):
        """ゴールデンデータを保存"""
        with open('tests/golden/golden_responses.json', 'w') as f:
            json.dump(self.test_cases, f, indent=2, ensure_ascii=False)
```

### 3.2 リグレッションテストの自動生成

```python
# tests/test_regression_auto.py
import json
import pytest
from deepdiff import DeepDiff

class TestRegression:
    """ゴールデンデータに基づく自動リグレッションテスト"""
    
    @classmethod
    def setup_class(cls):
        # ゴールデンデータを読み込み
        with open('tests/golden/golden_responses.json', 'r') as f:
            cls.golden_data = json.load(f)
    
    def test_all_golden_scenarios(self):
        """全ゴールデンシナリオをテスト"""
        for test_case in self.golden_data:
            self._verify_endpoint(test_case)
    
    def _verify_endpoint(self, test_case):
        """エンドポイントの動作を検証"""
        endpoint = test_case['endpoint']
        pattern = test_case['pattern']
        expected_result = test_case['result']
        
        # 現在の実装で実行
        actual_result = self._execute_test(endpoint, pattern)
        
        # 結果を比較（些細な違いは無視）
        diff = DeepDiff(
            expected_result, 
            actual_result,
            ignore_order=True,
            exclude_paths=[
                "root['timestamp']",
                "root['session_id']"
            ]
        )
        
        assert not diff, f"Regression detected in {pattern['name']}: {diff}"
```

### 3.3 パフォーマンステスト

```python
# tests/test_performance.py
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """パフォーマンスの劣化を検出"""
    
    def test_response_time_not_degraded(self):
        """レスポンスタイムが劣化していないことを確認"""
        
        # ベースライン（既存実装）
        baseline_times = self._measure_response_times(use_new_service=False)
        
        # 新実装
        new_times = self._measure_response_times(use_new_service=True)
        
        # 統計値を計算
        baseline_p95 = statistics.quantiles(baseline_times, n=20)[18]  # 95パーセンタイル
        new_p95 = statistics.quantiles(new_times, n=20)[18]
        
        # 10%以上の劣化は許容しない
        assert new_p95 <= baseline_p95 * 1.1, \
            f"Performance degraded: {baseline_p95:.3f}s -> {new_p95:.3f}s"
    
    def _measure_response_times(self, use_new_service: bool, iterations: int = 100):
        """レスポンスタイムを測定"""
        times = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for i in range(iterations):
                future = executor.submit(self._single_request, use_new_service)
                futures.append(future)
            
            for future in futures:
                times.append(future.result())
        
        return times
```

## 4. パフォーマンス計測方法

### 4.1 メトリクス収集

```python
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# メトリクス定義
request_count = Counter(
    'app_requests_total', 
    'Total requests',
    ['endpoint', 'method', 'status']
)

request_duration = Histogram(
    'app_request_duration_seconds',
    'Request duration',
    ['endpoint', 'service_version']  # old vs new
)

active_sessions = Gauge(
    'app_active_sessions',
    'Number of active sessions'
)

memory_usage = Gauge(
    'app_memory_usage_bytes',
    'Memory usage in bytes'
)

def track_performance(service_version='old'):
    """パフォーマンスを追跡するデコレータ"""
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await f(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                # メトリクスを記録
                duration = time.time() - start_time
                endpoint = request.endpoint or 'unknown'
                
                request_count.labels(
                    endpoint=endpoint,
                    method=request.method,
                    status=status
                ).inc()
                
                request_duration.labels(
                    endpoint=endpoint,
                    service_version=service_version
                ).observe(duration)
        
        return wrapper
    return decorator
```

### 4.2 A/Bテスト結果の可視化

```python
# monitoring/ab_test_dashboard.py
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class ABTestDashboard:
    """新旧サービスの比較ダッシュボード"""
    
    def __init__(self, metrics_db):
        self.metrics_db = metrics_db
    
    def generate_comparison_report(self, feature: str, time_range: timedelta):
        """比較レポートの生成"""
        end_time = datetime.utcnow()
        start_time = end_time - time_range
        
        # メトリクスを取得
        old_metrics = self._get_metrics(feature, 'old', start_time, end_time)
        new_metrics = self._get_metrics(feature, 'new', start_time, end_time)
        
        # レポート生成
        report = {
            'feature': feature,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'comparison': {
                'response_time': {
                    'old_p50': old_metrics['response_time_p50'],
                    'new_p50': new_metrics['response_time_p50'],
                    'improvement': self._calculate_improvement(
                        old_metrics['response_time_p50'],
                        new_metrics['response_time_p50']
                    )
                },
                'error_rate': {
                    'old': old_metrics['error_rate'],
                    'new': new_metrics['error_rate'],
                    'improvement': self._calculate_improvement(
                        old_metrics['error_rate'],
                        new_metrics['error_rate']
                    )
                },
                'memory_usage': {
                    'old': old_metrics['memory_usage'],
                    'new': new_metrics['memory_usage'],
                    'improvement': self._calculate_improvement(
                        old_metrics['memory_usage'],
                        new_metrics['memory_usage']
                    )
                }
            },
            'recommendation': self._generate_recommendation(old_metrics, new_metrics)
        }
        
        return report
    
    def _generate_recommendation(self, old_metrics, new_metrics):
        """移行の推奨事項を生成"""
        issues = []
        
        # レスポンスタイムチェック
        if new_metrics['response_time_p95'] > old_metrics['response_time_p95'] * 1.1:
            issues.append("レスポンスタイムが10%以上劣化")
        
        # エラー率チェック
        if new_metrics['error_rate'] > old_metrics['error_rate']:
            issues.append("エラー率が増加")
        
        # メモリ使用量チェック
        if new_metrics['memory_usage'] > old_metrics['memory_usage'] * 1.2:
            issues.append("メモリ使用量が20%以上増加")
        
        if not issues:
            return {
                'status': 'ready',
                'message': '新サービスへの移行を推奨します'
            }
        else:
            return {
                'status': 'not_ready',
                'message': '以下の問題を解決してください',
                'issues': issues
            }
```

## 5. 段階的移行の詳細手順

### 5.1 Day-by-Day 移行計画

```markdown
## Week 1: 準備とユーティリティ

### Day 1: 環境準備とベースライン確立
- [ ] ゴールデンテストの記録
- [ ] パフォーマンスベースラインの測定
- [ ] ディレクトリ構造の作成
- [ ] CI/CDパイプラインの設定

### Day 2-3: ユーティリティ関数の移行
- [ ] utils/validators.py の作成
- [ ] utils/formatters.py の作成
- [ ] utils/constants.py の作成
- [ ] ユニットテストの作成
- [ ] app.pyからのインポート切り替え

### Day 4-5: LLMServiceの実装
- [ ] services/llm_service.py の作成
- [ ] APIキー管理の移行
- [ ] モデル初期化の移行
- [ ] ストリーミング処理の移行
- [ ] 影テストの実装

## Week 2: コアサービスの実装

### Day 6-7: SessionServiceの実装
- [ ] services/session_service.py の作成
- [ ] セッション管理ロジックの移行
- [ ] メモリ管理の移行
- [ ] Redisとの連携確認

### Day 8-10: ChatServiceの実装
- [ ] services/chat_service.py の作成
- [ ] チャットロジックの移行
- [ ] ストリーミングレスポンスの実装
- [ ] 履歴管理の移行
- [ ] 包括的なテスト作成

## Week 3: 統合とテスト

### Day 11-12: 段階的統合
- [ ] フィーチャーフラグの実装
- [ ] カナリアリリースの設定
- [ ] 監視ダッシュボードの設定
- [ ] A/Bテストの開始

### Day 13-14: 最終確認とクリーンアップ
- [ ] パフォーマンステストの実施
- [ ] セキュリティ監査
- [ ] ドキュメントの更新
- [ ] 不要コードの削除
```

### 5.2 チェックリストテンプレート

```python
# migration_checklist.py
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class MigrationTask:
    """移行タスクの定義"""
    id: str
    description: str
    service: str
    status: str = 'pending'  # pending, in_progress, completed, blocked
    started_at: datetime = None
    completed_at: datetime = None
    notes: str = ''
    
    def start(self):
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()
    
    def complete(self, notes: str = ''):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.notes = notes
    
    def block(self, reason: str):
        self.status = 'blocked'
        self.notes = f"Blocked: {reason}"

class MigrationTracker:
    """移行の進捗を追跡"""
    
    def __init__(self):
        self.tasks = self._initialize_tasks()
    
    def _initialize_tasks(self) -> List[MigrationTask]:
        """全移行タスクを初期化"""
        return [
            # Phase 1: Utils
            MigrationTask('utils_1', 'Create validators.py', 'utils'),
            MigrationTask('utils_2', 'Create formatters.py', 'utils'),
            MigrationTask('utils_3', 'Create constants.py', 'utils'),
            MigrationTask('utils_4', 'Write unit tests for utils', 'utils'),
            MigrationTask('utils_5', 'Switch imports in app.py', 'utils'),
            
            # Phase 2: LLM Service
            MigrationTask('llm_1', 'Create llm_service.py', 'llm'),
            MigrationTask('llm_2', 'Migrate API key management', 'llm'),
            MigrationTask('llm_3', 'Implement streaming', 'llm'),
            MigrationTask('llm_4', 'Add shadow testing', 'llm'),
            MigrationTask('llm_5', 'Performance validation', 'llm'),
            
            # ... 他のタスク
        ]
    
    def get_status_report(self) -> Dict:
        """現在の状況レポートを生成"""
        total = len(self.tasks)
        completed = len([t for t in self.tasks if t.status == 'completed'])
        in_progress = len([t for t in self.tasks if t.status == 'in_progress'])
        blocked = len([t for t in self.tasks if t.status == 'blocked'])
        
        return {
            'total_tasks': total,
            'completed': completed,
            'in_progress': in_progress,
            'blocked': blocked,
            'pending': total - completed - in_progress - blocked,
            'progress_percentage': (completed / total) * 100,
            'blocked_tasks': [t for t in self.tasks if t.status == 'blocked'],
            'current_phase': self._get_current_phase()
        }
    
    def _get_current_phase(self) -> str:
        """現在のフェーズを判定"""
        for task in self.tasks:
            if task.status in ['in_progress', 'pending']:
                return task.service
        return 'completed'
```

## 6. ロールバック手順

### 6.1 即時ロールバック

```bash
#!/bin/bash
# rollback.sh - 緊急ロールバックスクリプト

echo "Starting emergency rollback..."

# 1. フィーチャーフラグを全てFalseに
export USE_NEW_UTILS=false
export USE_NEW_LLM=false
export USE_NEW_SESSION=false
export USE_NEW_CHAT=false
export USE_NEW_SCENARIO=false
export USE_NEW_WATCH=false

# 2. アプリケーションを再起動
sudo systemctl restart workplace-roleplay

# 3. ヘルスチェック
sleep 5
curl -f http://localhost:5001/health || {
    echo "Health check failed! Restoring backup..."
    cp app_original_backup.py app.py
    sudo systemctl restart workplace-roleplay
}

echo "Rollback completed"
```

### 6.2 部分的ロールバック

```python
# partial_rollback.py
import os
import json

class PartialRollback:
    """特定のサービスのみロールバック"""
    
    def rollback_service(self, service_name: str):
        """特定のサービスをロールバック"""
        
        # 1. フィーチャーフラグを更新
        config_file = 'migration_config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        config['features'][f'use_new_{service_name}'] = False
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # 2. 環境変数も更新
        os.environ[f'USE_NEW_{service_name.upper()}'] = 'false'
        
        # 3. ログに記録
        logging.warning(f"Rolled back {service_name} to legacy implementation")
        
        # 4. アラート送信
        self._send_rollback_alert(service_name)
    
    def _send_rollback_alert(self, service_name: str):
        """ロールバックをチームに通知"""
        # Slack/Email通知など
        pass
```

## 7. まとめ

この補足資料により、V3設計の実装において：

1. **セッション管理**: 既存の仕組みを完全に維持
2. **安全な移行**: Shadow Testing、フィーチャーフラグ、カナリアリリース
3. **徹底的なテスト**: ゴールデンテスト、リグレッションテスト、パフォーマンステスト
4. **詳細な監視**: メトリクス収集、A/Bテスト、自動レポート
5. **確実なロールバック**: 即時・部分的なロールバックが可能

これにより、**既存機能を一切壊すことなく**、段階的かつ安全にリファクタリングを進めることができます。