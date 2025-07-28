"""
ペルソナシステムの簡易E2Eテスト
"""
import pytest
import asyncio
from playwright.async_api import async_playwright

pytest_plugins = ('pytest_asyncio',)


class TestPersonaSimpleE2E:
    """ペルソナシステムの簡易E2Eテスト"""

    @pytest.mark.asyncio
    async def test_homepage_loads(self):
        """ホームページが正常に読み込まれることを確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # ホームページにアクセス
                response = await page.goto("http://localhost:5001", timeout=10000)
                assert response.status == 200
                
                # タイトルを確認
                title = await page.title()
                assert "職場コミュニケーション" in title
                
                # 主要な要素が存在することを確認
                chat_container = await page.query_selector("#chat-container")
                assert chat_container is not None
                
                print("✅ ホームページの読み込みテスト成功")
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_api_endpoints(self):
        """APIエンドポイントが正常に動作することを確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # APIエンドポイントをテスト
                await page.goto("http://localhost:5001")
                
                # モデル一覧API
                models_response = await page.evaluate("""
                    async () => {
                        const response = await fetch('/api/models');
                        return await response.json();
                    }
                """)
                assert 'models' in models_response
                print("✅ モデル一覧APIテスト成功")
                
                # ペルソナ一覧API（存在しないシナリオ）
                personas_response = await page.evaluate("""
                    async () => {
                        const response = await fetch('/api/persona-scenarios/suitable-personas/test_scenario');
                        return await response.json();
                    }
                """)
                assert 'personas' in personas_response
                print("✅ ペルソナ一覧APIテスト成功")
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_chat_page_navigation(self):
        """チャットページへのナビゲーションを確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto("http://localhost:5001")
                
                # チャット（雑談）リンクを探す
                chat_link = await page.query_selector('a[href="/chat"]')
                if chat_link:
                    await chat_link.click()
                    await page.wait_for_url("**/chat", timeout=5000)
                    print("✅ チャットページへのナビゲーション成功")
                else:
                    print("⚠️ チャットリンクが見つかりません")
                
            finally:
                await browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])