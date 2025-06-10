/**
 * 強み分析チャート表示用JavaScript
 */

// グローバル名前空間の汚染を防ぐため、完全に隔離された実行環境を作成
console.log('[strength_chart.js] Script loaded at:', window.location.pathname);
console.log('[strength_chart.js] Full URL:', window.location.href);

if (typeof window.StrengthAnalysisModule === 'undefined') {
    window.StrengthAnalysisModule = {};
}

(function(StrengthAnalysis) {
    'use strict';
    
    console.log('[strength_chart.js] IIFE executing at:', window.location.pathname);
    
    // 初期化フラグ（二重実行を防ぐ）
    if (StrengthAnalysis.initialized) {
        console.log('StrengthAnalysisModule already initialized, skipping.');
        return;
    }
    
    // このスクリプトは強み分析ページでのみ動作する
    const currentPath = window.location.pathname;
    if (currentPath !== '/strength_analysis') {
        console.log('strength_chart.js: Not on strength analysis page (' + currentPath + '), exiting.');
        return;
    }
    
    // 二重チェック：必要な要素が存在するか確認
    if (!document.getElementById('strengthRadarChart')) {
        console.log('strength_chart.js: Required elements not found, exiting.');
        return;
    }
    
    // 初期化完了フラグ
    StrengthAnalysis.initialized = true;

    // チャートインスタンスをローカルで管理
    let strengthRadarChart = null;
    let growthChart = null;

    // 強みカテゴリの定義（Pythonと同期）
    const STRENGTH_CATEGORIES = {
    empathy: { name: "共感力", color: "#FF6384" },
    clarity: { name: "明確な伝達力", color: "#36A2EB" },
    active_listening: { name: "傾聴力", color: "#FFCE56" },
    adaptability: { name: "適応力", color: "#4BC0C0" },
    positivity: { name: "前向きさ", color: "#9966FF" },
    professionalism: { name: "プロフェッショナリズム", color: "#FF9F40" }
};

/**
 * レーダーチャートの描画
 */
function renderStrengthRadarChart(canvasId, strengthData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('Canvas element not found:', canvasId);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // データの準備
    const labels = Object.keys(strengthData.scores).map(key => 
        STRENGTH_CATEGORIES[key]?.name || key
    );
    const data = Object.values(strengthData.scores);
    
    // 既存のチャートがあれば破棄
    if (strengthRadarChart && typeof strengthRadarChart.destroy === 'function') {
        strengthRadarChart.destroy();
    }
    
    // 新しいChart.jsインスタンスを作成
    try {
        strengthRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: '現在のスキル',
                data: data,
                fill: true,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(75, 192, 192, 1)',
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        font: {
                            size: 12
                        }
                    },
                    pointLabels: {
                        font: {
                            size: 14
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'あなたのコミュニケーションスキル',
                    font: {
                        size: 18
                    },
                    padding: 20
                },
                legend: {
                    display: false
                }
            }
        }
    });
    } catch (error) {
        console.error('Error creating radar chart:', error);
        throw error;
    }
}

/**
 * 成長推移グラフの描画
 */
function renderGrowthChart(canvasId, historyData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('Canvas element not found:', canvasId);
        return;
    }
    
    if (!historyData || historyData.length === 0) {
        canvas.parentElement.innerHTML = '<p class="no-data">まだ練習履歴がありません。練習を重ねると成長推移が表示されます。</p>';
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // データの準備
    const labels = historyData.map(d => {
        const date = new Date(d.timestamp);
        return `${date.getMonth() + 1}/${date.getDate()}`;
    });
    
    // 各スキルのデータセットを作成
    const datasets = Object.keys(STRENGTH_CATEGORIES).map(category => ({
        label: STRENGTH_CATEGORIES[category].name,
        data: historyData.map(d => d.scores[category] || 0),
        borderColor: STRENGTH_CATEGORIES[category].color,
        backgroundColor: STRENGTH_CATEGORIES[category].color + '20',
        fill: false,
        tension: 0.1
    }));
    
    // 既存のチャートがあれば破棄
    if (growthChart && typeof growthChart.destroy === 'function') {
        growthChart.destroy();
    }
    
    try {
        growthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'スキルの成長推移',
                    font: {
                        size: 18
                    },
                    padding: 20
                },
                legend: {
                    display: true,
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
    } catch (error) {
        console.error('Error creating growth chart:', error);
        throw error;
    }
}

/**
 * 強みの詳細表示
 */
function displayStrengthDetails(strengthData) {
    const topStrengthsDiv = document.getElementById('topStrengths');
    if (!topStrengthsDiv) return;
    
    // トップ3の強みを取得
    const sortedStrengths = Object.entries(strengthData.scores)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3);
    
    const strengthsHTML = sortedStrengths.map(([key, score], index) => {
        const category = STRENGTH_CATEGORIES[key];
        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉';
        
        return `
            <div class="strength-item">
                <div class="strength-header">
                    <span class="medal">${medal}</span>
                    <h3>${category.name}</h3>
                    <span class="score">${Math.round(score)}点</span>
                </div>
                <p class="strength-description">${getStrengthDescription(key)}</p>
                <div class="strength-progress">
                    <div class="progress-bar" style="width: ${score}%; background-color: ${category.color}"></div>
                </div>
            </div>
        `;
    }).join('');
    
    topStrengthsDiv.innerHTML = strengthsHTML;
}

/**
 * 強みの説明文を取得
 */
function getStrengthDescription(key) {
    const descriptions = {
        empathy: "相手の気持ちを理解し、適切に反応する力が優れています。",
        clarity: "分かりやすく論理的に説明する能力が高いです。",
        active_listening: "相手の話を真摯に聞き、理解を示すことができます。",
        adaptability: "相手や状況に応じて柔軟に対応できます。",
        positivity: "建設的で前向きな雰囲気を作ることが得意です。",
        professionalism: "職場での適切な振る舞いと判断力を持っています。"
    };
    
    return descriptions[key] || "";
}

/**
 * 励ましメッセージの表示
 */
function displayEncouragementMessage(messages) {
    const messageDiv = document.getElementById('encouragementMessage');
    if (!messageDiv || !messages || messages.length === 0) return;
    
    const messagesHTML = messages.map(message => 
        `<p class="encouragement-text">✨ ${message}</p>`
    ).join('');
    
    messageDiv.innerHTML = messagesHTML;
}

/**
 * 強み分析データの取得と表示
 */
async function loadStrengthAnalysis(sessionType = 'chat') {
    console.log('[loadStrengthAnalysis] Called with sessionType:', sessionType);
    console.log('[loadStrengthAnalysis] Current path:', window.location.pathname);
    console.log('[loadStrengthAnalysis] Call stack:', new Error().stack);
    
    // 再度安全チェック
    if (window.location.pathname !== '/strength_analysis') {
        console.warn('loadStrengthAnalysis called outside strength analysis page, aborting.');
        return;
    }
    
    try {
        console.log('Loading strength analysis for session type:', sessionType);
        
        const response = await fetch('/api/strength_analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                type: sessionType,
                // シナリオタイプの場合でも、強み分析ページでは全シナリオの統計を表示
                scenario_id: sessionType === 'scenario' ? 'all' : undefined 
            })
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.text();
            console.error('Response error:', errorData);
            throw new Error(`Failed to load strength analysis: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Received data:', data);
        
        // エラーレスポンスのチェック
        if (data.error) {
            throw new Error(data.error);
        }
        
        // レーダーチャートの描画
        if (data.scores) {
            renderStrengthRadarChart('strengthRadarChart', { scores: data.scores });
            displayStrengthDetails({ scores: data.scores });
        }
        
        // 成長推移グラフの描画
        if (data.history) {
            renderGrowthChart('growthChart', data.history);
        }
        
        // 励ましメッセージの表示
        if (data.messages) {
            displayEncouragementMessage(data.messages);
        }
        
    } catch (error) {
        console.error('Error loading strength analysis:', error);
        showError('強み分析の読み込みに失敗しました。エラー: ' + error.message);
    }
}

/**
 * エラー表示
 */
function showError(message) {
    // 各セクションにエラーメッセージを表示
    const sections = ['strengthRadarChart', 'growthChart', 'topStrengths', 'encouragementMessage'];
    
    sections.forEach(sectionId => {
        const element = document.getElementById(sectionId);
        if (element) {
            if (element.tagName === 'CANVAS') {
                element.parentElement.innerHTML = `<div class="error-message">${message}</div>`;
            } else {
                element.innerHTML = `<div class="error-message">${message}</div>`;
            }
        }
    });
}

/**
 * フィードバック後の強み表示（既存のフィードバック機能と統合）
 */
function displayStrengthHighlight(strengthData) {
    if (!strengthData || !strengthData.top_strengths) return;
    
    const strengthHighlight = document.getElementById('strengthHighlight');
    if (!strengthHighlight) return;
    
    const topStrengths = strengthData.top_strengths;
    const strengthHTML = topStrengths.map(strength => `
        <div class="strength-badge">
            <span class="strength-name">${strength.name}</span>
            <span class="strength-score">${Math.round(strength.score)}点</span>
        </div>
    `).join('');
    
    strengthHighlight.innerHTML = `
        <h3>あなたの強み</h3>
        <div class="strength-badges">${strengthHTML}</div>
    `;
    
    // アニメーション効果
    setTimeout(() => {
        strengthHighlight.classList.add('show');
    }, 100);
}

// ページ読み込み時の処理
document.addEventListener('DOMContentLoaded', function() {
    // 再度チェック：強み分析ページでない場合は何もしない
    if (window.location.pathname !== '/strength_analysis') {
        console.log('strength_chart.js DOMContentLoaded: Not on strength analysis page, exiting.');
        return;
    }
    
    // 強み分析ページであることを確認（URLパスもチェック）
    const isStrengthAnalysisPage = window.location.pathname === '/strength_analysis';
    const hasChartElement = document.getElementById('strengthRadarChart') !== null;
    
    // 強み分析ページの場合のみ実行
    if (isStrengthAnalysisPage && hasChartElement) {
        // Chart.jsが読み込まれているか確認
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            showError('チャートライブラリの読み込みに失敗しました。');
            return;
        }
        
        // 少し遅延してから実行（Chart.jsの完全な初期化を待つ）
        setTimeout(() => {
            loadStrengthAnalysis();
        }, 100);
        
        // タブ切り替え機能（あれば）
        const tabs = document.querySelectorAll('.tab-button');
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const sessionType = this.dataset.sessionType;
                loadStrengthAnalysis(sessionType);
                
                // アクティブタブの切り替え
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }
});

})(window.StrengthAnalysisModule); // 名前空間を渡してIIFEを終了