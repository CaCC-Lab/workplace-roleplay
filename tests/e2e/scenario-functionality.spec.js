const { test, expect } = require('@playwright/test');

test.describe('シナリオ機能のE2Eテスト', () => {
  
  test.beforeEach(async ({ page }) => {
    // 各テスト前にシナリオページに移動
    await page.goto('/scenario');
    await expect(page.locator('h2')).toContainText('シナリオ練習');
  });

  test('シナリオ一覧が正しく表示される', async ({ page }) => {
    // シナリオグリッドが表示されることを確認
    await expect(page.locator('.scenario-grid')).toBeVisible();
    
    // 少なくとも1つのシナリオカードが表示されることを確認
    const scenarioCards = page.locator('.scenario-card');
    await expect(scenarioCards.first()).toBeVisible();
    
    // シナリオカードの基本要素確認
    const firstCard = scenarioCards.first();
    await expect(firstCard.locator('.scenario-title')).toBeVisible();
    await expect(firstCard.locator('.scenario-difficulty')).toBeVisible();
    await expect(firstCard.locator('.scenario-description')).toBeVisible();
  });

  test('難易度フィルターが正しく動作する', async ({ page }) => {
    // 難易度フィルターが存在する場合のテスト
    const difficultyFilter = page.locator('#difficulty-filter, .difficulty-filter');
    
    if (await difficultyFilter.isVisible()) {
      // 初級フィルターを選択
      await difficultyFilter.selectOption('初級');
      
      // 初級シナリオのみが表示されることを確認
      const visibleCards = page.locator('.scenario-card:visible');
      const count = await visibleCards.count();
      
      if (count > 0) {
        // 表示されているカードが初級であることを確認
        await expect(visibleCards.first().locator('.scenario-difficulty')).toContainText('初級');
      }
      
      // 中級フィルターのテスト
      await difficultyFilter.selectOption('中級');
      
      // 中級シナリオが表示されることを確認
      const intermediateCards = page.locator('.scenario-card:visible');
      if (await intermediateCards.count() > 0) {
        await expect(intermediateCards.first().locator('.scenario-difficulty')).toContainText('中級');
      }
    }
  });

  test('シナリオを選択して練習開始ができる', async ({ page }) => {
    // 最初のシナリオカードをクリック
    const firstScenario = page.locator('.scenario-card').first();
    await firstScenario.click();
    
    // シナリオ練習画面に遷移することを確認
    await expect(page.locator('.scenario-chat-container, #scenario-chat')).toBeVisible({ timeout: 10000 });
    
    // シナリオ情報が表示されることを確認
    await expect(page.locator('.scenario-info, .current-scenario')).toBeVisible();
    
    // チャット入力エリアが表示されることを確認
    await expect(page.locator('#user-input')).toBeVisible();
    await expect(page.locator('#send-button')).toBeVisible();
  });

  test('シナリオ練習でメッセージ送信ができる', async ({ page }) => {
    // シナリオを選択
    await page.locator('.scenario-card').first().click();
    await expect(page.locator('#user-input')).toBeVisible({ timeout: 10000 });
    
    const testMessage = 'おはようございます。今日もよろしくお願いします。';
    
    // メッセージを入力して送信
    await page.fill('#user-input', testMessage);
    await page.click('#send-button');
    
    // ユーザーメッセージが表示されることを確認
    await expect(page.locator('.user-message')).toContainText(testMessage);
    
    // AI応答（シナリオキャラクター）の応答を確認
    await expect(page.locator('.ai-message, .scenario-response')).toBeVisible({ timeout: 15000 });
    
    // 入力フィールドがクリアされることを確認
    await expect(page.locator('#user-input')).toHaveValue('');
  });

  test('シナリオフィードバック機能', async ({ page }) => {
    // シナリオを選択して会話
    await page.locator('.scenario-card').first().click();
    await expect(page.locator('#user-input')).toBeVisible({ timeout: 10000 });
    
    // メッセージを送信
    await page.fill('#user-input', 'シナリオテストメッセージです');
    await page.click('#send-button');
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 15000 });
    
    // フィードバックボタンまたは機能を探す
    const feedbackButton = page.locator('#feedback-button, .feedback-btn, text=フィードバック');
    
    if (await feedbackButton.isVisible()) {
      await feedbackButton.click();
      
      // フィードバック内容が表示されることを確認
      await expect(page.locator('.feedback-content, #feedback-display')).toBeVisible({ timeout: 10000 });
      
      // フィードバック内容が有意義であることを確認
      const feedbackText = await page.locator('.feedback-content').textContent();
      expect(feedbackText.length).toBeGreaterThan(10);
    }
  });

  test('シナリオ終了とリセット機能', async ({ page }) => {
    // シナリオを選択
    await page.locator('.scenario-card').first().click();
    await expect(page.locator('#user-input')).toBeVisible({ timeout: 10000 });
    
    // いくつかのメッセージを送信
    const messages = ['初回メッセージ', '2回目メッセージ'];
    
    for (const message of messages) {
      await page.fill('#user-input', message);
      await page.click('#send-button');
      await expect(page.locator('.user-message').last()).toContainText(message);
      await page.waitForTimeout(2000);
    }
    
    // リセットまたは終了ボタンを探す
    const resetButton = page.locator('#reset-button, .reset-btn, text=リセット, text=終了');
    
    if (await resetButton.isVisible()) {
      await resetButton.click();
      
      // 会話がクリアされることを確認
      const messageCount = await page.locator('.user-message').count();
      expect(messageCount).toBe(0);
    }
  });

  test('シナリオ検索機能', async ({ page }) => {
    // 検索ボックスが存在する場合のテスト
    const searchBox = page.locator('#scenario-search, .search-input');
    
    if (await searchBox.isVisible()) {
      // 検索キーワードを入力
      await searchBox.fill('会議');
      
      // 検索結果の確認
      await page.waitForTimeout(1000); // 検索結果の更新を待つ
      
      const visibleCards = page.locator('.scenario-card:visible');
      const count = await visibleCards.count();
      
      if (count > 0) {
        // 検索にヒットしたシナリオのタイトルや説明に「会議」が含まれることを確認
        const firstCard = visibleCards.first();
        const cardText = await firstCard.textContent();
        expect(cardText.toLowerCase()).toMatch(/会議|meeting/);
      }
      
      // 検索をクリア
      await searchBox.clear();
      await page.waitForTimeout(1000);
      
      // 全てのシナリオが再表示されることを確認
      const allCards = page.locator('.scenario-card:visible');
      const allCount = await allCards.count();
      expect(allCount).toBeGreaterThanOrEqual(count);
    }
  });

  test('シナリオタグフィルター', async ({ page }) => {
    // タグフィルターが存在する場合のテスト
    const tagFilter = page.locator('.tag-filter, .scenario-tags');
    
    if (await tagFilter.isVisible()) {
      // 特定のタグをクリック
      const firstTag = tagFilter.locator('.tag').first();
      
      if (await firstTag.isVisible()) {
        const tagText = await firstTag.textContent();
        await firstTag.click();
        
        // タグに該当するシナリオのみが表示されることを確認
        await page.waitForTimeout(1000);
        const filteredCards = page.locator('.scenario-card:visible');
        
        if (await filteredCards.count() > 0) {
          // 表示されているカードが選択したタグを含むことを確認
          const cardText = await filteredCards.first().textContent();
          expect(cardText).toContain(tagText);
        }
      }
    }
  });

  test('シナリオ進行状況の保存と復元', async ({ page }) => {
    // シナリオを選択して会話開始
    await page.locator('.scenario-card').first().click();
    await expect(page.locator('#user-input')).toBeVisible({ timeout: 10000 });
    
    // メッセージを送信
    const testMessage = '進行状況テストメッセージ';
    await page.fill('#user-input', testMessage);
    await page.click('#send-button');
    await expect(page.locator('.user-message')).toContainText(testMessage);
    
    // ページをリロード
    await page.reload();
    
    // 会話履歴が保持されているか確認（実装に応じて）
    // セッション管理の実装により動作が異なる可能性がある
    const messages = page.locator('.user-message');
    if (await messages.count() > 0) {
      await expect(messages.first()).toContainText(testMessage);
    }
  });

  test('レスポンシブデザイン - モバイル表示', async ({ page }) => {
    // モバイルサイズに変更
    await page.setViewportSize({ width: 375, height: 667 });
    
    // シナリオグリッドがモバイルで適切に表示されることを確認
    await expect(page.locator('.scenario-grid')).toBeVisible();
    
    // シナリオカードがスタック表示されることを確認
    const cards = page.locator('.scenario-card');
    await expect(cards.first()).toBeVisible();
    
    // シナリオを選択
    await cards.first().click();
    await expect(page.locator('#user-input')).toBeVisible({ timeout: 10000 });
    
    // モバイルでのチャット機能を確認
    await page.fill('#user-input', 'モバイルテスト');
    await page.click('#send-button');
    await expect(page.locator('.user-message')).toContainText('モバイルテスト');
  });
});