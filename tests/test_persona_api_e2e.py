"""
ペルソナAPI機能のPlaywright E2Eテスト
"""
import pytest
import asyncio
from playwright.async_api import async_playwright

pytest_plugins = ('pytest_asyncio',)


class TestPersonaAPIE2E:
    """ペルソナAPIのE2Eテスト"""

    @pytest.mark.asyncio
    async def test_persona_api_endpoints(self):
        """ペルソナ関連APIエンドポイントの動作確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto("http://localhost:5001")
                
                # 1. 適切なペルソナ取得API
                personas_response = await page.evaluate("""
                    async () => {
                        const response = await fetch('/api/persona-scenarios/suitable-personas/scenario1');
                        const data = await response.json();
                        return {
                            status: response.status,
                            data: data
                        };
                    }
                """)
                
                assert personas_response['status'] == 200
                assert 'personas' in personas_response['data']
                assert isinstance(personas_response['data']['personas'], list)
                print(f"✅ ペルソナ取得API成功 - {len(personas_response['data']['personas'])}個のペルソナ")
                
                # 2. ペルソナが存在する場合の詳細確認
                if personas_response['data']['personas']:
                    first_persona = personas_response['data']['personas'][0]
                    assert 'persona_code' in first_persona
                    assert 'name' in first_persona
                    assert 'industry' in first_persona
                    assert 'role' in first_persona
                    print(f"✅ ペルソナデータ構造確認 - {first_persona['name']}")
                
                # 3. 存在しないシナリオでのエラーハンドリング
                error_response = await page.evaluate("""
                    async () => {
                        const response = await fetch('/api/persona-scenarios/suitable-personas/invalid_scenario');
                        const data = await response.json();
                        return {
                            status: response.status,
                            data: data
                        };
                    }
                """)
                
                assert error_response['status'] == 200  # 空のリストが返される
                assert 'personas' in error_response['data']
                print("✅ エラーハンドリング確認")
                
                # 4. ペルソナ統計API（存在する場合）
                stats_response = await page.evaluate("""
                    async () => {
                        try {
                            const response = await fetch('/api/persona-scenarios/persona-stats/IT_MANAGER_ANALYTICAL');
                            const data = await response.json();
                            return {
                                status: response.status,
                                data: data
                            };
                        } catch (error) {
                            return {
                                status: 404,
                                error: error.message
                            };
                        }
                    }
                """)
                
                if stats_response['status'] == 200:
                    assert 'total_interactions' in stats_response['data']
                    print("✅ ペルソナ統計API確認")
                else:
                    print("⚠️ ペルソナ統計APIは未実装または未対応")
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_persona_data_integrity(self):
        """ペルソナデータの整合性確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto("http://localhost:5001")
                
                # シナリオ1〜5でペルソナを取得して整合性確認
                for scenario_id in range(1, 6):
                    response = await page.evaluate(f"""
                        async () => {{
                            const response = await fetch('/api/persona-scenarios/suitable-personas/scenario{scenario_id}');
                            return await response.json();
                        }}
                    """)
                    
                    if response['personas']:
                        for persona in response['personas']:
                            # 必須フィールドの確認
                            required_fields = ['persona_code', 'name', 'industry', 'role', 'personality_type']
                            for field in required_fields:
                                assert field in persona, f"シナリオ{scenario_id}のペルソナに{field}が不足"
                            
                            # データ型の確認
                            assert isinstance(persona['years_experience'], int), "years_experienceは整数である必要があります"
                            
                        print(f"✅ シナリオ{scenario_id}: {len(response['personas'])}個のペルソナデータ整合性確認")
                    else:
                        print(f"ℹ️ シナリオ{scenario_id}: ペルソナが設定されていません")
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """ペルソナAPIのパフォーマンステスト"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto("http://localhost:5001")
                
                # APIレスポンス時間の測定
                performance_results = await page.evaluate("""
                    async () => {
                        const results = [];
                        
                        for (let i = 1; i <= 5; i++) {
                            const startTime = performance.now();
                            const response = await fetch(`/api/persona-scenarios/suitable-personas/scenario${i}`);
                            const endTime = performance.now();
                            
                            results.push({
                                scenario: `scenario${i}`,
                                responseTime: endTime - startTime,
                                status: response.status
                            });
                        }
                        
                        return results;
                    }
                """)
                
                # パフォーマンス結果の確認
                for result in performance_results:
                    assert result['status'] == 200
                    assert result['responseTime'] < 5000, f"{result['scenario']}のAPIが5秒以上かかっています"
                    print(f"✅ {result['scenario']}: {result['responseTime']:.2f}ms")
                
                avg_response_time = sum(r['responseTime'] for r in performance_results) / len(performance_results)
                print(f"✅ 平均レスポンス時間: {avg_response_time:.2f}ms")
                
            finally:
                await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])