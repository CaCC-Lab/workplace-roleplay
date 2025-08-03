"""
現在のアプリケーションの動作を記録してゴールデンテストデータを作成
"""
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any
import requests
import sys
import os

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class GoldenTestRecorder:
    """現在の動作を「正解」として記録"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_cases = []
        
    def record_all_endpoints(self):
        """全エンドポイントの動作を記録"""
        print("ゴールデンテストの記録を開始します...")
        
        # 1. 基本的なエンドポイント
        self.record_basic_endpoints()
        
        # 2. チャット機能
        self.record_chat_scenarios()
        
        # 3. シナリオ機能
        self.record_scenario_flows()
        
        # 4. 観戦モード
        self.record_watch_mode()
        
        # 5. TTS機能
        self.record_tts_functionality()
        
        # 結果を保存
        self.save_golden_data()
        
    def record_basic_endpoints(self):
        """基本的なエンドポイントのテスト"""
        print("\n1. 基本的なエンドポイントをテスト中...")
        
        # ヘルスチェック
        response = self.session.get(f"{self.base_url}/")
        self.record_test_case("GET /", None, response)
        
        # モデル一覧
        response = self.session.get(f"{self.base_url}/api/models")
        self.record_test_case("GET /api/models", None, response)
        
        # 音声一覧
        response = self.session.get(f"{self.base_url}/api/tts/voices")
        self.record_test_case("GET /api/tts/voices", None, response)
        
    def record_chat_scenarios(self):
        """チャット機能の様々なパターンを記録"""
        print("\n2. チャット機能をテスト中...")
        
        test_patterns = [
            {
                'name': 'simple_greeting',
                'messages': ['こんにちは'],
                'description': 'シンプルな挨拶'
            },
            {
                'name': 'multi_turn_conversation',
                'messages': [
                    'こんにちは',
                    '今日の天気はどうですか？',
                    'ありがとうございます'
                ],
                'description': '複数ターンの会話'
            },
            {
                'name': 'long_message',
                'messages': [
                    'これは長いメッセージのテストです。' * 50
                ],
                'description': '長いメッセージ'
            }
        ]
        
        for pattern in test_patterns:
            print(f"  - {pattern['description']}をテスト中...")
            
            # セッションをクリア
            self.session.post(f"{self.base_url}/api/chat/clear")
            
            # 各メッセージを送信
            conversation_flow = []
            for message in pattern['messages']:
                request_data = {'message': message}
                response = self.session.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                )
                
                # SSEレスポンスの最初の部分だけ記録
                response_preview = response.text[:500] if response.text else ""
                
                conversation_flow.append({
                    'request': request_data,
                    'response_status': response.status_code,
                    'response_preview': response_preview,
                    'headers': dict(response.headers)
                })
                
                time.sleep(0.5)  # レート制限を避ける
            
            self.test_cases.append({
                'endpoint': '/api/chat',
                'pattern': pattern,
                'conversation_flow': conversation_flow,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def record_scenario_flows(self):
        """シナリオ機能のテスト"""
        print("\n3. シナリオ機能をテスト中...")
        
        # シナリオ一覧を取得
        response = self.session.get(f"{self.base_url}/api/scenarios")
        self.record_test_case("GET /api/scenarios", None, response)
        
        if response.status_code == 200:
            scenarios = response.json().get('scenarios', [])
            if scenarios:
                # 最初のシナリオでテスト
                test_scenario = scenarios[0]
                print(f"  - シナリオ '{test_scenario.get('title', 'Unknown')}'をテスト中...")
                
                # シナリオ開始
                request_data = {'scenario_id': test_scenario['id']}
                response = self.session.post(
                    f"{self.base_url}/api/scenario/start",
                    json=request_data
                )
                self.record_test_case("POST /api/scenario/start", request_data, response)
                
                # シナリオメッセージ
                if response.status_code == 200:
                    request_data = {
                        'scenario_id': test_scenario['id'],
                        'message': 'はい、わかりました'
                    }
                    response = self.session.post(
                        f"{self.base_url}/api/scenario/message",
                        json=request_data
                    )
                    self.record_test_case("POST /api/scenario/message", request_data, response)
    
    def record_watch_mode(self):
        """観戦モードのテスト"""
        print("\n4. 観戦モードをテスト中...")
        
        # 観戦開始
        request_data = {
            'theme': '新人研修での質問',
            'personas': {
                'A': 'gemini-1.5-flash',
                'B': 'gemini-1.5-pro'
            }
        }
        response = self.session.post(
            f"{self.base_url}/api/watch/start",
            json=request_data
        )
        self.record_test_case("POST /api/watch/start", request_data, response)
        
        # 次の会話
        if response.status_code == 200:
            response = self.session.post(f"{self.base_url}/api/watch/next")
            self.record_test_case("POST /api/watch/next", None, response)
    
    def record_tts_functionality(self):
        """TTS機能のテスト"""
        print("\n5. TTS機能をテスト中...")
        
        test_cases = [
            {
                'text': 'こんにちは',
                'voice': 'kore',
                'description': '基本的なTTS'
            },
            {
                'text': 'これはテストです',
                'voice': 'charon',
                'emotion': 'happy',
                'description': '感情付きTTS'
            }
        ]
        
        for test_case in test_cases:
            print(f"  - {test_case['description']}をテスト中...")
            request_data = {k: v for k, v in test_case.items() if k != 'description'}
            
            response = self.session.post(
                f"{self.base_url}/api/tts",
                json=request_data
            )
            
            # 音声データは大きいので、メタデータのみ記録
            if response.status_code == 200:
                response_data = response.json()
                response_data['audio'] = f"<{len(response_data.get('audio', ''))} characters>"
            else:
                response_data = response.text
            
            self.test_cases.append({
                'endpoint': '/api/tts',
                'test_case': test_case,
                'request': request_data,
                'response_status': response.status_code,
                'response_data': response_data,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def record_test_case(self, endpoint: str, request_data: Any, response: requests.Response):
        """テストケースを記録"""
        response_data = None
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
            else:
                response_data = response.text[:1000]  # 最初の1000文字まで
        except:
            response_data = response.text[:1000] if response.text else None
        
        self.test_cases.append({
            'endpoint': endpoint,
            'request': request_data,
            'response_status': response.status_code,
            'response_data': response_data,
            'response_headers': dict(response.headers),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def save_golden_data(self):
        """ゴールデンデータを保存"""
        filename = f'tests/golden/golden_responses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        golden_data = {
            'metadata': {
                'recorded_at': datetime.utcnow().isoformat(),
                'base_url': self.base_url,
                'total_tests': len(self.test_cases)
            },
            'test_cases': self.test_cases
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(golden_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ ゴールデンテストデータを保存しました: {filename}")
        print(f"   記録されたテストケース数: {len(self.test_cases)}")
        
        # 最新版へのシンボリックリンクも作成
        latest_link = 'tests/golden/golden_responses_latest.json'
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(os.path.basename(filename), latest_link)
        print(f"   最新版リンク: {latest_link}")


def main():
    """メイン関数"""
    print("="*50)
    print("Workplace Roleplay ゴールデンテスト記録ツール")
    print("="*50)
    
    # アプリケーションが起動しているか確認
    try:
        response = requests.get("http://localhost:5001/")
        if response.status_code != 200:
            print("❌ エラー: アプリケーションが起動していません")
            print("   まず 'python app.py' でアプリケーションを起動してください")
            return
    except requests.exceptions.ConnectionError:
        print("❌ エラー: localhost:5001に接続できません")
        print("   まず 'python app.py' でアプリケーションを起動してください")
        return
    
    # ゴールデンテストを記録
    recorder = GoldenTestRecorder()
    recorder.record_all_endpoints()


if __name__ == "__main__":
    main()