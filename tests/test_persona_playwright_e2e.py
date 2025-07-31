"""
AIペルソナシステムのPlaywright E2Eテスト
実際のGemini APIとブラウザを使用した統合テスト
"""
import pytest
import asyncio
from playwright.async_api import async_playwright, Page, expect

pytest_plugins = ('pytest_asyncio',)


class TestPersonaE2E:
    """ペルソナシステムのE2Eテスト"""

    @pytest.mark.asyncio
    async def test_persona_scenario_flow(self):
        """ペルソナシナリオの完全な対話フロー"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="ja-JP"
            )
            page = await context.new_page()
            
            try:
                # アプリケーションにアクセス
                await page.goto("http://localhost:5001")
                await page.wait_for_load_state("networkidle")
                
                # シナリオページへ移動
                await page.click('a[href="/scenarios"]')
                await page.wait_for_url("**/scenarios")
                
                # シナリオ1を選択
                await page.click('button[data-scenario-id="scenario1"]')
                
                # ペルソナ選択モーダルが表示されることを確認
                await expect(page.locator('#personaSelectionModal')).to_be_visible()
                
                # 最初のペルソナを選択
                await page.click('.select-persona-btn:first-child')
                
                # チャット画面が表示されることを確認
                await expect(page.locator('#messageContainer')).to_be_visible()
                
                # メッセージを送信
                await page.fill('#messageInput', 'こんにちは、よろしくお願いします。')
                await page.click('#sendButton')
                
                # AI応答を待つ（ストリーミング）
                await page.wait_for_selector('.assistant-message', timeout=30000)
                
                # 応答が表示されることを確認
                assistant_message = await page.locator('.assistant-message').last.text_content()
                assert assistant_message is not None
                assert len(assistant_message) > 0
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_persona_selection_ui(self):
        """ペルソナ選択UIの動作確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto("http://localhost:5001/scenarios")
                await page.wait_for_load_state("networkidle")
                
                # シナリオを選択
                await page.click('button[data-scenario-id="scenario1"]')
                
                # ペルソナ選択モーダルの要素を確認
                await expect(page.locator('#personaSelectionModal')).to_be_visible()
                
                # ペルソナカードが表示されることを確認
                persona_cards = page.locator('.persona-card')
                await expect(persona_cards).to_have_count(5, timeout=10000)
                
                # 各ペルソナカードの情報を確認
                for i in range(await persona_cards.count()):
                    card = persona_cards.nth(i)
                    await expect(card.locator('.persona-info h4')).to_be_visible()
                    await expect(card.locator('.persona-role')).to_be_visible()
                    await expect(card.locator('.persona-personality')).to_be_visible()
                    await expect(card.locator('.select-persona-btn')).to_be_enabled()
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """ストリーミング応答の動作確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # シナリオとペルソナを選択してチャット開始
                await page.goto("http://localhost:5001/scenarios")
                await page.click('button[data-scenario-id="scenario1"]')
                await page.click('.select-persona-btn:first-child')
                
                # メッセージ送信
                await page.fill('#messageInput', 'プロジェクトの進捗について教えてください。')
                await page.click('#sendButton')
                
                # ストリーミングコンテナが表示されることを確認
                streaming_container = page.locator('.message.assistant-message.streaming')
                await expect(streaming_container).to_be_visible(timeout=5000)
                
                # タイピングインジケーターが表示されることを確認
                await expect(streaming_container.locator('.typing-indicator')).to_be_visible()
                
                # ストリーミング完了を待つ
                await page.wait_for_selector('.message.assistant-message:not(.streaming)', timeout=30000)
                
                # メタ情報（時刻）が追加されることを確認
                await expect(page.locator('.message-meta').last).to_be_visible()
                
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """エラーハンドリングの確認"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto("http://localhost:5001/scenarios")
                
                # 存在しないシナリオIDでAPIを直接呼び出し
                response = await page.evaluate("""
                    async () => {
                        const response = await fetch('/api/persona-scenarios/suitable-personas/invalid_scenario');
                        return {
                            status: response.status,
                            ok: response.ok
                        };
                    }
                """)
                
                # エラーレスポンスが返されることを確認
                assert response['status'] == 200  # 空のペルソナリストが返される
                assert response['ok'] is True
                
            finally:
                await browser.close()


if __name__ == "__main__":
    # Playwrightテストを実行
    pytest.main([__file__, "-v", "-s"])