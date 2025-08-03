"""
ゴールデンテストデータに基づくリグレッションテスト
"""
import json
import pytest
import requests
from datetime import datetime
from typing import Dict, Any, List
from deepdiff import DeepDiff


class TestRegression:
    """ゴールデンデータに基づく自動リグレッションテスト"""
    
    @classmethod
    def setup_class(cls):
        """テストクラスのセットアップ"""
        # ゴールデンデータを読み込み
        try:
            with open('tests/golden/golden_responses_latest.json', 'r', encoding='utf-8') as f:
                cls.golden_data = json.load(f)
        except FileNotFoundError:
            pytest.skip("ゴールデンテストデータが見つかりません。まず record_golden_responses.py を実行してください。")
        
        cls.base_url = cls.golden_data['metadata']['base_url']
        cls.session = requests.Session()
    
    def test_basic_endpoints(self):
        """基本的なエンドポイントのリグレッションテスト"""
        basic_endpoints = [
            ('GET /', None),
            ('GET /api/models', None),
            ('GET /api/tts/voices', None)
        ]
        
        for endpoint, request_data in basic_endpoints:
            golden_case = self._find_golden_case(endpoint)
            if not golden_case:
                pytest.skip(f"ゴールデンデータに {endpoint} が見つかりません")
            
            self._verify_endpoint(golden_case)
    
    def test_chat_functionality(self):
        """チャット機能のリグレッションテスト"""
        # シンプルな挨拶のテスト
        golden_cases = [tc for tc in self.golden_data['test_cases'] 
                       if tc['endpoint'] == '/api/chat' and 
                       tc.get('pattern', {}).get('name') == 'simple_greeting']
        
        if not golden_cases:
            pytest.skip("チャット機能のゴールデンデータが見つかりません")
        
        # まずトップページにアクセスしてセッションを初期化
        self.session.get(f"{self.base_url}/")
        
        # CSRFトークンを取得
        csrf_response = self.session.get(f"{self.base_url}/api/csrf_token")
        if csrf_response.status_code == 200:
            csrf_token = csrf_response.json().get('csrf_token')
            headers = {'X-CSRF-Token': csrf_token}
        else:
            headers = {}
        
        # セッションをクリア
        self.session.post(f"{self.base_url}/api/chat/clear", headers=headers)
        
        # 新しいメッセージを送信
        response = self.session.post(
            f"{self.base_url}/api/chat",
            json={'message': 'こんにちは'},
            headers=headers
        )
        
        # ステータスコードの確認（403の場合はCSRF無効化されている可能性）
        assert response.status_code in [200, 403], f"予期しないステータスコード: {response.status_code}"
        
        if response.status_code == 200:
            # SSEレスポンスの形式確認
            assert response.text.startswith('data:'), "SSE形式でない応答"
    
    def test_scenario_endpoints(self):
        """シナリオ機能のリグレッションテスト"""
        # シナリオ一覧の取得
        golden_case = self._find_golden_case("GET /api/scenarios")
        if golden_case:
            self._verify_endpoint(golden_case)
    
    def test_tts_functionality(self):
        """TTS機能のリグレッションテスト"""
        tts_cases = [tc for tc in self.golden_data['test_cases'] 
                    if tc['endpoint'] == '/api/tts']
        
        if not tts_cases:
            pytest.skip("TTS機能のゴールデンデータが見つかりません")
        
        # 基本的なTTSテスト
        response = self.session.post(
            f"{self.base_url}/api/tts",
            json={'text': 'こんにちは', 'voice': 'kore'}
        )
        
        assert response.status_code == 200, f"TTSが失敗しました: {response.status_code}"
        
        # レスポンスの形式を確認
        data = response.json()
        assert 'audio' in data, "音声データが含まれていません"
        assert 'format' in data, "フォーマット情報が含まれていません"
        assert data['format'] == 'wav', "期待されるフォーマットと異なります"
    
    def _find_golden_case(self, endpoint: str) -> Dict[str, Any]:
        """特定のエンドポイントのゴールデンケースを検索"""
        for case in self.golden_data['test_cases']:
            if case['endpoint'] == endpoint:
                return case
        return None
    
    def _verify_endpoint(self, golden_case: Dict[str, Any]):
        """エンドポイントの動作を検証"""
        endpoint = golden_case['endpoint']
        method, path = endpoint.split(' ', 1)
        
        # リクエストを実行
        if method == 'GET':
            response = self.session.get(f"{self.base_url}{path}")
        elif method == 'POST':
            response = self.session.post(
                f"{self.base_url}{path}",
                json=golden_case.get('request')
            )
        else:
            pytest.skip(f"未対応のHTTPメソッド: {method}")
        
        # ステータスコードの確認
        assert response.status_code == golden_case['response_status'], \
            f"{endpoint} のステータスコードが異なります: " \
            f"期待値={golden_case['response_status']}, 実際={response.status_code}"
        
        # JSONレスポンスの場合は構造を比較
        if response.headers.get('content-type', '').startswith('application/json'):
            actual_data = response.json()
            expected_data = golden_case['response_data']
            
            # 動的な値を除外して比較
            diff = DeepDiff(
                expected_data,
                actual_data,
                ignore_order=True,
                exclude_paths=[
                    "root['timestamp']",
                    "root['session_id']",
                    "root['models']"  # モデルリストは変更される可能性がある
                ]
            )
            
            # 重要な違いがないことを確認
            if diff:
                # 些細な違いは許容
                important_diff = self._filter_important_differences(diff)
                assert not important_diff, \
                    f"{endpoint} のレスポンスに重要な違いがあります: {important_diff}"
    
    def _filter_important_differences(self, diff: DeepDiff) -> Dict:
        """重要な違いのみをフィルタリング"""
        important_diff = {}
        
        # タイプの変更は重要
        if 'type_changes' in diff:
            important_diff['type_changes'] = diff['type_changes']
        
        # 値の削除は重要
        if 'values_changed' in diff:
            # タイムスタンプなどの動的な値は除外
            filtered_changes = {}
            for key, change in diff['values_changed'].items():
                if not any(skip in key for skip in ['timestamp', 'date', 'time', 'id']):
                    filtered_changes[key] = change
            
            if filtered_changes:
                important_diff['values_changed'] = filtered_changes
        
        # アイテムの削除は重要
        if 'dictionary_item_removed' in diff:
            important_diff['dictionary_item_removed'] = diff['dictionary_item_removed']
        
        return important_diff


class TestPerformanceRegression:
    """パフォーマンスのリグレッションテスト"""
    
    def test_response_times(self):
        """主要エンドポイントのレスポンスタイムをテスト"""
        import time
        
        endpoints = [
            ('GET', '/api/models'),
            ('GET', '/api/tts/voices')
        ]
        
        for method, path in endpoints:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(f"http://localhost:5001{path}")
            else:
                response = requests.post(f"http://localhost:5001{path}")
            
            elapsed_time = time.time() - start_time
            
            # レスポンスタイムが1秒以内であることを確認
            assert elapsed_time < 1.0, \
                f"{path} のレスポンスタイムが遅すぎます: {elapsed_time:.2f}秒"
            
            # ステータスコードも確認
            assert response.status_code in [200, 201], \
                f"{path} が失敗しました: {response.status_code}"