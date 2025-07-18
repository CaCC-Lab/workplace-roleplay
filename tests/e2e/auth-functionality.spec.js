const { test, expect } = require('@playwright/test');

test.describe('認証機能のE2Eテスト', () => {
  
  test.describe('ユーザー登録', () => {
    test('有効なデータで新規登録ができる', async ({ page }) => {
      await page.goto('/auth/register');
      
      // ユニークなテストデータを生成
      const timestamp = Date.now();
      const username = `testuser${timestamp}`;
      const email = `test${timestamp}@example.com`;
      const password = 'SecurePass123!';
      
      // 登録フォームに入力
      await page.fill('input[name="username"]', username);
      await page.fill('input[name="email"]', email);
      await page.fill('input[name="password"]', password);
      await page.fill('input[name="confirm_password"]', password);
      
      // 登録ボタンをクリック
      await page.click('input[type="submit"], button[type="submit"]');
      
      // 登録成功後の確認（リダイレクトまたは成功メッセージ）
      await expect(page.url()).toMatch(/\/(dashboard|profile|success)/, { timeout: 10000 });
      
      // または成功メッセージの確認
      await expect(page.locator('.success-message, .alert-success')).toBeVisible({ timeout: 5000 });
    });

    test('無効なメールアドレスで登録エラー', async ({ page }) => {
      await page.goto('/auth/register');
      
      // 無効なメールアドレスで登録試行
      await page.fill('input[name="username"]', 'testuser');
      await page.fill('input[name="email"]', 'invalid-email');
      await page.fill('input[name="password"]', 'password123');
      await page.fill('input[name="confirm_password"]', 'password123');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // エラーメッセージの確認
      await expect(page.locator('.error-message, .alert-danger, .field-error')).toBeVisible();
    });

    test('パスワード不一致で登録エラー', async ({ page }) => {
      await page.goto('/auth/register');
      
      // パスワードが一致しない場合
      await page.fill('input[name="username"]', 'testuser');
      await page.fill('input[name="email"]', 'test@example.com');
      await page.fill('input[name="password"]', 'password123');
      await page.fill('input[name="confirm_password"]', 'password456');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // パスワード不一致エラーの確認
      await expect(page.locator('.error-message, .alert-danger')).toContainText(/パスワード|password|match/i);
    });

    test('既存ユーザー名で登録エラー', async ({ page }) => {
      await page.goto('/auth/register');
      
      // 既に存在するユーザー名で登録試行
      await page.fill('input[name="username"]', 'admin');
      await page.fill('input[name="email"]', 'newemail@example.com');
      await page.fill('input[name="password"]', 'password123');
      await page.fill('input[name="confirm_password"]', 'password123');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // 重複エラーメッセージの確認
      await expect(page.locator('.error-message, .alert-danger')).toContainText(/存在|既に|already|exists/i);
    });
  });

  test.describe('ログイン', () => {
    test('有効な認証情報でログインできる', async ({ page }) => {
      await page.goto('/auth/login');
      
      // テストユーザーでログイン
      await page.fill('input[name="username_or_email"]', 'testuser1');
      await page.fill('input[name="password"]', 'testpass123');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // ログイン成功後の確認
      await expect(page.url()).toMatch(/\/(dashboard|profile|\?)/, { timeout: 10000 });
      
      // ログイン状態の確認（ナビゲーションの変化など）
      await expect(page.locator('.user-menu, .logout-link, text=ログアウト')).toBeVisible({ timeout: 5000 });
    });

    test('メールアドレスでもログインできる', async ({ page }) => {
      await page.goto('/auth/login');
      
      // メールアドレスでログイン
      await page.fill('input[name="username_or_email"]', 'test1@example.com');
      await page.fill('input[name="password"]', 'testpass123');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // ログイン成功の確認
      await expect(page.url()).not.toContain('/auth/login', { timeout: 10000 });
    });

    test('無効なパスワードでログインエラー', async ({ page }) => {
      await page.goto('/auth/login');
      
      // 間違ったパスワードでログイン試行
      await page.fill('input[name="username_or_email"]', 'testuser1');
      await page.fill('input[name="password"]', 'wrongpassword');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // エラーメッセージの確認
      await expect(page.locator('.error-message, .alert-danger')).toContainText(/パスワード|password|incorrect/i);
      
      // ログインページに留まることを確認
      await expect(page.url()).toContain('/auth/login');
    });

    test('存在しないユーザーでログインエラー', async ({ page }) => {
      await page.goto('/auth/login');
      
      // 存在しないユーザーでログイン試行
      await page.fill('input[name="username_or_email"]', 'nonexistentuser');
      await page.fill('input[name="password"]', 'password123');
      
      await page.click('input[type="submit"], button[type="submit"]');
      
      // エラーメッセージの確認
      await expect(page.locator('.error-message, .alert-danger')).toContainText(/見つかりません|not found|invalid/i);
    });

    test('空のフィールドでログインエラー', async ({ page }) => {
      await page.goto('/auth/login');
      
      // 空のまま送信
      await page.click('input[type="submit"], button[type="submit"]');
      
      // 必須フィールドエラーの確認
      await expect(page.locator('.error-message, .alert-danger, .field-error')).toBeVisible();
    });
  });

  test.describe('ログアウト', () => {
    test('ログアウト機能が正しく動作する', async ({ page }) => {
      // まずログイン
      await page.goto('/auth/login');
      await page.fill('input[name="username_or_email"]', 'testuser1');
      await page.fill('input[name="password"]', 'testpass123');
      await page.click('input[type="submit"], button[type="submit"]');
      
      // ログイン成功を確認
      await expect(page.locator('.user-menu, .logout-link')).toBeVisible({ timeout: 10000 });
      
      // ログアウト
      await page.click('text=ログアウト, .logout-link, a[href="/auth/logout"]');
      
      // ログアウト後の確認
      await expect(page.url()).toMatch(/\/(auth\/login|\?)/, { timeout: 10000 });
      await expect(page.locator('text=ログイン')).toBeVisible();
    });
  });

  test.describe('認証保護', () => {
    test('未認証では保護されたページにアクセスできない', async ({ page }) => {
      // ログアウト状態で保護されたページにアクセス
      await page.goto('/dashboard');
      
      // ログインページにリダイレクトされることを確認
      await expect(page.url()).toContain('/auth/login', { timeout: 10000 });
    });

    test('認証後は保護されたページにアクセスできる', async ({ page }) => {
      // ログイン
      await page.goto('/auth/login');
      await page.fill('input[name="username_or_email"]', 'testuser1');
      await page.fill('input[name="password"]', 'testpass123');
      await page.click('input[type="submit"], button[type="submit"]');
      
      // 保護されたページにアクセス
      await page.goto('/dashboard');
      
      // アクセスできることを確認
      await expect(page.url()).not.toContain('/auth/login');
      await expect(page.locator('h1, h2')).toBeVisible();
    });
  });

  test.describe('セッション管理', () => {
    test('ログイン状態がページ間で保持される', async ({ page }) => {
      // ログイン
      await page.goto('/auth/login');
      await page.fill('input[name="username_or_email"]', 'testuser1');
      await page.fill('input[name="password"]', 'testpass123');
      await page.click('input[type="submit"], button[type="submit"]');
      
      // 異なるページに移動
      await page.goto('/');
      await page.goto('/scenario');
      await page.goto('/watch');
      
      // 各ページでログイン状態が保持されていることを確認
      await expect(page.locator('.user-menu, .logout-link')).toBeVisible();
    });

    test('ブラウザリロード後もセッションが保持される', async ({ page }) => {
      // ログイン
      await page.goto('/auth/login');
      await page.fill('input[name="username_or_email"]', 'testuser1');
      await page.fill('input[name="password"]', 'testpass123');
      await page.click('input[type="submit"], button[type="submit"]');
      
      // ページをリロード
      await page.reload();
      
      // ログイン状態が保持されていることを確認
      await expect(page.locator('.user-menu, .logout-link')).toBeVisible({ timeout: 5000 });
    });
  });
});