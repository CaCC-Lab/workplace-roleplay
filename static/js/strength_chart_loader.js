/**
 * 強み分析チャートのローダー
 * strength_chart.jsを強み分析ページでのみ動的に読み込む
 */

(function() {
    'use strict';
    
    // 強み分析ページでのみstrength_chart.jsを読み込む
    if (window.location.pathname === '/strength_analysis') {
        console.log('Loading strength chart script for strength analysis page');
        
        // strength_chart.jsを動的に読み込む
        const script = document.createElement('script');
        script.src = '/static/js/strength_chart_main.js';
        script.onload = function() {
            console.log('Strength chart script loaded successfully');
        };
        script.onerror = function() {
            console.error('Failed to load strength chart script');
        };
        document.head.appendChild(script);
    } else {
        console.log('Not on strength analysis page, skipping strength chart script');
    }
})();