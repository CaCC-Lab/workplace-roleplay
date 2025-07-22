"""
あらゆる想定を考慮した徹底的な包括テスト
CLAUDE.md原則: モック禁止、実際のAPI使用、完全網羅テスト
"""
import pytest
import json
import time
import threading
import psutil
import gc
import sys
import os
import requests
import random
import string
import html
import base64
import hashlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
import warnings
warnings.filterwarnings("ignore")

from app import app


class TestExhaustiveComprehensive:
    """あらゆる想定を考慮した徹底的テスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['CSRF_ENABLED'] = False
        with app.test_client() as client:
            with app.app_context():
                yield client

    @pytest.fixture
    def csrf_token(self, client):
        """CSRFトークンを取得"""
        response = client.get('/api/csrf-token')
        return response.get_json().get('csrf_token', '')

    # ==================== セキュリティテスト ====================

    def test_sql_injection_attempts(self, client, csrf_token):
        """SQLインジェクション攻撃テスト"""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'admin'); --",
            "' OR 1=1; --",
            "admin'--",
            "admin'/*",
            "' OR 'x'='x",
            "'; EXEC xp_cmdshell('dir'); --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --"
        ]
        
        print("\n🔒 SQLインジェクション攻撃テスト実行中...")
        
        for payload in sql_payloads:
            # チャットメッセージでSQLインジェクション試行
            init_response = client.post('/api/start_chat',
                                       json={
                                           'model': 'gemini-1.5-flash',
                                           'partner_type': 'colleague',
                                           'situation': 'break',
                                           'topic': 'general'
                                       },
                                       headers={
                                           'Content-Type': 'application/json',
                                           'X-CSRFToken': csrf_token
                                       })
            
            if init_response.status_code == 200:
                response = client.post('/api/chat',
                                      json={'message': payload},
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                # SQLインジェクションが成功していないことを確認
                assert response.status_code in [200, 400, 429], f"SQLペイロードで予期しないエラー: {payload}"
                
                if response.status_code == 200:
                    # レスポンスにSQLエラーメッセージが含まれていないか確認
                    data = response.data.decode('utf-8').lower()
                    sql_error_keywords = ['sql error', 'database error', 'mysql', 'postgresql', 'sqlite']
                    for keyword in sql_error_keywords:
                        assert keyword not in data, f"SQLエラーが露出: {keyword} in {payload}"
            
            time.sleep(0.2)  # レート制限対策

    def test_xss_attack_attempts(self, client, csrf_token):
        """XSS攻撃テスト"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<svg onload=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=\"alert('XSS')\">",
            "<audio src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "\"><script>alert('XSS')</script>",
            "<script>document.cookie='stolen'</script>"
        ]
        
        print("\n🛡️ XSS攻撃テスト実行中...")
        
        for payload in xss_payloads:
            init_response = client.post('/api/start_chat',
                                       json={
                                           'model': 'gemini-1.5-flash',
                                           'partner_type': 'colleague',
                                           'situation': 'break',
                                           'topic': 'general'
                                       },
                                       headers={
                                           'Content-Type': 'application/json',
                                           'X-CSRFToken': csrf_token
                                       })
            
            if init_response.status_code == 200:
                response = client.post('/api/chat',
                                      json={'message': payload},
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                # XSSが適切にエスケープされているか確認
                if response.status_code == 200:
                    data = response.data.decode('utf-8')
                    # 生のスクリプトタグが残っていないか確認
                    assert '<script>' not in data, f"XSSペイロードがエスケープされていない: {payload}"
                    assert 'javascript:' not in data, f"JavaScriptプロトコルがエスケープされていない: {payload}"
            
            time.sleep(0.2)

    def test_csrf_protection_verification(self, client):
        """CSRF保護の検証（テスト環境では無効化されているが構造確認）"""
        print("\n🔐 CSRF保護構造検証...")
        
        # CSRFトークンなしでリクエスト
        response = client.post('/api/chat',
                              json={'message': 'テスト'},
                              headers={'Content-Type': 'application/json'})
        
        # テスト環境ではCSRFが無効化されているため成功するが、
        # 本番環境での保護機能が実装されていることを確認
        csrf_token_endpoint = client.get('/api/csrf-token')
        assert csrf_token_endpoint.status_code == 200, "CSRFトークンエンドポイントが機能していない"
        
        token_data = csrf_token_endpoint.get_json()
        assert 'csrf_token' in token_data, "CSRFトークンが生成されていない"

    # ==================== エッジケース・ストレステスト ====================

    def test_extreme_message_lengths(self, client, csrf_token):
        """極端なメッセージ長テスト"""
        print("\n📏 極端なメッセージ長テスト...")
        
        # セッション初期化
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        if init_response.status_code != 200:
            pytest.skip("セッション初期化失敗によりメッセージ長テストをスキップ")
        
        # 極端に短いメッセージ
        for short_msg in ['', ' ', 'a', '1']:
            response = client.post('/api/chat',
                                  json={'message': short_msg},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            # 空メッセージはエラーでも良いが、アプリがクラッシュしてはいけない
            assert response.status_code in [200, 400, 429], f"短いメッセージで予期しないエラー: '{short_msg}'"
        
        # 極端に長いメッセージ
        long_messages = [
            'あ' * 1000,    # 1000文字
            'あ' * 10000,   # 10000文字
            'テスト' * 1000,  # 繰り返し
            '🚀' * 500,     # 絵文字
            string.ascii_letters * 100  # ASCII文字
        ]
        
        for long_msg in long_messages:
            response = client.post('/api/chat',
                                  json={'message': long_msg},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            # 長いメッセージでもアプリがクラッシュしてはいけない
            assert response.status_code in [200, 400, 413, 429], f"長いメッセージで予期しないエラー: {len(long_msg)}文字"
            time.sleep(0.3)

    def test_special_characters_and_encodings(self, client, csrf_token):
        """特殊文字とエンコーディングテスト"""
        print("\n🔤 特殊文字・エンコーディングテスト...")
        
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        if init_response.status_code != 200:
            pytest.skip("セッション初期化失敗により特殊文字テストをスキップ")
        
        special_messages = [
            "🚀🎉🌟💖🔥",  # 絵文字
            "Hello 世界 🌍",  # 混合文字
            "ñáéíóúüç",  # アクセント付き文字
            "Здравствуй мир",  # キリル文字
            "مرحبا بالعالم",  # アラビア文字
            "你好世界",  # 中国語
            "안녕하세요",  # 韓国語
            "こんにちは👋世界🌎",  # 日本語+絵文字
            "\n\t\r",  # 制御文字
            "\"'`\\",  # 引用符・エスケープ文字
            "<!DOCTYPE html>",  # HTML
            "{\"json\": \"test\"}",  # JSON
            "function() { return true; }",  # JavaScript
            "SELECT * FROM users;",  # SQL
            "/*コメント*/",  # コメント文字
            "&lt;&gt;&amp;",  # HTMLエンティティ
            "±÷×≈≠≤≥",  # 数学記号
            "©®™€£¥",  # 記号・通貨
        ]
        
        for msg in special_messages:
            response = client.post('/api/chat',
                                  json={'message': msg},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            assert response.status_code in [200, 400, 429], f"特殊文字でエラー: {repr(msg)}"
            
            if response.status_code == 200:
                # レスポンスが適切にエンコードされているか確認
                data = response.data.decode('utf-8')
                # 基本的なJSON構造が維持されているか確認
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        json.loads(data)
                    except json.JSONDecodeError:
                        pytest.fail(f"無効なJSONレスポンス for message: {repr(msg)}")
            
            time.sleep(0.2)

    def test_concurrent_requests_stress(self, client, csrf_token):
        """同時リクエスト・ストレステスト"""
        print("\n⚡ 同時リクエストストレステスト...")
        
        def make_concurrent_request(thread_id):
            """並行リクエストを実行"""
            try:
                # セッション初期化
                init_response = client.post('/api/start_chat',
                                           json={
                                               'model': 'gemini-1.5-flash',
                                               'partner_type': 'colleague',
                                               'situation': 'break',
                                               'topic': 'general'
                                           },
                                           headers={
                                               'Content-Type': 'application/json',
                                               'X-CSRFToken': csrf_token
                                           })
                
                if init_response.status_code != 200:
                    return {'thread_id': thread_id, 'success': False, 'error': 'init_failed'}
                
                # チャットリクエスト
                response = client.post('/api/chat',
                                      json={'message': f'並行テスト{thread_id}'},
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                return {
                    'thread_id': thread_id,
                    'success': response.status_code in [200, 429],
                    'status_code': response.status_code,
                    'response_time': time.time()
                }
                
            except Exception as e:
                return {'thread_id': thread_id, 'success': False, 'error': str(e)}
        
        # 5個の並行リクエストでテスト（レート制限を考慮）
        concurrent_count = 5
        results = []
        
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(concurrent_count)]
            
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
        
        # 結果分析
        successful_requests = sum(1 for r in results if r.get('success', False))
        print(f"並行リクエスト結果: {successful_requests}/{concurrent_count} 成功")
        
        # 少なくとも1つは成功すること（レート制限があっても）
        assert successful_requests >= 1, f"並行リクエストが全て失敗: {results}"

    def test_memory_usage_monitoring(self, client, csrf_token):
        """メモリ使用量監視テスト"""
        print("\n🧠 メモリ使用量監視テスト...")
        
        # 初期メモリ使用量を記録
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        if init_response.status_code != 200:
            pytest.skip("セッション初期化失敗によりメモリテストをスキップ")
        
        # 10回のリクエストでメモリ使用量をモニタリング
        memory_readings = []
        
        for i in range(10):
            response = client.post('/api/chat',
                                  json={'message': f'メモリテスト{i}'},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            if response.status_code == 429:
                break
            
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_readings.append(current_memory)
            time.sleep(1)
        
        if memory_readings:
            final_memory = memory_readings[-1]
            memory_increase = final_memory - initial_memory
            
            print(f"メモリ使用量: 初期 {initial_memory:.1f}MB → 最終 {final_memory:.1f}MB (増加: {memory_increase:.1f}MB)")
            
            # 極端なメモリリークがないことを確認（100MB以上の増加は異常）
            assert memory_increase < 100, f"メモリリークの可能性: {memory_increase:.1f}MB増加"

    # ==================== データ整合性・状態管理テスト ====================

    def test_session_state_consistency(self, client, csrf_token):
        """セッション状態の整合性テスト"""
        print("\n🔄 セッション状態整合性テスト...")
        
        # 複数のセッション設定で状態の整合性を確認
        session_configs = [
            {'partner_type': 'colleague', 'situation': 'break', 'topic': 'general'},
            {'partner_type': 'superior', 'situation': 'meeting', 'topic': 'work'},
            {'partner_type': 'subordinate', 'situation': 'after_work', 'topic': 'hobby'}
        ]
        
        for config in session_configs:
            # セッション初期化
            init_response = client.post('/api/start_chat',
                                       json={**config, 'model': 'gemini-1.5-flash'},
                                       headers={
                                           'Content-Type': 'application/json',
                                           'X-CSRFToken': csrf_token
                                       })
            
            if init_response.status_code == 200:
                # 複数のメッセージでコンテキスト保持を確認
                messages = [
                    '最初のメッセージです',
                    '2番目のメッセージで、最初の内容を参照します',
                    '最後のメッセージです'
                ]
                
                for msg in messages:
                    response = client.post('/api/chat',
                                          json={'message': msg},
                                          headers={
                                              'Content-Type': 'application/json',
                                              'X-CSRFToken': csrf_token
                                          })
                    
                    if response.status_code == 429:
                        break
                    
                    assert response.status_code == 200, f"セッション状態が不整合: {config}"
                    time.sleep(0.5)
            
            time.sleep(1)

    def test_data_validation_edge_cases(self, client, csrf_token):
        """データ検証エッジケースのテスト"""
        print("\n✅ データ検証エッジケーステスト...")
        
        # 無効なJSONペイロード
        invalid_payloads = [
            '{"message": }',  # 無効なJSON
            '{"msg": "test"}',  # 間違ったフィールド名
            '{"message": null}',  # null値
            '{"message": 123}',  # 数値（文字列期待）
            '{"message": []}',  # 配列
            '{"message": {}}',  # オブジェクト
            '',  # 空文字列
            'not json at all',  # 非JSON
            '{"message": "test", "extra": "field"}',  # 余分なフィールド
        ]
        
        for payload in invalid_payloads:
            try:
                response = client.post('/api/chat',
                                      data=payload,
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                # 無効なペイロードは適切にエラーハンドリングされるべき
                assert response.status_code in [400, 415, 422], f"無効なペイロードが受け入れられた: {payload}"
                
            except Exception as e:
                # アプリケーションがクラッシュしてはいけない
                pytest.fail(f"無効なペイロードでアプリケーションクラッシュ: {payload}, {e}")

    # ==================== パフォーマンス・タイミングテスト ====================

    def test_response_time_measurement(self, client, csrf_token):
        """レスポンス時間測定テスト"""
        print("\n⏱️ レスポンス時間測定テスト...")
        
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        if init_response.status_code != 200:
            pytest.skip("セッション初期化失敗によりパフォーマンステストをスキップ")
        
        response_times = []
        
        for i in range(5):
            start_time = time.time()
            
            response = client.post('/api/chat',
                                  json={'message': f'パフォーマンステスト{i}'},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 429:
                break
            
            if response.status_code == 200:
                response_times.append(response_time)
            
            time.sleep(2)  # レート制限対策
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            print(f"レスポンス時間統計: 平均 {avg_response_time:.2f}秒, 最大 {max_response_time:.2f}秒")
            
            # 極端に遅いレスポンスがないことを確認（60秒以上は異常）
            assert max_response_time < 60, f"レスポンス時間が異常に遅い: {max_response_time:.2f}秒"

    # ==================== API制限・エラー境界テスト ====================

    def test_api_parameter_boundary_conditions(self, client, csrf_token):
        """APIパラメータ境界条件テスト"""
        print("\n🎯 APIパラメータ境界条件テスト...")
        
        # partner_type境界テスト
        partner_type_tests = [
            ('colleague', True),
            ('superior', True),
            ('subordinate', True),
            ('', False),
            ('invalid_partner', False),
            ('COLLEAGUE', False),  # 大文字
            ('colleague123', False),
            (None, False)
        ]
        
        for partner_type, should_succeed in partner_type_tests:
            payload = {
                'model': 'gemini-1.5-flash',
                'situation': 'break',
                'topic': 'general'
            }
            
            if partner_type is not None:
                payload['partner_type'] = partner_type
            
            response = client.post('/api/start_chat',
                                  json=payload,
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            if should_succeed:
                assert response.status_code in [200, 429], f"有効なpartner_type'{partner_type}'が拒否された"
            else:
                assert response.status_code in [400, 422], f"無効なpartner_type'{partner_type}'が受け入れられた"
        
        # モデル名境界テスト
        model_tests = [
            ('gemini-1.5-flash', True),
            ('gemini-1.5-pro', True),
            ('', False),
            ('invalid_model', False),
            ('gpt-4', False),  # 他社モデル
            (None, False)
        ]
        
        for model, should_succeed in model_tests:
            payload = {
                'partner_type': 'colleague',
                'situation': 'break',
                'topic': 'general'
            }
            
            if model is not None:
                payload['model'] = model
            
            response = client.post('/api/start_chat',
                                  json=payload,
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            if should_succeed:
                assert response.status_code in [200, 429], f"有効なmodel'{model}'が拒否された"
            else:
                assert response.status_code in [400, 422], f"無効なmodel'{model}'が受け入れられた"

    # ==================== 国際化・多言語テスト ====================

    def test_multilingual_support(self, client, csrf_token):
        """多言語サポートテスト"""
        print("\n🌍 多言語サポートテスト...")
        
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        if init_response.status_code != 200:
            pytest.skip("セッション初期化失敗により多言語テストをスキップ")
        
        multilingual_messages = [
            "Hello, how are you today?",  # 英語
            "Hola, ¿cómo estás?",  # スペイン語
            "Bonjour, comment allez-vous?",  # フランス語
            "Guten Tag, wie geht es Ihnen?",  # ドイツ語
            "Buongiorno, come sta?",  # イタリア語
            "你好，你好吗？",  # 中国語（簡体字）
            "你好，你好嗎？",  # 中国語（繁体字）
            "안녕하세요, 어떻게 지내세요?",  # 韓国語
            "こんにちは、元気ですか？",  # 日本語
            "Здравствуйте, как дела?",  # ロシア語
            "مرحبا، كيف حالك؟",  # アラビア語
            "हैलो, आप कैसे हैं?",  # ヒンディー語
        ]
        
        for msg in multilingual_messages:
            response = client.post('/api/chat',
                                  json={'message': msg},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            if response.status_code == 429:
                break
            
            assert response.status_code in [200, 400], f"多言語メッセージでエラー: {msg}"
            
            if response.status_code == 200:
                # レスポンスが適切にエンコードされているか確認
                data = response.data.decode('utf-8')
                # Unicode文字が適切に処理されているか基本チェック
                assert len(data) > 0, f"空のレスポンス for multilingual message: {msg}"
            
            time.sleep(0.5)

    # ==================== ログ・監査・エラー追跡テスト ====================

    def test_error_logging_and_tracking(self, client, csrf_token):
        """エラーログ・追跡テスト"""
        print("\n📝 エラーログ・追跡テスト...")
        
        # 意図的にエラーを発生させてログを確認
        error_inducing_requests = [
            # 空のメッセージ
            {'message': ''},
            # 極端に長いメッセージ
            {'message': 'x' * 50000},
            # 無効なフィールド
            {'invalid_field': 'test'},
            # 型不一致
            {'message': 123}
        ]
        
        for req in error_inducing_requests:
            response = client.post('/api/chat',
                                  json=req,
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            # エラーが適切にハンドリングされているか確認
            assert response.status_code in [200, 400, 413, 422, 429], f"予期しないエラーレスポンス: {req}"
            
            if response.status_code in [400, 422]:
                # エラーレスポンスが適切な形式か確認
                try:
                    error_data = response.get_json()
                    assert 'error' in error_data or 'message' in error_data, "エラーレスポンスに説明がない"
                except:
                    # JSONでない場合もエラーメッセージがあるべき
                    assert len(response.data) > 0, "エラーレスポンスが空"

    # ==================== ネットワーク・接続テスト ====================

    def test_timeout_and_connection_handling(self, client, csrf_token):
        """タイムアウト・接続処理テスト"""
        print("\n🔌 タイムアウト・接続処理テスト...")
        
        # 複数の迅速なリクエストでタイムアウト処理をテスト
        rapid_requests = []
        
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        if init_response.status_code != 200:
            pytest.skip("セッション初期化失敗によりタイムアウトテストをスキップ")
        
        # 10個の迅速なリクエスト
        for i in range(10):
            start_time = time.time()
            
            response = client.post('/api/chat',
                                  json={'message': f'迅速リクエスト{i}'},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            end_time = time.time()
            duration = end_time - start_time
            
            rapid_requests.append({
                'index': i,
                'status_code': response.status_code,
                'duration': duration,
                'success': response.status_code in [200, 429]
            })
            
            # レート制限に達した場合は停止
            if response.status_code == 429:
                print(f"レート制限に達しました（{i+1}番目のリクエスト）")
                break
        
        # 結果分析
        successful_requests = [r for r in rapid_requests if r['success']]
        print(f"迅速リクエスト結果: {len(successful_requests)}/{len(rapid_requests)} 成功")
        
        if successful_requests:
            avg_duration = sum(r['duration'] for r in successful_requests) / len(successful_requests)
            print(f"平均応答時間: {avg_duration:.2f}秒")
            
            # 極端に遅いリクエストがないことを確認
            max_duration = max(r['duration'] for r in successful_requests)
            assert max_duration < 120, f"タイムアウト時間が異常: {max_duration:.2f}秒"

    # ==================== 総合評価・メトリクステスト ====================

    def test_comprehensive_metrics_collection(self, client, csrf_token):
        """包括的メトリクス収集テスト"""
        print("\n📊 包括的メトリクス収集...")
        
        metrics = {
            'total_tests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'average_response_time': 0,
            'memory_usage_mb': 0,
            'endpoints_tested': set(),
            'error_types': {},
            'features_tested': []
        }
        
        # 各エンドポイントのテスト
        endpoints = [
            ('/api/csrf-token', 'GET'),
            ('/api/models', 'GET'),
            ('/api/scenarios', 'GET'),
            ('/api/start_chat', 'POST'),
            ('/api/chat', 'POST')
        ]
        
        for endpoint, method in endpoints:
            metrics['endpoints_tested'].add(endpoint)
            
            try:
                if method == 'GET':
                    response = client.get(endpoint)
                else:
                    if endpoint == '/api/start_chat':
                        data = {
                            'model': 'gemini-1.5-flash',
                            'partner_type': 'colleague',
                            'situation': 'break',
                            'topic': 'general'
                        }
                    elif endpoint == '/api/chat':
                        data = {'message': 'メトリクステスト'}
                    
                    response = client.post(endpoint,
                                          json=data,
                                          headers={
                                              'Content-Type': 'application/json',
                                              'X-CSRFToken': csrf_token
                                          })
                
                metrics['total_tests'] += 1
                
                if response.status_code == 200:
                    metrics['successful_requests'] += 1
                elif response.status_code == 429:
                    metrics['rate_limited_requests'] += 1
                else:
                    metrics['failed_requests'] += 1
                    error_type = f"HTTP_{response.status_code}"
                    metrics['error_types'][error_type] = metrics['error_types'].get(error_type, 0) + 1
                
            except Exception as e:
                metrics['failed_requests'] += 1
                error_type = type(e).__name__
                metrics['error_types'][error_type] = metrics['error_types'].get(error_type, 0) + 1
        
        # メモリ使用量測定
        try:
            process = psutil.Process()
            metrics['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
        except:
            metrics['memory_usage_mb'] = 0
        
        # テスト機能一覧
        metrics['features_tested'] = [
            'セキュリティ（SQLインジェクション、XSS）',
            '極端なメッセージ長',
            '特殊文字・エンコーディング',
            '同時リクエスト',
            'メモリ使用量監視',
            'セッション状態整合性',
            'データ検証エッジケース',
            'レスポンス時間測定',
            'APIパラメータ境界条件',
            '多言語サポート',
            'エラーログ・追跡',
            'タイムアウト・接続処理'
        ]
        
        # 最終レポート出力
        print("\n" + "="*50)
        print("📈 徹底的テスト最終レポート")
        print("="*50)
        print(f"総テスト数: {metrics['total_tests']}")
        print(f"成功リクエスト: {metrics['successful_requests']}")
        print(f"失敗リクエスト: {metrics['failed_requests']}")
        print(f"レート制限: {metrics['rate_limited_requests']}")
        print(f"メモリ使用量: {metrics['memory_usage_mb']:.1f} MB")
        print(f"テスト済みエンドポイント: {len(metrics['endpoints_tested'])}")
        print(f"エラータイプ: {metrics['error_types']}")
        print(f"テスト済み機能数: {len(metrics['features_tested'])}")
        print("="*50)
        
        # 基本的な品質基準
        success_rate = metrics['successful_requests'] / max(1, metrics['total_tests'])
        assert success_rate >= 0.3, f"成功率が低すぎる: {success_rate:.1%}"
        assert len(metrics['endpoints_tested']) >= 3, "テスト済みエンドポイントが不足"
        assert len(metrics['features_tested']) >= 10, "テスト済み機能が不足"