const { test, expect } = require('@playwright/test');

test.describe('基本的なページナビゲーション', () => {
  
  test('トップページが正しく表示される', async ({ page }) => {
    await page.goto('/');
    
    // ページタイトルの確認
    await expect(page).toHaveTitle(/職場コミュニケーション練習アプリ/);
    
    // メインヘッダーの確認
    await expect(page.locator('h1')).toContainText('職場コミュニケーション練習アプリ');
    
    // 主要機能カードの存在確認
    await expect(page.locator('h3:has-text("シナリオロールプレイ")')).toBeVisible();
    await expect(page.locator('h3:has-text("雑談練習")')).toBeVisible();
    await expect(page.locator('h3:has-text("会話観戦モード")')).toBeVisible();
    await expect(page.locator('h3:has-text("学習履歴")')).toBeVisible();
  });

  test('雑談練習ページにアクセスできる', async ({ page }) => {
    await page.goto('/');
    
    // 雑談練習ボタンをクリック
    await page.click('text=雑談練習を始める');
    
    // ページが正しく表示されることを確認
    await expect(page.locator('h1')).toContainText('雑談練習');
    await expect(page.locator('#partner-type')).toBeVisible();
    await expect(page.locator('#situation')).toBeVisible();
  });

  test('シナリオ練習ページにアクセスできる', async ({ page }) => {
    await page.goto('/scenario');
    
    // ページタイトルと要素の確認
    await expect(page.locator('h1, h2')).toContainText('シナリオ');
    await expect(page.locator('body')).toBeVisible();
  });

  test('会話観戦ページにアクセスできる', async ({ page }) => {
    await page.goto('/watch');
    
    // ページタイトルと要素の確認
    await expect(page.locator('h1, h2')).toContainText('観戦');
    await expect(page.locator('body')).toBeVisible();
  });

  test('学習履歴ページにアクセスできる', async ({ page }) => {
    await page.goto('/history');
    
    // ページタイトルの確認
    await expect(page.locator('h1')).toContainText('学習履歴');
    await expect(page.locator('body')).toBeVisible();
  });

  test('認証関連のページが適切に動作する', async ({ page }) => {
    // ログインページにアクセス
    await page.goto('/auth/login');
    
    // ページが読み込まれることを確認
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('h1, h2')).toContainText(/ログイン|login/i);
    
    // 新規登録ページにアクセス
    await page.goto('/auth/register');
    
    // ページが読み込まれることを確認
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('h1, h2')).toContainText(/登録|register/i);
  });

  test('レスポンシブデザインが正しく動作する', async ({ page }) => {
    // デスクトップサイズでアクセス
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    
    // ページが表示されることを確認
    await expect(page.locator('h1')).toBeVisible();
    
    // モバイルサイズに変更
    await page.setViewportSize({ width: 375, height: 667 });
    
    // モバイル表示が適切に調整されていることを確認
    await expect(page.locator('h1')).toBeVisible();
    
    // タブレットサイズでの確認
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('h1')).toBeVisible();
  });
});