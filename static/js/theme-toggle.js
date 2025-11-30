/**
 * ダークモード切り替え機能
 * 職場コミュニケーション練習アプリ
 */

(function() {
    'use strict';
    
    const THEME_KEY = 'workplace-roleplay-theme';
    
    // テーマを適用
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateToggleButton(theme);
    }
    
    // トグルボタンの状態を更新
    function updateToggleButton(theme) {
        const button = document.getElementById('theme-toggle');
        if (!button) return;
        
        const icon = button.querySelector('i');
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
            button.setAttribute('data-tooltip', 'ライトモードに切り替え');
        } else {
            icon.className = 'fas fa-moon';
            button.setAttribute('data-tooltip', 'ダークモードに切り替え');
        }
    }
    
    // 現在のテーマを取得
    function getCurrentTheme() {
        // ローカルストレージから取得
        const savedTheme = localStorage.getItem(THEME_KEY);
        if (savedTheme) {
            return savedTheme;
        }
        
        // システム設定を確認
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        
        return 'light';
    }
    
    // テーマを切り替え
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }
    
    // トグルボタンを作成
    function createToggleButton() {
        // 既存のボタンがあれば削除
        const existing = document.getElementById('theme-toggle');
        if (existing) {
            existing.remove();
        }
        
        const button = document.createElement('button');
        button.id = 'theme-toggle';
        button.className = 'theme-toggle';
        button.setAttribute('aria-label', 'テーマ切り替え');
        button.innerHTML = '<i class="fas fa-moon"></i>';
        button.addEventListener('click', toggleTheme);
        
        document.body.appendChild(button);
        
        // 初期状態を設定
        updateToggleButton(getCurrentTheme());
    }
    
    // システムのテーマ変更を監視
    function watchSystemTheme() {
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
                // ユーザーが手動で設定していない場合のみ追従
                if (!localStorage.getItem(THEME_KEY)) {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }
    
    // 初期化
    function init() {
        // 初期テーマを適用
        applyTheme(getCurrentTheme());
        
        // DOMロード後にボタンを作成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createToggleButton);
        } else {
            createToggleButton();
        }
        
        // システムテーマの変更を監視
        watchSystemTheme();
    }
    
    // 即座に初期化（FLOCを防ぐ）
    init();
    
    // グローバルに公開
    window.themeToggle = {
        toggle: toggleTheme,
        setTheme: applyTheme,
        getTheme: getCurrentTheme
    };
})();
