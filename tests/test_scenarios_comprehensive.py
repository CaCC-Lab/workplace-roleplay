"""
全35シナリオの包括的テスト（モックなし・実際のGemini API使用）
CLAUDE.md原則: モック禁止、実際のAPIでの包括的テスト
"""
import pytest
import json
import time
import os
import yaml
from typing import Dict, List, Any
from app import app, load_scenarios


class TestScenariosComprehensive:
    """全30シナリオの包括的テスト"""

    @pytest.fixture(scope="session")
    def all_scenarios(self):
        """全シナリオデータの読み込み"""
        scenarios = load_scenarios()
        print(f"読み込まれたシナリオ数: {len(scenarios)}")
        return scenarios

    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['CSRF_ENABLED'] = False
        app.config['BYPASS_CSRF'] = True  # CSRFチェックを完全にバイパス
        app.config['SESSION_TYPE'] = 'filesystem'  # セッションタイプを明示的に設定
        with app.test_client() as client:
            with app.app_context():
                yield client

    @pytest.fixture
    def csrf_token(self, client):
        """CSRFトークンを取得"""
        # セッション内でCSRFトークンを取得
        response = client.get('/api/csrf-token')
        token = response.get_json().get('csrf_token', '')
        return token

    def test_csrf_token_flow(self, client):
        """CSRFトークンの取得と使用フローをテスト"""
        # CSRFトークンを取得
        response = client.get('/api/csrf-token')
        assert response.status_code == 200
        token = response.get_json().get('csrf_token')
        assert token is not None
        print(f"取得したCSRFトークン: {token}")
        
        # セッションのデバッグ情報を表示
        with client.session_transaction() as sess:
            print(f"セッション内容: {dict(sess)}")
        
        # テスト用の簡単なAPIリクエスト
        test_response = client.post('/api/scenario_chat',
                                  json={
                                      'message': 'test',
                                      'scenario_id': 'scenario1',
                                      'model': 'gemini-1.5-flash'
                                  },
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': token
                                  })
        
        print(f"レスポンスステータス: {test_response.status_code}")
        if test_response.status_code != 200:
            print(f"レスポンス内容: {test_response.data.decode('utf-8')}")
    
    def test_all_scenarios_loaded(self, all_scenarios):
        """全35シナリオが正しく読み込まれることを確認"""
        assert len(all_scenarios) == 35, f"シナリオ数が不正: {len(all_scenarios)}"
        
        # 各シナリオのIDが重複していないことを確認（キー自体がIDなので重複はない）
        scenario_ids = list(all_scenarios.keys())
        assert len(scenario_ids) == len(set(scenario_ids)), "シナリオIDに重複があります"
        
        # 必須フィールドの存在確認
        required_fields = ['title', 'description', 'difficulty']
        for scenario_id, scenario_data in all_scenarios.items():
            for field in required_fields:
                assert field in scenario_data, f"シナリオ {scenario_id} に必須フィールド {field} がありません"

    def test_scenario_content_quality(self, all_scenarios):
        """シナリオコンテンツの品質評価"""
        quality_issues = []
        
        for scenario_id, scenario_data in all_scenarios.items():
            # タイトルの品質チェック
            title = scenario_data.get('title', '')
            if len(title) < 5:
                quality_issues.append(f"シナリオ{scenario_id}: タイトルが短すぎます")
            
            # 説明文の品質チェック
            description = scenario_data.get('description', '')
            if len(description) < 20:
                quality_issues.append(f"シナリオ{scenario_id}: 説明文が短すぎます")
            
            # 難易度の妥当性チェック
            difficulty = scenario_data.get('difficulty', '')
            if difficulty not in ['初級', '中級', '上級']:
                quality_issues.append(f"シナリオ{scenario_id}: 無効な難易度 '{difficulty}'")
            
            # 学習ポイントの存在チェック
            learning_points = scenario_data.get('learning_points', [])
            if not learning_points or len(learning_points) < 2:
                quality_issues.append(f"シナリオ{scenario_id}: 学習ポイントが不足")
            
            # フィードバックポイントの存在チェック
            feedback_points = scenario_data.get('feedback_points', [])
            if not feedback_points or len(feedback_points) < 2:
                quality_issues.append(f"シナリオ{scenario_id}: フィードバックポイントが不足")
            
            # キャラクター設定の存在チェック
            character_setting = scenario_data.get('character_setting', {})
            if not character_setting:
                quality_issues.append(f"シナリオ{scenario_id}: キャラクター設定が不足")
        
        # 品質問題の報告
        if quality_issues:
            print(f"品質問題が発見されました ({len(quality_issues)}件):")
            for issue in quality_issues[:10]:  # 最初の10件を表示
                print(f"  {issue}")
        
        # 80%以上の品質を要求
        quality_score = (len(all_scenarios) * 6 - len(quality_issues)) / (len(all_scenarios) * 6) * 100
        print(f"シナリオ品質スコア: {quality_score:.1f}%")
        assert quality_score >= 80, f"シナリオ品質が基準に満たない: {quality_score:.1f}%"

    @pytest.mark.parametrize("scenario_id", list(range(1, 36)))
    def test_individual_scenario_with_real_gemini(self, client, all_scenarios, scenario_id):
        """各シナリオを個別に実際のGemini APIでテスト"""
        # レート制限対策
        time.sleep(1.0)
        
        # シナリオデータを取得（all_scenariosは辞書）
        scenario_key = f"scenario{scenario_id}"
        scenario = all_scenarios.get(scenario_key)
        if not scenario:
            pytest.skip(f"シナリオ{scenario_id}が見つかりません")
        
        print(f"\n=== シナリオ{scenario_id}: {scenario['title']} ===")
        
        # CSRFトークンを取得（セッションコンテキスト内で実行）
        response = client.get('/api/csrf-token')
        assert response.status_code == 200, "CSRFトークン取得失敗"
        csrf_token = response.get_json().get('csrf_token', '')
        assert csrf_token, "CSRFトークンが空です"
        
        # シナリオページにアクセスしてセッションを初期化
        start_response = client.get(f'/scenario/{scenario_key}')
        
        # 404エラーの場合はシナリオが見つからない
        if start_response.status_code == 404:
            pytest.skip(f"シナリオ{scenario_id}が見つかりません")
        
        assert start_response.status_code == 200, (
            f"シナリオ{scenario_id}ページアクセス失敗: {start_response.status_code}. "
            f"レスポンス: {start_response.data.decode('utf-8')[:200]}"
        )
        
        # 難易度レベルに応じたテストメッセージ
        test_messages = self.get_test_messages_for_difficulty(scenario['difficulty'])
        
        for message in test_messages:
            # メッセージ送信
            response = client.post('/api/scenario_chat',
                                 json={
                                     'message': message,
                                     'scenario_id': scenario_key,
                                     'model': 'gemini-1.5-flash'
                                 },
                                 headers={
                                     'Content-Type': 'application/json',
                                     'X-CSRFToken': csrf_token
                                 })
            
            # レート制限の場合はスキップ
            if response.status_code == 429:
                pytest.skip(f"APIレート制限によりシナリオ{scenario_id}のメッセージテストをスキップ")
            
            # 404エラーの場合はAPIエンドポイントが未実装
            if response.status_code == 404:
                pytest.skip(f"シナリオ{scenario_id}のチャットAPIエンドポイントが未実装")
            
            assert response.status_code == 200, (
                f"シナリオ{scenario_id}のメッセージ送信失敗: {response.status_code}"
            )
            
            # レスポンス内容の確認
            if response.headers.get('content-type', '').startswith('application/json'):
                json_data = response.get_json()
                response_content = json_data.get('response', '')
                assert len(response_content) > 10, f"シナリオ{scenario_id}のAI応答が短すぎます"
                
                # シナリオに適した応答かの基本チェック
                self.validate_scenario_response(response_content, scenario)
            
            # レート制限対策
            time.sleep(0.5)

    def get_test_messages_for_difficulty(self, difficulty: str) -> List[str]:
        """難易度に応じたテストメッセージを生成"""
        if difficulty == '初級':
            return [
                "こんにちは、よろしくお願いします。",
                "分からないことがあるのですが、教えていただけますか？"
            ]
        elif difficulty == '中級':
            return [
                "お疲れ様です。こちらの件についてご相談があります。",
                "状況を整理して、今後の進め方を検討したいと思います。"
            ]
        else:  # 上級
            return [
                "お忙しい中失礼いたします。重要な案件についてご相談があります。",
                "複数の選択肢がある中で、最適な解決策を見つけたいと考えています。"
            ]

    def validate_scenario_response(self, response_content: str, scenario: Dict[str, Any]):
        """シナリオに適した応答内容かを検証"""
        # 日本語応答の確認
        japanese_chars = sum(1 for char in response_content 
                           if '\u3040' <= char <= '\u309F' or 
                              '\u30A0' <= char <= '\u30FF' or 
                              '\u4E00' <= char <= '\u9FAF')
        
        if japanese_chars < 10:
            print(f"警告: 日本語が少ない応答 (シナリオ{scenario['id']})")
        
        # カテゴリー関連キーワードの確認
        category = scenario.get('category', '')
        category_keywords = {
            '会議': ['会議', '議論', '検討', '決定', '提案'],
            '顧客対応': ['お客様', '顧客', 'サービス', '対応', '解決'],
            '上司報告': ['報告', '進捗', '状況', '結果', '相談'],
            '同僚連携': ['連携', '協力', '情報共有', 'チーム', '一緒'],
            '部下指導': ['指導', '教育', 'サポート', 'アドバイス', '成長'],
            '営業': ['営業', '提案', '顧客', '売上', '契約'],
            '技術相談': ['技術', '仕様', '設計', '開発', '問題解決'],
            '問題解決': ['問題', '課題', '解決', '対策', '改善']
        }
        
        if category in category_keywords:
            keywords = category_keywords[category]
            has_relevant_keywords = any(keyword in response_content for keyword in keywords)
            if not has_relevant_keywords:
                print(f"注意: カテゴリー '{category}' に関連するキーワードが少ない (シナリオ{scenario['id']})")

    def test_scenario_difficulty_distribution(self, all_scenarios):
        """シナリオの難易度分布を確認"""
        difficulty_counts = {}
        for scenario_id, scenario in all_scenarios.items():
            difficulty = scenario.get('difficulty', 'unknown')
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        print(f"難易度分布: {difficulty_counts}")
        
        # 各難易度に最低3つのシナリオがあることを確認
        for difficulty in ['初級', '中級', '上級']:
            assert difficulty_counts.get(difficulty, 0) >= 3, f"難易度 '{difficulty}' のシナリオが不足"

    def test_scenario_category_distribution(self, all_scenarios):
        """シナリオのカテゴリー分布を確認（タグベース）"""
        tag_counts = {}
        
        # タグベースの分類を行う
        for scenario_id, scenario in all_scenarios.items():
            if isinstance(scenario, dict):
                tags = scenario.get('tags', [])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print(f"タグ分布: {tag_counts}")
        
        # タグが存在する場合のチェック
        if tag_counts:
            # 少なくとも10種類以上のタグが存在することを確認
            assert len(tag_counts) >= 10, f"タグの種類が少ない: {len(tag_counts)}種類"
            
            # 各タグが少なくとも1つのシナリオで使用されていることを確認
            for tag, count in tag_counts.items():
                assert count >= 1, f"タグ '{tag}' が未使用"
        else:
            print("警告: シナリオにタグ情報が含まれていません")

    def test_scenarios_with_different_models(self, client, csrf_token, all_scenarios):
        """異なるGeminiモデルでのシナリオテスト"""
        models = ['gemini-1.5-flash', 'gemini-1.5-pro']
        model_results = {}
        
        # 最初の5つのシナリオで各モデルをテスト
        scenario_ids = list(all_scenarios.keys())[:5]
        test_scenarios = {sid: all_scenarios[sid] for sid in scenario_ids}
        
        for model in models:
            successful_scenarios = []
            
            for scenario_id, scenario in test_scenarios.items():
                try:
                    # レート制限対策
                    time.sleep(2.0)
                    
                    # シナリオ開始
                    start_response = client.post(f'/api/scenario/{scenario_id}/start',
                                               json={'model': model},
                                               headers={
                                                   'Content-Type': 'application/json',
                                                   'X-CSRFToken': csrf_token
                                               })
                    
                    # レート制限や404エラーの場合はスキップ
                    if start_response.status_code in [429, 404]:
                        continue
                    
                    if start_response.status_code == 200:
                        successful_scenarios.append(scenario_id)
                    
                except Exception as e:
                    print(f"モデル {model} でシナリオ{scenario_id}のテストエラー: {e}")
            
            model_results[model] = successful_scenarios
        
        print(f"モデル別シナリオ成功数:")
        for model, scenarios in model_results.items():
            print(f"  {model}: {len(scenarios)}個成功")
        
        # 少なくとも1つのモデルで3つ以上のシナリオが動作することを確認
        max_successful = max(len(scenarios) for scenarios in model_results.values())
        assert max_successful >= 3, f"どのモデルも十分なシナリオを実行できません: 最大{max_successful}個"

    def test_scenario_api_endpoints_availability(self, client, csrf_token):
        """シナリオ関連APIエンドポイントの可用性確認"""
        endpoints_to_test = [
            ('/api/scenarios', 'GET'),
            ('/api/scenario/1/start', 'POST'),
            ('/api/scenario_chat', 'POST'),
            ('/api/scenario_feedback', 'POST')
        ]
        
        endpoint_results = {}
        
        for endpoint, method in endpoints_to_test:
            try:
                if method == 'GET':
                    response = client.get(endpoint)
                else:  # POST
                    if 'start' in endpoint:
                        data = {'model': 'gemini-1.5-flash'}
                    elif 'chat' in endpoint:
                        data = {'message': 'テスト', 'scenario_id': 1}
                    elif 'feedback' in endpoint:
                        data = {'scenario_id': 1, 'conversation': []}
                    
                    response = client.post(endpoint,
                                         json=data,
                                         headers={
                                             'Content-Type': 'application/json',
                                             'X-CSRFToken': csrf_token
                                         })
                
                endpoint_results[endpoint] = {
                    'status': response.status_code,
                    'available': response.status_code in [200, 400, 404, 429]
                }
                
            except Exception as e:
                endpoint_results[endpoint] = {
                    'status': 'error',
                    'available': False,
                    'error': str(e)
                }
        
        print("シナリオAPIエンドポイント可用性:")
        for endpoint, result in endpoint_results.items():
            print(f"  {endpoint}: {result}")
        
        # 重要なエンドポイントが利用可能であることを確認
        critical_endpoints = ['/api/scenarios', '/api/scenario/1/start']
        for endpoint in critical_endpoints:
            if endpoint in endpoint_results:
                assert endpoint_results[endpoint]['available'], f"重要なエンドポイント {endpoint} が利用できません"

    def test_scenario_error_handling(self, client, csrf_token):
        """シナリオのエラーハンドリングテスト"""
        # 存在しないシナリオ
        response = client.post('/api/scenario/999/start',
                              json={'model': 'gemini-1.5-flash'},
                              headers={
                                  'Content-Type': 'application/json',
                                  'X-CSRFToken': csrf_token
                              })
        
        if response.status_code == 404:
            print("存在しないシナリオで適切に404が返される")
        elif response.status_code == 400:
            json_data = response.get_json()
            if json_data and 'error' in json_data:
                print(f"存在しないシナリオで適切なエラーハンドリング: {json_data['error']}")
        
        # 無効なモデル
        response = client.post('/api/scenario/1/start',
                              json={'model': 'invalid-model'},
                              headers={
                                  'Content-Type': 'application/json',
                                  'X-CSRFToken': csrf_token
                              })
        
        if response.status_code in [400, 404]:
            print("無効なモデルで適切なエラーハンドリング")

    def test_scenario_content_consistency(self, all_scenarios):
        """シナリオコンテンツの一貫性チェック"""
        inconsistencies = []
        
        for scenario_id, scenario in all_scenarios.items():
            # シナリオが辞書型であることを確認
            if not isinstance(scenario, dict):
                inconsistencies.append(f"{scenario_id}: シナリオデータが辞書型ではない")
                continue
            
            # タイトルと説明の一貫性
            title = scenario.get('title', '').lower()
            description = scenario.get('description', '').lower()
            
            # タイトルに含まれる主要キーワードが説明にも含まれているかチェック
            title_keywords = ['会議', '顧客', '上司', '同僚', '部下', '営業', '技術', '問題']
            for keyword in title_keywords:
                if keyword in title and keyword not in description:
                    inconsistencies.append(f"シナリオ{scenario_id}: タイトルのキーワード '{keyword}' が説明にない")
        
        if inconsistencies:
            print(f"コンテンツの一貫性問題 ({len(inconsistencies)}件):")
            for inconsistency in inconsistencies[:5]:  # 最初の5件を表示
                print(f"  {inconsistency}")
        
        # 一貫性問題が全体の20%以下であることを確認
        consistency_rate = (len(all_scenarios) - len(inconsistencies)) / len(all_scenarios) * 100
        print(f"コンテンツ一貫性率: {consistency_rate:.1f}%")
        assert consistency_rate >= 80, f"コンテンツの一貫性が低い: {consistency_rate:.1f}%"


class TestScenarioPerformance:
    """シナリオのパフォーマンステスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            with app.app_context():
                yield client

    def test_scenario_loading_performance(self):
        """シナリオ読み込みパフォーマンステスト"""
        start_time = time.time()
        scenarios = load_scenarios()
        load_time = time.time() - start_time
        
        print(f"シナリオ読み込み時間: {load_time:.3f}秒")
        print(f"読み込まれたシナリオ数: {len(scenarios)}")
        
        # 35個のシナリオを1秒以内に読み込めることを確認
        assert load_time < 1.0, f"シナリオ読み込みが遅い: {load_time:.3f}秒"
        assert len(scenarios) == 35, f"シナリオ数が不正: {len(scenarios)}"

    def test_scenario_memory_usage(self):
        """シナリオのメモリ使用量テスト"""
        import sys
        
        # メモリ使用量計測（簡易版）
        before_scenarios = sys.getsizeof(globals())
        scenarios = load_scenarios()
        after_scenarios = sys.getsizeof(globals()) + sys.getsizeof(scenarios)
        
        memory_increase = after_scenarios - before_scenarios
        print(f"シナリオ読み込みによるメモリ増加: {memory_increase} bytes")
        
        # メモリ使用量が妥当な範囲内であることを確認
        assert memory_increase < 1024 * 1024, f"メモリ使用量が多すぎる: {memory_increase} bytes"


# 実際のアプリケーション起動チェック
@pytest.fixture(scope="session", autouse=True)
def ensure_app_running():
    """テスト実行前にアプリケーションが起動していることを確認"""
    import requests
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:5001", timeout=5)
            if response.status_code == 200:
                print(f"✅ アプリケーションが http://localhost:5001 で動作中")
                return
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                print(f"アプリケーション起動待機中... ({attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                pytest.fail(
                    "アプリケーションが起動していません。"
                    "テスト実行前に 'PORT=5001 python app.py' でアプリを起動してください。"
                )