const { test, expect } = require('@playwright/test');

test.describe('雑談機能のE2Eテスト', () => {
  
  test.beforeEach(async ({ page }) => {
    // 各テスト前に雑談ページに移動して練習を開始
    await page.goto('/');
    await page.click('text=雑談練習を始める');
    await expect(page.locator('h2')).toContainText('練習設定');
    
    // 練習を開始する
    await page.click('#start-practice');
    
    // チャットが開始されるまで待機
    await expect(page.locator('#user-input')).toBeEnabled();
    await expect(page.locator('#send-button')).toBeEnabled();
  });

  test('基本的なメッセージ送信ができる', async ({ page }) => {
    const testMessage = 'こんにちは、今日はいい天気ですね';
    
    // メッセージを入力
    await page.fill('#user-input', testMessage);
    
    // 送信ボタンをクリック
    await page.click('#send-button');
    
    // ユーザーメッセージが表示されることを確認
    await expect(page.locator('.user-message')).toContainText(testMessage);
    
    // AI応答が表示されることを確認（タイムアウトを長めに設定）
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 10000 });
    
    // 入力フィールドがクリアされることを確認
    await expect(page.locator('#user-input')).toHaveValue('');
  });

  test('Enterキーでメッセージ送信ができる', async ({ page }) => {
    const testMessage = 'Enterキーのテストです';
    
    // メッセージを入力
    await page.fill('#user-input', testMessage);
    
    // Enterキーを押す
    await page.press('#user-input', 'Enter');
    
    // メッセージが送信されることを確認
    await expect(page.locator('.user-message')).toContainText(testMessage);
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 10000 });
  });

  test('空のメッセージは送信できない', async ({ page }) => {
    // 初期メッセージ数を記録
    const initialMessageCount = await page.locator('#chat-messages .message').count();
    
    // 空の状態で送信ボタンをクリック
    await page.click('#send-button');
    
    // 少し待機
    await page.waitForTimeout(500);
    
    // メッセージが追加されていないことを確認
    const afterMessageCount = await page.locator('#chat-messages .message').count();
    expect(afterMessageCount).toBe(initialMessageCount);
  });

  test('長いメッセージの処理', async ({ page }) => {
    const longMessage = 'これは非常に長いメッセージのテストです。'.repeat(20);
    
    // 長いメッセージを入力
    await page.fill('#user-input', longMessage);
    await page.click('#send-button');
    
    // メッセージが適切に表示されることを確認
    await expect(page.locator('.user-message')).toContainText('これは非常に長いメッセージ');
    
    // レスポンスが返ることを確認
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 15000 });
  });

  test('連続したメッセージ送信', async ({ page }) => {
    const messages = [
      '最初のメッセージです',
      '2番目のメッセージです',
      '3番目のメッセージです'
    ];
    
    for (const message of messages) {
      // メッセージを送信
      await page.fill('#user-input', message);
      await page.click('#send-button');
      
      // ユーザーメッセージが表示されることを確認
      await expect(page.locator('.user-message').last()).toContainText(message);
      
      // AI応答を待つ
      await expect(page.locator('.ai-message').last()).toBeVisible({ timeout: 10000 });
      
      // 少し待機
      await page.waitForTimeout(1000);
    }
    
    // 全てのメッセージが表示されていることを確認
    const userMessages = page.locator('.user-message');
    await expect(userMessages).toHaveCount(3);
  });

  test('AIモデル切り替え機能', async ({ page }) => {
    // モデル選択要素が存在する場合のテスト
    const modelSelector = page.locator('#model-selector');
    
    if (await modelSelector.isVisible()) {
      // 異なるモデルを選択
      await modelSelector.selectOption('gemini-1.5-flash');
      
      // メッセージを送信
      await page.fill('#user-input', 'モデル切り替えテスト');
      await page.click('#send-button');
      
      // 応答が返ることを確認
      await expect(page.locator('.ai-message')).toBeVisible({ timeout: 10000 });
    }
  });

  test('会話履歴のクリア機能', async ({ page }) => {
    // 最初のメッセージを送信
    await page.fill('#user-input', '最初のメッセージです');
    await page.click('#send-button');
    await expect(page.locator('.user-message')).toContainText('最初のメッセージです');
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 10000 });
    
    // 履歴クリアボタンをクリック
    await page.click('#clear-history');
    
    // チャットがリセットされることを確認
    await expect(page.locator('.user-message')).not.toBeVisible();
    await expect(page.locator('#user-input')).toBeDisabled();
    await expect(page.locator('#send-button')).toBeDisabled();
  });

  test('フィードバック機能', async ({ page }) => {
    // メッセージを送信
    await page.fill('#user-input', 'フィードバックテスト用メッセージ');
    await page.click('#send-button');
    await expect(page.locator('.ai-message')).toBeVisible({ timeout: 10000 });
    
    // フィードバックボタンが表示される場合
    const feedbackButton = page.locator('#feedback-button, .feedback-btn');
    
    if (await feedbackButton.isVisible()) {
      await feedbackButton.click();
      
      // フィードバック内容が表示されることを確認
      await expect(page.locator('.feedback-content, #feedback-display')).toBeVisible({ timeout: 10000 });
    }
  });

  test('チャット機能の基本的な安定性', async ({ page }) => {
    // 複数回のメッセージ送信でエラーが発生しないことを確認
    const messages = ['テスト1', 'テスト2', 'テスト3'];
    
    for (const message of messages) {
      await page.fill('#user-input', message);
      await page.click('#send-button');
      
      // メッセージが正常に送信されることを確認
      await expect(page.locator('.user-message').last()).toContainText(message);
      await expect(page.locator('.ai-message').last()).toBeVisible({ timeout: 5000 });
      
      // 少し待機
      await page.waitForTimeout(500);
    }
    
    // 全てのメッセージが表示されていることを確認
    const userMessages = page.locator('.user-message');
    await expect(userMessages).toHaveCount(3);
  });
});