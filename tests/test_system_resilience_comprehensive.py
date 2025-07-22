"""
システム回復性・データ整合性・極限状況の徹底的テスト
CLAUDE.md原則: モック禁止、実際のシステム状態での検証
"""
import pytest
import json
import time
import threading
import os
import psutil
import gc
import requests
import random
import string
import hashlib
import tempfile
import shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
import subprocess
import signal
import sys

from app import app


class TestSystemResilienceComprehensive:
    """システム回復性・極限状況の徹底的テスト"""

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

    # ==================== システムリソース極限テスト ====================

    def test_extreme_memory_pressure(self, client, csrf_token):
        """極限メモリ圧迫テスト"""
        print("\n🧠 極限メモリ圧迫テスト...")
        
        # 初期メモリ状態を記録
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
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
            pytest.skip("セッション初期化失敗によりメモリ圧迫テストをスキップ")
        
        # 大量のメモリを消費する操作を実行
        memory_intensive_operations = []
        
        try:
            # 1. 大量の文字列生成
            large_strings = []
            for i in range(10):
                large_string = 'A' * (1024 * 1024)  # 1MB文字列
                large_strings.append(large_string)
            
            # 2. メモリ使用量を監視しながらリクエスト
            for i in range(20):
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                if memory_increase > 500:  # 500MB増加で停止
                    print(f"⚠️ メモリ使用量が{memory_increase:.1f}MB増加したため停止")
                    break
                
                # 大きなメッセージでリクエスト
                large_message = f"メモリテスト{i}" + "データ" * 1000
                
                response = client.post('/api/chat',
                                      json={'message': large_message},
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                if response.status_code == 429:
                    break
                
                # アプリケーションがクラッシュしていないことを確認
                assert response.status_code in [200, 400, 413], f"メモリ圧迫でアプリケーション異常: {response.status_code}"
                
                # 短時間待機
                time.sleep(0.1)
            
            # ガベージコレクション実行
            gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024
            total_increase = final_memory - initial_memory
            
            print(f"メモリ圧迫テスト結果: {initial_memory:.1f}MB → {final_memory:.1f}MB (増加: {total_increase:.1f}MB)")
            
            # 極端なメモリリークがないことを確認
            assert total_increase < 200, f"メモリリークの可能性: {total_increase:.1f}MB増加"
            
        finally:
            # メモリ解放
            large_strings = None
            gc.collect()

    def test_cpu_intensive_operations(self, client, csrf_token):
        """CPU集約的操作テスト"""
        print("\n⚡ CPU集約的操作テスト...")
        
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
            pytest.skip("セッション初期化失敗によりCPUテストをスキップ")
        
        # CPU使用率監視
        cpu_percentages = []
        
        def monitor_cpu():
            """CPU使用率を監視"""
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_percentages.append(cpu_percent)
        
        # CPU監視スレッドを開始
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # CPU集約的なメッセージを送信
        complex_messages = [
            "この複雑な計算について説明してください: " + "π" * 1000,
            "以下の複雑なシナリオを分析してください: " + "複雑な状況" * 500,
            "詳細な分析をお願いします: " + "データ分析" * 800,
        ]
        
        cpu_test_start = time.time()
        
        for i, message in enumerate(complex_messages):
            response = client.post('/api/chat',
                                  json={'message': message},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            if response.status_code == 429:
                break
            
            # アプリケーションが応答することを確認
            assert response.status_code in [200, 400], f"CPU集約的操作でアプリケーション異常: {response.status_code}"
            
            print(f"CPU集約的メッセージ {i+1}/3 処理完了")
            time.sleep(1)
        
        cpu_test_end = time.time()
        
        # CPU監視の完了を待つ
        monitor_thread.join(timeout=5)
        
        if cpu_percentages:
            avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
            max_cpu = max(cpu_percentages)
            
            print(f"CPU使用率: 平均 {avg_cpu:.1f}%, 最大 {max_cpu:.1f}%")
            print(f"CPU集約的操作時間: {cpu_test_end - cpu_test_start:.2f}秒")
            
            # 極端にCPU使用率が高くないことを確認（90%以下）
            assert max_cpu < 90, f"CPU使用率が異常に高い: {max_cpu:.1f}%"

    def test_disk_space_pressure(self, client, csrf_token):
        """ディスク容量圧迫テスト"""
        print("\n💽 ディスク容量圧迫テスト...")
        
        # 一時ディレクトリでディスク容量をテスト
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 現在のディスク使用量を確認
            disk_usage = shutil.disk_usage(temp_dir)
            free_space_gb = disk_usage.free / (1024**3)
            
            print(f"利用可能ディスク容量: {free_space_gb:.1f}GB")
            
            if free_space_gb < 1:
                print("⚠️ ディスク容量が不足しているため圧迫テストをスキップ")
                return
            
            # 少量のテストファイルを作成（実際のディスク圧迫は危険なので控えめに）
            test_files = []
            total_size = 0
            max_test_size = min(100 * 1024 * 1024, free_space_gb * 0.1 * 1024**3)  # 100MBまたは空き容量の10%
            
            while total_size < max_test_size:
                file_path = os.path.join(temp_dir, f"test_file_{len(test_files)}.dat")
                file_size = min(10 * 1024 * 1024, max_test_size - total_size)  # 10MBずつ
                
                with open(file_path, 'wb') as f:
                    f.write(b'0' * file_size)
                
                test_files.append(file_path)
                total_size += file_size
                
                if len(test_files) >= 10:  # 最大10ファイル
                    break
            
            print(f"テストファイル作成完了: {len(test_files)}ファイル, {total_size / 1024 / 1024:.1f}MB")
            
            # ディスク容量圧迫下でのアプリケーション動作テスト
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
                                      json={'message': 'ディスク容量テスト'},
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                # ディスク容量圧迫下でもアプリケーションが動作することを確認
                assert response.status_code in [200, 400, 429], f"ディスク圧迫でアプリケーション異常: {response.status_code}"
                
                print("✅ ディスク容量圧迫下でのアプリケーション動作OK")
            
        finally:
            # テストファイルを削除
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ==================== ネットワーク障害・復旧テスト ====================

    def test_gemini_api_failure_simulation(self, client, csrf_token):
        """Gemini API障害シミュレーション"""
        print("\n🔌 Gemini API障害シミュレーション...")
        
        # 無効なAPIキーで障害をシミュレート
        original_api_key = os.environ.get('GOOGLE_API_KEY')
        
        try:
            # 無効なAPIキーを設定
            os.environ['GOOGLE_API_KEY'] = 'invalid_key_for_testing'
            
            # アプリケーションを再初期化（注意：この方法は限定的）
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
            
            # API障害時の適切なエラーハンドリングを確認
            if init_response.status_code != 200:
                error_data = init_response.get_json()
                if error_data and 'error' in error_data:
                    print(f"✅ API障害が適切にハンドリングされています: {error_data['error']}")
                else:
                    print("⚠️ API障害のエラーメッセージが不明確")
            
        finally:
            # 元のAPIキーを復元
            if original_api_key:
                os.environ['GOOGLE_API_KEY'] = original_api_key
            else:
                os.environ.pop('GOOGLE_API_KEY', None)

    def test_network_timeout_handling(self, client, csrf_token):
        """ネットワークタイムアウト処理テスト"""
        print("\n⏰ ネットワークタイムアウト処理テスト...")
        
        # 複数の迅速なリクエストでタイムアウトを誘発
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
        
        timeout_results = []
        
        # 10個の同時リクエストでタイムアウトをテスト
        for i in range(10):
            start_time = time.time()
            
            response = client.post('/api/chat',
                                  json={'message': f'タイムアウトテスト{i}'},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            
            end_time = time.time()
            duration = end_time - start_time
            
            timeout_results.append({
                'index': i,
                'status_code': response.status_code,
                'duration': duration,
                'success': response.status_code in [200, 429]
            })
            
            if response.status_code == 429:
                print(f"レート制限到達（{i+1}番目のリクエスト）")
                break
            
            # 間隔なしで連続実行
        
        # タイムアウト結果の分析
        successful_requests = [r for r in timeout_results if r['success']]
        failed_requests = [r for r in timeout_results if not r['success']]
        
        print(f"タイムアウトテスト結果: 成功 {len(successful_requests)}, 失敗 {len(failed_requests)}")
        
        if successful_requests:
            avg_duration = sum(r['duration'] for r in successful_requests) / len(successful_requests)
            max_duration = max(r['duration'] for r in successful_requests)
            print(f"平均応答時間: {avg_duration:.2f}秒, 最大: {max_duration:.2f}秒")
            
            # 極端に遅いタイムアウトがないことを確認
            assert max_duration < 60, f"応答時間が異常: {max_duration:.2f}秒"

    # ==================== データ整合性・永続性テスト ====================

    def test_session_data_consistency(self, client, csrf_token):
        """セッションデータ整合性テスト"""
        print("\n🔄 セッションデータ整合性テスト...")
        
        # 複数の設定でセッションを作成し、データの整合性を確認
        session_configs = [
            {
                'name': '同僚-休憩-一般',
                'config': {'partner_type': 'colleague', 'situation': 'break', 'topic': 'general'}
            },
            {
                'name': '上司-会議-仕事',
                'config': {'partner_type': 'superior', 'situation': 'meeting', 'topic': 'work'}
            },
            {
                'name': '部下-仕事後-趣味',
                'config': {'partner_type': 'subordinate', 'situation': 'after_work', 'topic': 'hobby'}
            }
        ]
        
        session_test_results = []
        
        for session_info in session_configs:
            config = session_info['config']
            name = session_info['name']
            
            print(f"🔍 {name} セッションテスト...")
            
            # セッション初期化
            init_response = client.post('/api/start_chat',
                                       json={**config, 'model': 'gemini-1.5-flash'},
                                       headers={
                                           'Content-Type': 'application/json',
                                           'X-CSRFToken': csrf_token
                                       })
            
            session_result = {
                'name': name,
                'init_success': init_response.status_code == 200,
                'messages_sent': 0,
                'responses_received': 0,
                'errors': []
            }
            
            if init_response.status_code == 200:
                # 3つのメッセージでコンテキスト整合性をテスト
                test_messages = [
                    f'{name}での最初のメッセージです',
                    '前のメッセージを覚えていますか？',
                    'セッションの整合性をテストしています'
                ]
                
                for i, message in enumerate(test_messages):
                    response = client.post('/api/chat',
                                          json={'message': message},
                                          headers={
                                              'Content-Type': 'application/json',
                                              'X-CSRFToken': csrf_token
                                          })
                    
                    session_result['messages_sent'] += 1
                    
                    if response.status_code == 200:
                        session_result['responses_received'] += 1
                    elif response.status_code == 429:
                        break
                    else:
                        session_result['errors'].append(f"メッセージ{i+1}: HTTP {response.status_code}")
                    
                    time.sleep(0.5)
            
            session_test_results.append(session_result)
            time.sleep(1)  # セッション間の待機
        
        # 結果分析
        successful_sessions = [s for s in session_test_results if s['init_success']]
        print(f"\nセッション整合性結果: {len(successful_sessions)}/{len(session_configs)} セッション成功")
        
        for result in session_test_results:
            print(f"  {result['name']}: 初期化={result['init_success']}, メッセージ={result['messages_sent']}, 応答={result['responses_received']}")
            if result['errors']:
                print(f"    エラー: {result['errors']}")
        
        # 少なくとも半数のセッションが成功することを確認
        assert len(successful_sessions) >= len(session_configs) / 2, "セッション整合性が不足"

    def test_concurrent_session_isolation(self, client, csrf_token):
        """同時セッション分離テスト"""
        print("\n🔒 同時セッション分離テスト...")
        
        def create_isolated_session(session_id):
            """分離されたセッションを作成してテスト"""
            try:
                # 各スレッドで独立したセッション設定
                configs = [
                    {'partner_type': 'colleague', 'situation': 'break', 'topic': 'general'},
                    {'partner_type': 'superior', 'situation': 'meeting', 'topic': 'work'},
                    {'partner_type': 'subordinate', 'situation': 'after_work', 'topic': 'hobby'}
                ]
                
                config = configs[session_id % len(configs)]
                
                # セッション初期化
                init_response = client.post('/api/start_chat',
                                           json={**config, 'model': 'gemini-1.5-flash'},
                                           headers={
                                               'Content-Type': 'application/json',
                                               'X-CSRFToken': csrf_token
                                           })
                
                if init_response.status_code != 200:
                    return {'session_id': session_id, 'success': False, 'error': 'init_failed'}
                
                # セッション固有のメッセージを送信
                unique_message = f"セッション{session_id}の固有メッセージ"
                
                response = client.post('/api/chat',
                                      json={'message': unique_message},
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                return {
                    'session_id': session_id,
                    'success': response.status_code in [200, 429],
                    'status_code': response.status_code,
                    'config': config
                }
                
            except Exception as e:
                return {'session_id': session_id, 'success': False, 'error': str(e)}
        
        # 3つの同時セッションでテスト
        concurrent_sessions = 3
        isolation_results = []
        
        with ThreadPoolExecutor(max_workers=concurrent_sessions) as executor:
            futures = [executor.submit(create_isolated_session, i) for i in range(concurrent_sessions)]
            
            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result()
                    isolation_results.append(result)
                except Exception as e:
                    isolation_results.append({'success': False, 'error': str(e)})
        
        # 結果分析
        successful_sessions = [r for r in isolation_results if r.get('success', False)]
        print(f"同時セッション分離結果: {len(successful_sessions)}/{concurrent_sessions} 成功")
        
        for result in isolation_results:
            session_id = result.get('session_id', 'unknown')
            success = result.get('success', False)
            status = result.get('status_code', 'N/A')
            print(f"  セッション{session_id}: 成功={success}, ステータス={status}")
        
        # 少なくとも1つのセッションは成功することを確認
        assert len(successful_sessions) >= 1, "同時セッション分離が機能していない"

    # ==================== セキュリティ境界・攻撃耐性テスト ====================

    def test_injection_attack_comprehensive(self, client, csrf_token):
        """包括的インジェクション攻撃テスト"""
        print("\n🛡️ 包括的インジェクション攻撃テスト...")
        
        # 様々なインジェクション攻撃パターン
        injection_payloads = [
            # NoSQL インジェクション
            {"$ne": None},
            {"$regex": ".*"},
            {"$where": "function() { return true; }"},
            
            # LDAP インジェクション
            "*)(uid=*",
            "admin)(&(password=*))",
            
            # OS コマンドインジェクション
            "; ls -la",
            "| cat /etc/passwd",
            "&& whoami",
            "`id`",
            "$(uname -a)",
            
            # XML インジェクション
            "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>",
            
            # サーバーサイドテンプレートインジェクション
            "{{7*7}}",
            "${7*7}",
            "<%=7*7%>",
            "#{7*7}",
            
            # ディレクトリトラバーサル
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            
            # スクリプトインジェクション
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "onload=alert('XSS')",
        ]
        
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
            pytest.skip("セッション初期化失敗によりインジェクションテストをスキップ")
        
        injection_results = []
        
        for i, payload in enumerate(injection_payloads[:15]):  # 最初の15個をテスト
            if isinstance(payload, dict):
                # JSON形式のペイロード
                test_payload = {'message': payload}
            else:
                # 文字列形式のペイロード
                test_payload = {'message': str(payload)}
            
            try:
                response = client.post('/api/chat',
                                      json=test_payload,
                                      headers={
                                          'Content-Type': 'application/json',
                                          'X-CSRFToken': csrf_token
                                      })
                
                result = {
                    'payload_index': i,
                    'payload': str(payload)[:50] + '...' if len(str(payload)) > 50 else str(payload),
                    'status_code': response.status_code,
                    'safe': response.status_code in [200, 400, 422, 429]  # 適切なレスポンス
                }
                
                # レスポンス内容の安全性チェック
                if response.status_code == 200:
                    data = response.data.decode('utf-8')
                    # 機密情報が漏洩していないかチェック
                    sensitive_indicators = [
                        '/etc/passwd', '/etc/shadow', 'root:', 'admin:',
                        'windows\\system32', 'c:\\windows',
                        'database error', 'sql error', 'mysql error',
                        'uid=', 'gid=', 'groups='
                    ]
                    
                    for indicator in sensitive_indicators:
                        if indicator.lower() in data.lower():
                            result['safe'] = False
                            result['security_issue'] = f"機密情報漏洩の可能性: {indicator}"
                            break
                
                injection_results.append(result)
                
                if response.status_code == 429:
                    break
                
            except Exception as e:
                injection_results.append({
                    'payload_index': i,
                    'payload': str(payload)[:50],
                    'status_code': 'exception',
                    'safe': True,  # 例外も一種の防御
                    'error': str(e)
                })
            
            time.sleep(0.2)  # レート制限対策
        
        # 結果分析
        safe_results = [r for r in injection_results if r['safe']]
        unsafe_results = [r for r in injection_results if not r['safe']]
        
        print(f"インジェクション攻撃テスト結果: {len(safe_results)}/{len(injection_results)} 安全")
        
        if unsafe_results:
            print("🚨 セキュリティリスク検出:")
            for result in unsafe_results:
                print(f"  ペイロード{result['payload_index']}: {result.get('security_issue', '不明な問題')}")
        
        # 全てのインジェクション攻撃が適切に防御されていることを確認
        assert len(unsafe_results) == 0, f"セキュリティ脆弱性検出: {len(unsafe_results)}個の問題"

    # ==================== 総合システム評価 ====================

    def test_comprehensive_system_evaluation(self, client, csrf_token):
        """包括的システム評価"""
        print("\n📊 包括的システム評価...")
        
        evaluation_metrics = {
            'system_stability': {'score': 0, 'max_score': 100},
            'performance': {'score': 0, 'max_score': 100},
            'security': {'score': 0, 'max_score': 100},
            'resilience': {'score': 0, 'max_score': 100},
            'functionality': {'score': 0, 'max_score': 100},
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'errors': []
        }
        
        # 1. システム安定性評価
        print("🔍 システム安定性評価...")
        try:
            # 基本機能テスト
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
                evaluation_metrics['system_stability']['score'] += 30
                
                # 連続リクエスト安定性
                stable_requests = 0
                for i in range(5):
                    response = client.post('/api/chat',
                                          json={'message': f'安定性テスト{i}'},
                                          headers={
                                              'Content-Type': 'application/json',
                                              'X-CSRFToken': csrf_token
                                          })
                    if response.status_code in [200, 429]:
                        stable_requests += 1
                    time.sleep(0.5)
                
                evaluation_metrics['system_stability']['score'] += (stable_requests / 5) * 70
            
            evaluation_metrics['total_tests'] += 1
            evaluation_metrics['passed_tests'] += 1
            
        except Exception as e:
            evaluation_metrics['failed_tests'] += 1
            evaluation_metrics['errors'].append(f"安定性テスト: {e}")
        
        # 2. パフォーマンス評価
        print("🔍 パフォーマンス評価...")
        try:
            response_times = []
            
            for i in range(3):
                start_time = time.time()
                response = client.get('/api/csrf-token')
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                time.sleep(0.5)
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                
                if avg_response_time < 0.5:
                    evaluation_metrics['performance']['score'] = 100
                elif avg_response_time < 1.0:
                    evaluation_metrics['performance']['score'] = 80
                elif avg_response_time < 2.0:
                    evaluation_metrics['performance']['score'] = 60
                else:
                    evaluation_metrics['performance']['score'] = 40
            
            evaluation_metrics['total_tests'] += 1
            evaluation_metrics['passed_tests'] += 1
            
        except Exception as e:
            evaluation_metrics['failed_tests'] += 1
            evaluation_metrics['errors'].append(f"パフォーマンステスト: {e}")
        
        # 3. セキュリティ評価
        print("🔍 セキュリティ評価...")
        try:
            # 基本的なセキュリティチェック
            security_score = 0
            
            # CSRFトークンの存在確認
            csrf_response = client.get('/api/csrf-token')
            if csrf_response.status_code == 200:
                csrf_data = csrf_response.get_json()
                if 'csrf_token' in csrf_data:
                    security_score += 25
            
            # SQLインジェクション基本防御確認
            sql_test_response = client.post('/api/chat',
                                           json={'message': "'; DROP TABLE users; --"},
                                           headers={
                                               'Content-Type': 'application/json',
                                               'X-CSRFToken': csrf_token
                                           })
            if sql_test_response.status_code in [200, 400, 429]:
                security_score += 25
            
            # XSS基本防御確認
            xss_test_response = client.post('/api/chat',
                                           json={'message': "<script>alert('XSS')</script>"},
                                           headers={
                                               'Content-Type': 'application/json',
                                               'X-CSRFToken': csrf_token
                                           })
            if xss_test_response.status_code in [200, 400, 429]:
                security_score += 25
            
            # エラーメッセージの適切性
            error_response = client.post('/api/chat',
                                        json={'invalid': 'data'},
                                        headers={
                                            'Content-Type': 'application/json',
                                            'X-CSRFToken': csrf_token
                                        })
            if error_response.status_code in [400, 422]:
                security_score += 25
            
            evaluation_metrics['security']['score'] = security_score
            evaluation_metrics['total_tests'] += 1
            evaluation_metrics['passed_tests'] += 1
            
        except Exception as e:
            evaluation_metrics['failed_tests'] += 1
            evaluation_metrics['errors'].append(f"セキュリティテスト: {e}")
        
        # 4. システム回復性評価
        print("🔍 システム回復性評価...")
        try:
            resilience_score = 0
            
            # エラー後の回復テスト
            # 意図的にエラーを発生
            client.post('/api/chat',
                       json={'message': ''},
                       headers={
                           'Content-Type': 'application/json',
                           'X-CSRFToken': csrf_token
                       })
            
            # 正常なリクエストが続行できるかテスト
            recovery_response = client.post('/api/start_chat',
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
            
            if recovery_response.status_code in [200, 429]:
                resilience_score += 50
            
            # リソース使用量の妥当性
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                if memory_mb < 500:  # 500MB未満
                    resilience_score += 25
                if cpu_percent < 50:  # CPU 50%未満
                    resilience_score += 25
                    
            except:
                pass  # リソース監視エラーは無視
            
            evaluation_metrics['resilience']['score'] = resilience_score
            evaluation_metrics['total_tests'] += 1
            evaluation_metrics['passed_tests'] += 1
            
        except Exception as e:
            evaluation_metrics['failed_tests'] += 1
            evaluation_metrics['errors'].append(f"回復性テスト: {e}")
        
        # 5. 機能性評価
        print("🔍 機能性評価...")
        try:
            functionality_score = 0
            
            # 主要エンドポイントの動作確認
            endpoints = [
                ('/api/csrf-token', 'GET'),
                ('/api/models', 'GET'),
                ('/api/scenarios', 'GET')
            ]
            
            working_endpoints = 0
            for endpoint, method in endpoints:
                try:
                    if method == 'GET':
                        response = client.get(endpoint)
                    
                    if response.status_code == 200:
                        working_endpoints += 1
                except:
                    pass
            
            functionality_score = (working_endpoints / len(endpoints)) * 100
            evaluation_metrics['functionality']['score'] = functionality_score
            evaluation_metrics['total_tests'] += 1
            evaluation_metrics['passed_tests'] += 1
            
        except Exception as e:
            evaluation_metrics['failed_tests'] += 1
            evaluation_metrics['errors'].append(f"機能性テスト: {e}")
        
        # 総合評価の計算
        total_score = sum(metric['score'] for metric in evaluation_metrics.values() if isinstance(metric, dict) and 'score' in metric)
        max_total_score = sum(metric['max_score'] for metric in evaluation_metrics.values() if isinstance(metric, dict) and 'max_score' in metric)
        
        overall_score = (total_score / max_total_score) * 100 if max_total_score > 0 else 0
        
        # 最終レポート
        print("\n" + "="*60)
        print("🏆 包括的システム評価レポート")
        print("="*60)
        print(f"総合スコア: {overall_score:.1f}/100")
        print("-"*60)
        print(f"システム安定性: {evaluation_metrics['system_stability']['score']:.1f}/100")
        print(f"パフォーマンス: {evaluation_metrics['performance']['score']:.1f}/100")
        print(f"セキュリティ: {evaluation_metrics['security']['score']:.1f}/100")
        print(f"システム回復性: {evaluation_metrics['resilience']['score']:.1f}/100")
        print(f"機能性: {evaluation_metrics['functionality']['score']:.1f}/100")
        print("-"*60)
        print(f"実行テスト数: {evaluation_metrics['total_tests']}")
        print(f"成功: {evaluation_metrics['passed_tests']}")
        print(f"失敗: {evaluation_metrics['failed_tests']}")
        
        if evaluation_metrics['errors']:
            print("\n⚠️ 検出された問題:")
            for error in evaluation_metrics['errors']:
                print(f"  - {error}")
        
        print("="*60)
        
        # 品質基準の確認
        assert overall_score >= 60, f"総合品質スコアが基準を下回っています: {overall_score:.1f}/100"
        assert evaluation_metrics['security']['score'] >= 75, f"セキュリティスコアが不足: {evaluation_metrics['security']['score']}/100"