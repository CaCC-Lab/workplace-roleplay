"""
AIチャット機能の動作確認テスト
Playwrightを使用してシナリオページでAIが応答するか確認
"""
import asyncio
from playwright.async_api import async_playwright
import time
import json

async def test_ai_chat():
    async with async_playwright() as p:
        # ブラウザを起動（ヘッドレスモードをオフにして確認）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # コンソールログを記録
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        
        # エラーを記録
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        
        try:
            print("1. トップページにアクセス")
            await page.goto("http://localhost:5001")
            await page.wait_for_load_state("networkidle")
            
            # モデルを選択
            print("2. Geminiモデルを選択")
            # ラジオボタンを見つけてクリック
            model_selector = 'input[type="radio"][value="gemini/gemini-1.5-flash"]'
            try:
                await page.wait_for_selector(model_selector, timeout=5000)
                await page.click(model_selector)
            except:
                # 別の方法でモデルを選択
                print("  モデル選択エレメントが見つからない場合の代替処理")
                pass
            await page.wait_for_timeout(500)
            
            # LocalStorageにモデルを保存
            await page.evaluate("""
                localStorage.setItem('selectedModel', 'gemini/gemini-1.5-flash');
            """)
            
            print("3. シナリオ一覧ページへ移動")
            await page.click('a[href="/scenarios"]')
            await page.wait_for_load_state("networkidle")
            
            # シナリオが表示されるまで待つ
            await page.wait_for_selector('.scenario-card', timeout=10000)
            
            print("4. 最初のシナリオをクリック")
            # シナリオカード内のリンクを探してクリック
            scenario_link = await page.query_selector('.scenario-card a')
            if scenario_link:
                href = await scenario_link.get_attribute('href')
                print(f"  シナリオリンク: {href}")
                await scenario_link.click()
            else:
                # 代替方法：カード自体をクリック
                await page.click('.scenario-card:first-child')
            
            # ページ遷移を待つ（少し待機時間を追加）
            await page.wait_for_timeout(2000)
            print(f"  遷移先URL: {page.url}")
            
            await page.wait_for_load_state("networkidle")
            
            # ページの内容を確認
            title = await page.title()
            print(f"  ページタイトル: {title}")
            
            # チャットメッセージエリアが表示されるまで待つ
            try:
                await page.wait_for_selector('#chat-messages', timeout=10000)
            except:
                print("  #chat-messagesが見つかりません。ページの内容を確認します。")
                # ページのHTML構造を確認
                body_text = await page.evaluate("document.body.innerText")
                print(f"  ページの内容（最初の200文字）: {body_text[:200]}")
                
                # スクリーンショットを保存
                await page.screenshot(path="scenario_page_error.png")
                print("  scenario_page_error.png にスクリーンショットを保存しました")
                raise
            
            print("5. 初期メッセージを待つ（最大30秒）")
            start_time = time.time()
            initial_message_found = False
            
            while time.time() - start_time < 30:
                messages = await page.query_selector_all('.message.bot-message')
                if messages:
                    initial_message_found = True
                    first_message_text = await messages[0].text_content()
                    print(f"✓ 初期メッセージを受信: {first_message_text[:50]}...")
                    break
                await page.wait_for_timeout(1000)
            
            if not initial_message_found:
                print("✗ 初期メッセージが表示されませんでした")
                
                # APIエンドポイントを直接テスト
                print("\n6. APIエンドポイントを直接テスト")
                api_response = await page.evaluate("""
                    async () => {
                        try {
                            const response = await fetch('/api/async/scenario/stream', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': window.csrfManager?.getToken() || ''
                                },
                                body: JSON.stringify({
                                    message: '',
                                    model: 'gemini/gemini-1.5-flash',
                                    scenario_id: 'scenario1',
                                    is_initial: true
                                })
                            });
                            
                            return {
                                status: response.status,
                                statusText: response.statusText,
                                headers: Object.fromEntries(response.headers.entries()),
                                body: await response.text()
                            };
                        } catch (err) {
                            return { error: err.toString() };
                        }
                    }
                """)
                
                print(f"API Response: {json.dumps(api_response, indent=2)}")
            
            else:
                # ユーザーメッセージを送信
                print("\n6. ユーザーメッセージを送信")
                await page.fill('#message-input', 'こんにちは')
                await page.click('#send-button')
                
                print("7. AI応答を待つ（最大30秒）")
                start_time = time.time()
                response_found = False
                
                while time.time() - start_time < 30:
                    messages = await page.query_selector_all('.message.bot-message')
                    if len(messages) > 1:  # 初期メッセージ + 新しい応答
                        response_found = True
                        response_text = await messages[-1].text_content()
                        print(f"✓ AI応答を受信: {response_text[:50]}...")
                        break
                    await page.wait_for_timeout(1000)
                
                if not response_found:
                    print("✗ AI応答が表示されませんでした")
            
            # コンソールログとエラーを表示
            if console_logs:
                print("\n=== ブラウザコンソールログ ===")
                for log in console_logs[-10:]:  # 最後の10件
                    print(log)
            
            if page_errors:
                print("\n=== ページエラー ===")
                for error in page_errors:
                    print(error)
            
            # ネットワークエラーを確認
            print("\n=== ネットワークリクエストの確認 ===")
            await page.evaluate("""
                () => {
                    const entries = performance.getEntriesByType('resource');
                    entries.forEach(entry => {
                        if (entry.name.includes('/api/') && entry.name.includes('scenario')) {
                            console.log(`${entry.name}: ${entry.responseEnd - entry.startTime}ms`);
                        }
                    });
                }
            """)
            
            await page.wait_for_timeout(3000)
            
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            
            # スクリーンショットを保存
            await page.screenshot(path="error_screenshot.png")
            print("エラー時のスクリーンショットを error_screenshot.png に保存しました")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ai_chat())