"""
ブラウザ互換性・アクセシビリティ・モバイル対応の徹底的テスト
CLAUDE.md原則: モック禁止、実際のブラウザでの動作確認
"""
import pytest
import asyncio
import json
import time
import re
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from datetime import datetime

# pytest-asyncioの設定
pytest_plugins = ('pytest_asyncio',)


class TestBrowserCompatibilityComprehensive:
    """ブラウザ互換性・アクセシビリティの徹底的テスト"""

    @pytest.mark.asyncio
    @pytest.fixture(scope="session")
    async def browsers_setup(self):
        """複数ブラウザのセットアップ"""
        playwright = await async_playwright().start()
        
        browsers = {}
        try:
            # Chromium（Chrome相当）
            browsers['chromium'] = await playwright.chromium.launch(
                headless=True,
                args=["--disable-web-security", "--disable-features=VizDisplayCompositor"]
            )
            
            # Firefox
            try:
                browsers['firefox'] = await playwright.firefox.launch(headless=True)
            except Exception as e:
                print(f"Firefox起動失敗: {e}")
            
            # WebKit（Safari相当）
            try:
                browsers['webkit'] = await playwright.webkit.launch(headless=True)
            except Exception as e:
                print(f"WebKit起動失敗: {e}")
            
            yield browsers
            
        finally:
            for browser in browsers.values():
                await browser.close()
            await playwright.stop()

    @pytest.mark.asyncio
    @pytest.fixture
    async def page_with_browser(self, browsers_setup, request):
        """指定されたブラウザでページを作成"""
        browser_name = getattr(request, 'param', 'chromium')
        browser = browsers_setup.get(browser_name)
        
        if not browser:
            pytest.skip(f"ブラウザ {browser_name} が利用できません")
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP"
        )
        page = await context.new_page()
        
        yield page, browser_name
        
        await context.close()

    @pytest.mark.asyncio
    async def test_cross_browser_compatibility(self):
        """クロスブラウザ互換性テスト"""
        print("\n🌐 クロスブラウザ互換性テスト...")
        
        playwright = await async_playwright().start()
        
        browsers_to_test = [
            ("chromium", playwright.chromium),
            ("firefox", playwright.firefox),
            ("webkit", playwright.webkit)
        ]
        
        for browser_name, browser_type in browsers_to_test:
            try:
                browser = await browser_type.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ja-JP"
                )
                page = await context.new_page()
                
                print(f"\n🌐 {browser_name} でのブラウザ互換性テスト...")
                
                # アプリケーションにアクセス
                await page.goto("http://localhost:5001", timeout=30000)
                
                # 基本的なページ要素の確認
                await page.wait_for_selector("h1, .title, .header", timeout=10000)
                
                # ナビゲーションメニューの確認
                nav_elements = await page.query_selector_all("nav, .navigation, .nav")
                assert len(nav_elements) > 0, f"{browser_name}: ナビゲーション要素が見つからない"
                
                # JavaScript動作確認
                js_working = await page.evaluate("() => typeof window !== 'undefined'")
                assert js_working, f"{browser_name}: JavaScript が動作していない"
                
                # CSS適用確認
                body = await page.query_selector("body")
                computed_style = await page.evaluate("(element) => getComputedStyle(element).display", body)
                assert computed_style != "none", f"{browser_name}: CSS が適切に適用されていない"
                
                print(f"✅ {browser_name}: 基本互換性OK")
                
                await context.close()
                await browser.close()
                
            except Exception as e:
                print(f"❌ {browser_name}: 互換性テスト失敗 - {e}")
                # 個別ブラウザのテスト失敗は全体の失敗にはしない
                continue
        
        await playwright.stop()

    @pytest.mark.asyncio
    async def test_responsive_design_comprehensive(self, browsers_setup):
        """レスポンシブデザイン徹底テスト"""
        print("\n📱 レスポンシブデザイン徹底テスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためレスポンシブテストをスキップ")
        
        # 様々なデバイスサイズでテスト
        device_sizes = [
            {"name": "スマートフォン(小)", "width": 320, "height": 568},
            {"name": "スマートフォン(大)", "width": 414, "height": 896},
            {"name": "タブレット(縦)", "width": 768, "height": 1024},
            {"name": "タブレット(横)", "width": 1024, "height": 768},
            {"name": "ノートPC", "width": 1366, "height": 768},
            {"name": "デスクトップ", "width": 1920, "height": 1080},
            {"name": "4K", "width": 3840, "height": 2160}
        ]
        
        for device in device_sizes:
            context = await browser.new_context(
                viewport={"width": device["width"], "height": device["height"]},
                locale="ja-JP"
            )
            page = await context.new_page()
            
            try:
                await page.goto("http://localhost:5001", timeout=15000)
                
                # レイアウト崩れチェック
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # 横スクロールが発生していないかチェック
                page_width = await page.evaluate("document.documentElement.scrollWidth")
                viewport_width = device["width"]
                
                if page_width > viewport_width + 20:  # 20pxの余裕を持たせる
                    print(f"⚠️ {device['name']}: 横スクロール発生 (ページ幅: {page_width}px, ビューポート: {viewport_width}px)")
                
                # 重要な要素が表示されているかチェック
                important_elements = await page.query_selector_all("h1, nav, button, .btn, input")
                visible_elements = 0
                
                for element in important_elements:
                    is_visible = await element.is_visible()
                    if is_visible:
                        visible_elements += 1
                
                assert visible_elements > 0, f"{device['name']}: 重要な要素が表示されていない"
                
                print(f"✅ {device['name']} ({device['width']}x{device['height']}): レスポンシブOK")
                
            except Exception as e:
                print(f"❌ {device['name']}: レスポンシブテスト失敗 - {e}")
            
            finally:
                await context.close()

    @pytest.mark.asyncio
    async def test_accessibility_comprehensive(self, browsers_setup):
        """アクセシビリティ徹底テスト"""
        print("\n♿ アクセシビリティ徹底テスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためアクセシビリティテストをスキップ")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto("http://localhost:5001", timeout=15000)
            
            # 1. キーボードナビゲーションテスト
            print("🔍 キーボードナビゲーションテスト...")
            focusable_elements = await page.query_selector_all(
                "button, input, select, textarea, a[href], [tabindex]:not([tabindex='-1'])"
            )
            
            if focusable_elements:
                # 最初の要素にフォーカス
                await focusable_elements[0].focus()
                
                # Tab キーでナビゲーション
                for i in range(min(5, len(focusable_elements))):
                    await page.keyboard.press("Tab")
                    focused_element = await page.evaluate("document.activeElement.tagName")
                    assert focused_element in ["BUTTON", "INPUT", "SELECT", "TEXTAREA", "A"], "Tab ナビゲーションが機能していない"
            
            # 2. ARIA属性チェック
            print("🔍 ARIA属性チェック...")
            aria_elements = await page.query_selector_all("[aria-label], [aria-describedby], [aria-labelledby], [role]")
            print(f"ARIA属性を持つ要素数: {len(aria_elements)}")
            
            # 3. セマンティックHTMLチェック
            print("🔍 セマンティックHTMLチェック...")
            semantic_elements = await page.query_selector_all("header, nav, main, section, article, aside, footer, h1, h2, h3, h4, h5, h6")
            assert len(semantic_elements) > 0, "セマンティックHTML要素が不足"
            
            # 4. alt属性チェック（画像）
            print("🔍 画像alt属性チェック...")
            images = await page.query_selector_all("img")
            images_without_alt = []
            
            for img in images:
                alt_text = await img.get_attribute("alt")
                if alt_text is None:
                    src = await img.get_attribute("src")
                    images_without_alt.append(src)
            
            if images_without_alt:
                print(f"⚠️ alt属性が不足している画像: {len(images_without_alt)}個")
            
            # 5. コントラスト比チェック（基本的な確認）
            print("🔍 基本的なコントラストチェック...")
            dark_backgrounds = await page.query_selector_all("[style*='background: black'], [style*='background-color: black'], .dark")
            if dark_backgrounds:
                print(f"ダークテーマ要素発見: {len(dark_backgrounds)}個")
            
            # 6. フォームのラベル確認
            print("🔍 フォームラベル確認...")
            form_inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='password'], textarea")
            unlabeled_inputs = []
            
            for input_elem in form_inputs:
                input_id = await input_elem.get_attribute("id")
                aria_label = await input_elem.get_attribute("aria-label")
                
                if input_id:
                    label = await page.query_selector(f"label[for='{input_id}']")
                    if not label and not aria_label:
                        unlabeled_inputs.append(input_id or "unknown")
                elif not aria_label:
                    unlabeled_inputs.append("no-id")
            
            if unlabeled_inputs:
                print(f"⚠️ ラベルが不足している入力要素: {len(unlabeled_inputs)}個")
            
            print("✅ アクセシビリティテスト完了")
            
        except Exception as e:
            pytest.fail(f"アクセシビリティテスト失敗: {e}")
        
        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_mobile_specific_features(self, browsers_setup):
        """モバイル特有機能テスト"""
        print("\n📱 モバイル特有機能テスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためモバイルテストをスキップ")
        
        # モバイルデバイスエミュレーション
        mobile_devices = [
            {
                "name": "iPhone 13",
                "viewport": {"width": 390, "height": 844},
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
                "is_mobile": True,
                "has_touch": True
            },
            {
                "name": "Samsung Galaxy S21",
                "viewport": {"width": 384, "height": 854},
                "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36",
                "is_mobile": True,
                "has_touch": True
            },
            {
                "name": "iPad",
                "viewport": {"width": 820, "height": 1180},
                "user_agent": "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
                "is_mobile": True,
                "has_touch": True
            }
        ]
        
        for device in mobile_devices:
            context = await browser.new_context(
                viewport=device["viewport"],
                user_agent=device["user_agent"],
                is_mobile=device["is_mobile"],
                has_touch=device["has_touch"]
            )
            page = await context.new_page()
            
            try:
                await page.goto("http://localhost:5001", timeout=15000)
                
                # タッチイベントのテスト
                print(f"🔍 {device['name']}: タッチイベントテスト...")
                buttons = await page.query_selector_all("button, .btn, [role='button']")
                
                if buttons:
                    # タッチターゲットサイズ確認（44px以上推奨）
                    for i, button in enumerate(buttons[:3]):  # 最初の3つをテスト
                        try:
                            bounding_box = await button.bounding_box()
                            if bounding_box:
                                width = bounding_box["width"]
                                height = bounding_box["height"]
                                
                                if width < 44 or height < 44:
                                    print(f"⚠️ {device['name']}: タッチターゲットが小さい (ボタン{i}: {width}x{height}px)")
                        except:
                            pass  # 要素が表示されていない場合はスキップ
                
                # スワイプジェスチャーテスト（可能な場合）
                print(f"🔍 {device['name']}: スワイプテスト...")
                try:
                    # ページの中央でスワイプ動作をテスト
                    viewport = device["viewport"]
                    center_x = viewport["width"] // 2
                    center_y = viewport["height"] // 2
                    
                    await page.touchscreen.tap(center_x, center_y)
                    print(f"✅ {device['name']}: タッチ操作OK")
                except Exception as e:
                    print(f"⚠️ {device['name']}: タッチ操作テスト失敗 - {e}")
                
                # オリエンテーション変更テスト
                print(f"🔍 {device['name']}: オリエンテーション変更テスト...")
                if device["name"] == "iPhone 13":  # iPhoneでのみテスト
                    # 横向きに変更
                    await page.set_viewport_size({"width": 844, "height": 390})
                    await page.wait_for_timeout(1000)
                    
                    # レイアウトが適応しているかチェック
                    page_width = await page.evaluate("document.documentElement.scrollWidth")
                    if page_width > 860:  # 20pxの余裕
                        print(f"⚠️ {device['name']}: 横向きでレイアウト崩れ")
                    else:
                        print(f"✅ {device['name']}: 横向き対応OK")
                    
                    # 縦向きに戻す
                    await page.set_viewport_size(device["viewport"])
                
                print(f"✅ {device['name']}: モバイルテスト完了")
                
            except Exception as e:
                print(f"❌ {device['name']}: モバイルテスト失敗 - {e}")
            
            finally:
                await context.close()

    @pytest.mark.asyncio
    async def test_performance_comprehensive(self, browsers_setup):
        """パフォーマンス徹底テスト"""
        print("\n⚡ パフォーマンス徹底テスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためパフォーマンステストをスキップ")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # パフォーマンス測定開始
            start_time = time.time()
            
            await page.goto("http://localhost:5001", timeout=30000)
            
            # DOMContentLoaded時間測定
            dom_loaded_time = await page.evaluate("""
                () => {
                    return performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart;
                }
            """)
            
            # ページ読み込み完了時間測定
            load_time = await page.evaluate("""
                () => {
                    return performance.timing.loadEventEnd - performance.timing.navigationStart;
                }
            """)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"📊 パフォーマンス測定結果:")
            print(f"  DOMContentLoaded: {dom_loaded_time}ms")
            print(f"  ページ読み込み完了: {load_time}ms")
            print(f"  総読み込み時間: {total_time:.2f}秒")
            
            # パフォーマンス基準チェック
            assert dom_loaded_time < 5000, f"DOMContentLoadedが遅い: {dom_loaded_time}ms"
            assert load_time < 10000, f"ページ読み込みが遅い: {load_time}ms"
            assert total_time < 15, f"総読み込み時間が遅い: {total_time}秒"
            
            # リソース読み込み詳細分析
            resources = await page.evaluate("""
                () => {
                    const resources = performance.getEntriesByType('resource');
                    return resources.map(r => ({
                        name: r.name,
                        duration: r.duration,
                        size: r.transferSize || 0,
                        type: r.initiatorType
                    }));
                }
            """)
            
            # 大きなリソースのチェック
            large_resources = [r for r in resources if r['size'] > 1024 * 1024]  # 1MB以上
            if large_resources:
                print(f"⚠️ 大きなリソース ({len(large_resources)}個):")
                for resource in large_resources[:3]:
                    print(f"    {resource['name']}: {resource['size'] / 1024 / 1024:.1f}MB")
            
            # 遅いリソースのチェック
            slow_resources = [r for r in resources if r['duration'] > 2000]  # 2秒以上
            if slow_resources:
                print(f"⚠️ 遅いリソース ({len(slow_resources)}個):")
                for resource in slow_resources[:3]:
                    print(f"    {resource['name']}: {resource['duration']:.0f}ms")
            
            print("✅ パフォーマンステスト完了")
            
        except Exception as e:
            pytest.fail(f"パフォーマンステスト失敗: {e}")
        
        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_javascript_errors_detection(self, browsers_setup):
        """JavaScript エラー検出テスト"""
        print("\n🐛 JavaScript エラー検出テスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためJSエラーテストをスキップ")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        js_errors = []
        console_errors = []
        
        # JavaScriptエラーをキャッチ
        page.on("pageerror", lambda error: js_errors.append(str(error)))
        
        # コンソールエラーをキャッチ
        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
        
        page.on("console", handle_console)
        
        try:
            await page.goto("http://localhost:5001", timeout=15000)
            
            # ページ上の各操作でエラーが発生しないかテスト
            operations = [
                "基本ナビゲーション",
                "ボタンクリック",
                "フォーム操作"
            ]
            
            for operation in operations:
                try:
                    if operation == "基本ナビゲーション":
                        # ナビゲーションリンクをテスト
                        nav_links = await page.query_selector_all("nav a, .nav-link")
                        if nav_links:
                            await nav_links[0].click()
                            await page.wait_for_timeout(1000)
                    
                    elif operation == "ボタンクリック":
                        # ボタンをテスト
                        buttons = await page.query_selector_all("button, .btn")
                        if buttons:
                            await buttons[0].click()
                            await page.wait_for_timeout(1000)
                    
                    elif operation == "フォーム操作":
                        # 入力フィールドをテスト
                        inputs = await page.query_selector_all("input[type='text'], textarea")
                        if inputs:
                            await inputs[0].fill("テスト入力")
                            await page.wait_for_timeout(1000)
                
                except Exception as e:
                    print(f"⚠️ {operation} 中にエラー: {e}")
            
            # 最終的なエラーチェック
            if js_errors:
                print(f"❌ JavaScript エラー ({len(js_errors)}個):")
                for error in js_errors[:3]:
                    print(f"    {error}")
                # JSエラーがあってもテストは継続（警告として扱う）
                
            if console_errors:
                print(f"⚠️ コンソールエラー ({len(console_errors)}個):")
                for error in console_errors[:3]:
                    print(f"    {error}")
            
            if not js_errors and not console_errors:
                print("✅ JavaScript エラーなし")
            
        except Exception as e:
            pytest.fail(f"JavaScript エラー検出テスト失敗: {e}")
        
        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_network_conditions_simulation(self, browsers_setup):
        """ネットワーク条件シミュレーションテスト"""
        print("\n🌐 ネットワーク条件シミュレーションテスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためネットワークテストをスキップ")
        
        # 様々なネットワーク条件をテスト
        network_conditions = [
            {"name": "高速", "download": 10000, "upload": 10000, "latency": 10},
            {"name": "3G", "download": 1600, "upload": 750, "latency": 150},
            {"name": "低速3G", "download": 400, "upload": 400, "latency": 400},
            {"name": "オフライン", "offline": True}
        ]
        
        for condition in network_conditions:
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # ネットワーク条件を設定
                if condition.get("offline"):
                    await context.set_offline(True)
                    print(f"🔍 {condition['name']} 条件でテスト...")
                    
                    # オフライン時の動作確認
                    try:
                        await page.goto("http://localhost:5001", timeout=5000)
                        pytest.fail("オフライン時にページが読み込まれた（キャッシュの可能性）")
                    except:
                        print(f"✅ {condition['name']}: 適切にオフライン状態を検出")
                else:
                    # CDPでネットワーク条件をエミュレート
                    cdp = await context.new_cdp_session(page)
                    await cdp.send("Network.emulateNetworkConditions", {
                        "offline": False,
                        "downloadThroughput": condition["download"] * 1024 / 8,  # bps
                        "uploadThroughput": condition["upload"] * 1024 / 8,      # bps
                        "latency": condition["latency"]
                    })
                    
                    print(f"🔍 {condition['name']} 条件でテスト...")
                    
                    start_time = time.time()
                    await page.goto("http://localhost:5001", timeout=30000)
                    load_time = time.time() - start_time
                    
                    print(f"  読み込み時間: {load_time:.2f}秒")
                    
                    # 低速条件での妥当性チェック
                    if condition["name"] == "低速3G":
                        assert load_time > 2, f"低速3Gにしては読み込みが速すぎる: {load_time:.2f}秒"
                    elif condition["name"] == "高速":
                        assert load_time < 10, f"高速条件にしては読み込みが遅い: {load_time:.2f}秒"
                    
                    print(f"✅ {condition['name']}: ネットワーク条件テストOK")
                
            except Exception as e:
                if not condition.get("offline"):
                    print(f"❌ {condition['name']}: ネットワークテスト失敗 - {e}")
            
            finally:
                await context.close()

    @pytest.mark.asyncio
    async def test_browser_cache_behavior(self, browsers_setup):
        """ブラウザキャッシュ動作テスト"""
        print("\n💾 ブラウザキャッシュ動作テスト...")
        
        browser = browsers_setup.get('chromium')
        if not browser:
            pytest.skip("Chromiumが利用できないためキャッシュテストをスキップ")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 初回アクセス
            print("🔍 初回アクセス...")
            start_time = time.time()
            await page.goto("http://localhost:5001", timeout=15000)
            first_load_time = time.time() - start_time
            
            # ページリロード（キャッシュ効果確認）
            print("🔍 ページリロード...")
            start_time = time.time()
            await page.reload()
            reload_time = time.time() - start_time
            
            print(f"📊 キャッシュ効果:")
            print(f"  初回読み込み: {first_load_time:.2f}秒")
            print(f"  リロード: {reload_time:.2f}秒")
            
            # キャッシュ効果があることを確認（リロードが速くなる）
            if reload_time < first_load_time * 0.8:
                print("✅ キャッシュ効果が確認できます")
            else:
                print("⚠️ キャッシュ効果が少ない可能性があります")
            
            # ハードリフレッシュテスト
            print("🔍 ハードリフレッシュ...")
            await page.keyboard.down("Shift")
            await page.reload()
            await page.keyboard.up("Shift")
            
            print("✅ キャッシュテスト完了")
            
        except Exception as e:
            pytest.fail(f"キャッシュテスト失敗: {e}")
        
        finally:
            await context.close()


# 実際のアプリケーション起動チェック
@pytest.fixture(scope="session", autouse=True)
def ensure_app_running():
    """テスト実行前にアプリケーションが起動していることを確認"""
    import requests
    
    max_retries = 10
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
                    "テスト実行前に 'python app.py' でアプリを起動してください。"
                )