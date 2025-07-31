// 仮想スクロールの有効/無効を制御するフラグ
const ENABLE_VIRTUAL_SCROLL = true;
const VIRTUAL_SCROLL_THRESHOLD = 30; // この数以上のシナリオがある場合に仮想スクロールを有効化

// グローバル変数
let virtualScroller = null;
let allScenarios = {};

document.addEventListener('DOMContentLoaded', function() {
    initializeModal();
    
    // シナリオデータを取得して初期化
    fetchScenarios().then(scenarios => {
        allScenarios = scenarios;
        const scenarioCount = Object.keys(scenarios).length;
        
        // シナリオ数に基づいて仮想スクロールを使用するか決定
        if (ENABLE_VIRTUAL_SCROLL && scenarioCount >= VIRTUAL_SCROLL_THRESHOLD) {
            console.log(`${scenarioCount} scenarios found. Using virtual scroll.`);
            initializeVirtualScroll(scenarios);
        } else {
            console.log(`${scenarioCount} scenarios found. Using regular rendering.`);
            initializeFilters();
        }
    });
    
    initializeRecommendations();
});

// モーダル関連の機能
function initializeModal() {
    const modal = document.getElementById('tipsModal');
    const span = document.getElementsByClassName('close')[0];
    
    window.showTips = function(scenarioId) {
        modal.style.display = "block";
        // ここでシナリオIDに応じたtipsを表示
    }

    span.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
}

// シナリオ操作関連の機能
window.startNewScenario = function(scenarioId) {
    fetch("/api/scenario_clear", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ scenario_id: scenarioId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            window.location.href = `/scenario/${scenarioId}`;
        }
    });
}

window.continuePreviousScenario = function(scenarioId) {
    window.location.href = `/scenario/${scenarioId}`;
}

// フィルターとソート機能
function initializeFilters() {
    const difficultyFilter = document.getElementById('difficulty-filter');
    const tagFilter = document.getElementById('tag-filter');
    // メインのscenarios-listを取得（推薦用ではないもの）
    const allLists = document.querySelectorAll('.scenarios-list');
    let scenariosList = null;
    for (const list of allLists) {
        if (!list.classList.contains('recommendation-list')) {
            scenariosList = list;
            break;
        }
    }
    if (!scenariosList) {
        console.error('Main scenarios list not found');
        return;
    }
    const scenarioCards = Array.from(document.querySelectorAll('.scenario-card'));
    
    // MutationObserverのフラグ管理
    let isUpdatingDOM = false;
    let observer = null;

    function sortScenarios(order = 'scenario-num') {
        // 毎回最新のscenarioCardsを取得
        const scenarioCards = Array.from(document.querySelectorAll('.scenario-card'));
        
        // ソート前にコンソールに情報を出力
        console.log(`Sorting scenarios with order: ${order}. Cards count: ${scenarioCards.length}`);
        
        if (scenarioCards.length === 0) {
            console.warn('No scenario cards found to sort');
            return;
        }

        const sortedCards = scenarioCards.sort((a, b) => {
            // シナリオID順ソート
            if (order === 'scenario-num') {
                // href属性からシナリオIDの数値部分を抽出
                const hrefA = a.querySelector('.primary-button').getAttribute('href');
                const hrefB = b.querySelector('.primary-button').getAttribute('href');
                
                const idA = parseInt(hrefA.match(/scenario(\d+)/)[1]) || 0;
                const idB = parseInt(hrefB.match(/scenario(\d+)/)[1]) || 0;
                
                console.log(`Comparing: scenario${idA} vs scenario${idB}`);
                return idA - idB;
            }
            // 難易度ソート
            else {
                const difficultyA = a.querySelector('.difficulty-badge').textContent.trim();
                const difficultyB = b.querySelector('.difficulty-badge').textContent.trim();
                
                let valueA = 1;
                let valueB = 1;
                
                // 難易度の値をマッピング
                const difficultyMap = {
                    '入門': 1,
                    '初級': 2,
                    '中級': 3,
                    '上級': 4
                };
                
                // 各難易度テキストから値を取得
                for (let [text, value] of Object.entries(difficultyMap)) {
                    if (difficultyA.includes(text)) {
                        valueA = value;
                    }
                    if (difficultyB.includes(text)) {
                        valueB = value;
                    }
                }
                
                if (order === 'asc') {
                    return valueA - valueB;
                } else {
                    return valueB - valueA;
                }
            }
        });

        // デバッグログの追加
        console.log('Sorted order:', sortedCards.map(card => {
            const href = card.querySelector('.primary-button').getAttribute('href');
            return href.match(/scenario\d+/)[0];
        }).join(', '));

        // DOM更新フラグをセット（MutationObserverによる再実行を防ぐ）
        isUpdatingDOM = true;
        
        // Observerを一時的に切断
        if (observer) {
            observer.disconnect();
        }

        // 既存のカードをすべて削除
        while (scenariosList.firstChild) {
            scenariosList.removeChild(scenariosList.firstChild);
        }

        // ソートされたカードを順番に追加
        sortedCards.forEach(card => {
            scenariosList.appendChild(card);
        });
        
        console.log('Sort completed and DOM updated');
        
        // DOM更新が完了したらフラグをリセットし、Observerを再開
        isUpdatingDOM = false;
        if (observer) {
            observer.observe(scenariosList, { childList: true });
        }
    }

    function filterScenarios() {
        // 毎回最新のscenarioCardsを取得
        const scenarioCards = Array.from(document.querySelectorAll('.scenario-card'));
        const selectedDifficulty = difficultyFilter.value;
        const selectedTag = tagFilter.value;

        scenarioCards.forEach(card => {
            const cardDifficulty = card.querySelector('.difficulty-badge').textContent.replace('難易度: ', '').trim();
            const cardTags = Array.from(card.querySelectorAll('.tag')).map(tag => tag.textContent.trim());
            
            const difficultyMatch = !selectedDifficulty || cardDifficulty.includes(selectedDifficulty);
            const tagMatch = !selectedTag || cardTags.some(tag => tag === selectedTag);

            card.style.display = difficultyMatch && tagMatch ? 'block' : 'none';
        });
    }

    // ソートセレクトボックスの追加
    const sortSelect = document.createElement('select');
    sortSelect.id = 'sort-select';
    sortSelect.className = 'styled-select';
    sortSelect.innerHTML = `
        <option value="scenario-num">シナリオ番号順</option>
        <option value="asc">難易度：低い順</option>
        <option value="desc">難易度：高い順</option>
    `;

    const filterGroup = document.createElement('div');
    filterGroup.className = 'filter-group';
    const label = document.createElement('label');
    label.htmlFor = 'sort-select';
    label.textContent = '並び替え';
    filterGroup.appendChild(label);
    filterGroup.appendChild(sortSelect);
    document.querySelector('.filter-options').appendChild(filterGroup);

    // イベントリスナーの設定
    difficultyFilter.addEventListener('change', filterScenarios);
    tagFilter.addEventListener('change', filterScenarios);
    sortSelect.addEventListener('change', (e) => sortScenarios(e.target.value));

    // 初期ソート - シナリオID順で実行
    console.log('Initializing filters and applying initial sort');
    sortScenarios('scenario-num');
    
    // 初期表示時は全てのシナリオを表示（フィルターをリセット）
    difficultyFilter.value = '';
    tagFilter.value = '';
    
    // フィルターを適用して全てのシナリオを表示
    filterScenarios();
    
    // MutationObserverはシナリオカードが動的に追加される場合のみ必要
    // 現在のページでは初期ロード時にすべてのカードが存在するため、削除
    // 必要な場合は以下のコメントを解除してください：
    /*
    observer = new MutationObserver((mutations) => {
        // DOM更新中の場合は何もしない（無限ループ防止）
        if (isUpdatingDOM) return;
        
        // DOMに変更があった場合に再ソート
        if (mutations.some(mutation => mutation.type === 'childList')) {
            console.log('DOM changes detected, reapplying sort');
            sortScenarios(sortSelect.value);
        }
    });
    
    // 監視の開始
    observer.observe(scenariosList, { childList: true });
    */
}

// 推薦機能の初期化
function initializeRecommendations() {
    console.log('Initializing recommendations system');
    
    // 推薦セクションの要素を取得
    const recommendedSection = document.getElementById('recommended-scenarios-section');
    const recommendedList = document.getElementById('recommended-scenarios-list');
    const refreshButton = document.getElementById('refresh-recommendations');
    const explanationButton = document.getElementById('show-recommendation-explanation');
    
    // 推薦セクションが存在しない場合は何もしない
    if (!recommendedSection) {
        console.log('Recommended scenarios section not found');
        return;
    }
    
    // 初回推薦の読み込み
    loadRecommendations();
    
    // イベントリスナーの設定
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            console.log('Refresh recommendations clicked');
            loadRecommendations();
        });
    }
    
    if (explanationButton) {
        explanationButton.addEventListener('click', () => {
            console.log('Show explanation clicked');
            showRecommendationExplanation();
        });
    }
}

// 推薦シナリオを読み込む
function loadRecommendations() {
    const recommendedSection = document.getElementById('recommended-scenarios-section');
    const recommendedList = document.getElementById('recommended-scenarios-list');
    
    if (!recommendedList) return;
    
    // ローディング表示
    recommendedList.innerHTML = '<div class="loading-recommendations"><i class="fas fa-spinner fa-spin"></i> 推薦シナリオを取得中...</div>';
    
    // 推薦APIを呼び出し
    fetch('/api/recommended_scenarios?limit=3')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.recommendations && data.recommendations.length > 0) {
                displayRecommendations(data.recommendations);
                recommendedSection.style.display = 'block';
            } else {
                // 推薦がない場合はセクションを非表示
                console.log('No recommendations available');
                recommendedSection.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error loading recommendations:', error);
            recommendedList.innerHTML = '<div class="recommendation-error"><i class="fas fa-exclamation-triangle"></i> 推薦シナリオの取得に失敗しました</div>';
        });
}

// 推薦シナリオを表示
function displayRecommendations(recommendations) {
    const recommendedList = document.getElementById('recommended-scenarios-list');
    
    if (!recommendedList) return;
    
    recommendedList.innerHTML = '';
    
    recommendations.forEach(rec => {
        const card = createRecommendationCard(rec);
        recommendedList.appendChild(card);
    });
}

// 推薦シナリオカードを作成
function createRecommendationCard(recommendation) {
    const card = document.createElement('div');
    card.className = 'scenario-card recommendation-card';
    
    // 難易度レベルの変換
    const difficultyLevels = {
        1: '★ 初級',
        2: '★★ 初中級', 
        3: '★★ 中級',
        4: '★★★ 中上級',
        5: '★★★ 上級'
    };
    
    const difficultyText = difficultyLevels[recommendation.difficulty] || '★★ 中級';
    const difficultyClass = recommendation.difficulty <= 2 ? '初級' : 
                          recommendation.difficulty <= 3 ? '中級' : '上級';
    
    card.innerHTML = `
        <div class="recommendation-badge">
            <i class="fas fa-star"></i> おすすめ
        </div>
        <div class="scenario-card-header">
            <h3>
                <i class="fas fa-briefcase"></i>
                ${recommendation.title}
            </h3>
            <span class="difficulty-badge difficulty-${difficultyClass}">
                ${difficultyText}
            </span>
        </div>
        <div class="scenario-content">
            <p class="scenario-description">${recommendation.description}</p>
            <div class="recommendation-reason">
                <i class="fas fa-lightbulb"></i> ${recommendation.reason}
            </div>
            <div class="scenario-tags">
                ${recommendation.target_strengths.map(skill => `<span class="tag skill-tag">${translateSkillName(skill)}</span>`).join('')}
            </div>
        </div>
        <div class="scenario-card-footer">
            <a href="/scenario/${recommendation.scenario_id}" class="primary-button">
                <i class="fas fa-play"></i> 開始
            </a>
            <button class="secondary-button" onclick="submitRecommendationFeedback('${recommendation.scenario_id}', 'helpful')">
                <i class="fas fa-thumbs-up"></i> 役立つ
            </button>
        </div>
    `;
    
    return card;
}

// スキル名を日本語に翻訳
function translateSkillName(skill) {
    const translations = {
        'empathy': '共感力',
        'clarity': '明確性',
        'active_listening': '傾聴力',
        'adaptability': '適応力',
        'positivity': '前向きさ',
        'professionalism': 'プロフェッショナリズム'
    };
    return translations[skill] || skill;
}

// 推薦根拠の説明を表示
function showRecommendationExplanation() {
    fetch('/api/recommendation_explanation')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayExplanationModal(data.explanation);
            } else {
                alert('推薦根拠の取得に失敗しました');
            }
        })
        .catch(error => {
            console.error('Error getting explanation:', error);
            alert('推薦根拠の取得中にエラーが発生しました');
        });
}

// 推薦根拠のモーダル表示
function displayExplanationModal(explanation) {
    const modal = document.getElementById('tipsModal');
    const content = document.getElementById('tipsContent');
    
    if (!modal || !content) return;
    
    let explanationHtml = '';
    
    if (explanation.status === 'no_analysis') {
        explanationHtml = `
            <p><i class="fas fa-info-circle"></i> ${explanation.message}</p>
        `;
    } else if (explanation.status === 'success') {
        const weakSkills = explanation.weak_skills || [];
        const skillScores = explanation.skill_scores || {};
        
        explanationHtml = `
            <div class="explanation-content">
                <h3><i class="fas fa-chart-line"></i> あなたのスキル分析結果</h3>
                <div class="skill-scores">
                    ${Object.entries(skillScores).map(([skill, score]) => `
                        <div class="skill-score-item">
                            <span class="skill-name">${translateSkillName(skill)}</span>
                            <div class="score-bar">
                                <div class="score-fill" style="width: ${(score / 5) * 100}%"></div>
                            </div>
                            <span class="score-value">${score.toFixed(1)}/5.0</span>
                        </div>
                    `).join('')}
                </div>
                
                ${weakSkills.length > 0 ? `
                    <h4><i class="fas fa-target"></i> 重点強化スキル</h4>
                    <div class="weak-skills">
                        ${weakSkills.slice(0, 3).map(([skill, score]) => `
                            <div class="weak-skill-item">
                                <span class="skill-name">${translateSkillName(skill)}</span>
                                <span class="improvement-potential">改善の余地があります</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                <div class="recommendation-logic">
                    <h4><i class="fas fa-cogs"></i> 推薦ロジック</h4>
                    <p>${explanation.recommendation_logic}</p>
                </div>
            </div>
        `;
    } else {
        explanationHtml = `
            <p><i class="fas fa-exclamation-triangle"></i> ${explanation.message}</p>
        `;
    }
    
    content.innerHTML = explanationHtml;
    modal.style.display = 'block';
}

// 推薦フィードバックの送信
function submitRecommendationFeedback(scenarioId, feedbackType) {
    fetch('/api/recommendation_feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            scenario_id: scenarioId,
            feedback_type: feedbackType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Feedback submitted successfully');
            // フィードバック完了のUI表示
            showFeedbackThanks();
        } else {
            console.error('Feedback submission failed:', data.error);
        }
    })
    .catch(error => {
        console.error('Error submitting feedback:', error);
    });
}

// シナリオデータをフェッチ
async function fetchScenarios() {
    try {
        // サーバーからシナリオデータを取得（または既存のDOMから抽出）
        const scenarioCards = document.querySelectorAll('.scenario-card');
        const scenarios = {};
        
        scenarioCards.forEach(card => {
            const link = card.querySelector('.primary-button');
            const href = link.getAttribute('href');
            const scenarioId = href.match(/scenario\/(.+)/)[1];
            
            const title = card.querySelector('h3').textContent.trim();
            const description = card.querySelector('.scenario-description').textContent.trim();
            const difficultyBadge = card.querySelector('.difficulty-badge');
            const difficulty = difficultyBadge.className.match(/difficulty-(\S+)/)[1];
            const tags = Array.from(card.querySelectorAll('.tag')).map(tag => tag.textContent.trim());
            
            // カテゴリを推測（アイコンから）
            let category = 'general';
            const icon = card.querySelector('h3 i');
            if (icon) {
                if (icon.classList.contains('fa-comments')) category = 'communication';
                else if (icon.classList.contains('fa-exclamation-triangle')) category = 'conflict';
                else if (icon.classList.contains('fa-handshake')) category = 'negotiation';
                else if (icon.classList.contains('fa-users')) category = 'leadership';
                else if (icon.classList.contains('fa-comment-dots')) category = 'feedback';
            }
            
            scenarios[scenarioId] = {
                id: scenarioId,
                title,
                description,
                difficulty,
                tags,
                category
            };
        });
        
        return scenarios;
    } catch (error) {
        console.error('Error fetching scenarios:', error);
        return {};
    }
}

// 仮想スクロールの初期化
function initializeVirtualScroll(scenarios) {
    // 仮想スクロールスクリプトを動的に読み込み
    const script = document.createElement('script');
    script.src = '/static/js/virtual-scroll.js';
    script.onload = () => {
        // スクリプトが読み込まれたら仮想スクロールを初期化
        virtualScroller = initializeScenarioVirtualScroll(scenarios);
        
        // フィルター機能を仮想スクロール用に調整
        initializeFiltersForVirtualScroll();
    };
    document.head.appendChild(script);
}

// 仮想スクロール用のフィルター初期化
function initializeFiltersForVirtualScroll() {
    const difficultyFilter = document.getElementById('difficulty-filter');
    const tagFilter = document.getElementById('tag-filter');
    const sortSelect = document.getElementById('sort-select') || createSortSelect();
    
    function applyFiltersAndSort() {
        if (!virtualScroller) return;
        
        const selectedDifficulty = difficultyFilter.value;
        const selectedTag = tagFilter.value;
        const sortOrder = sortSelect.value;
        
        // フィルター関数
        const filterFn = (scenario) => {
            const difficultyMatch = !selectedDifficulty || scenario.difficulty === selectedDifficulty;
            const tagMatch = !selectedTag || scenario.tags.includes(selectedTag);
            return difficultyMatch && tagMatch;
        };
        
        // ソート関数
        const sortFn = getSortFunction(sortOrder);
        
        // フィルターとソートを適用
        virtualScroller.filterItems(filterFn);
        virtualScroller.sortItems(sortFn);
    }
    
    // イベントリスナーの設定
    difficultyFilter.addEventListener('change', applyFiltersAndSort);
    tagFilter.addEventListener('change', applyFiltersAndSort);
    sortSelect.addEventListener('change', applyFiltersAndSort);
    
    // 初期ソート
    applyFiltersAndSort();
}

// ソートセレクトボックスの作成（既存のものがない場合）
function createSortSelect() {
    const sortSelect = document.createElement('select');
    sortSelect.id = 'sort-select';
    sortSelect.className = 'styled-select';
    sortSelect.innerHTML = `
        <option value="scenario-num">シナリオ番号順</option>
        <option value="asc">難易度：低い順</option>
        <option value="desc">難易度：高い順</option>
    `;
    
    const filterGroup = document.createElement('div');
    filterGroup.className = 'filter-group';
    const label = document.createElement('label');
    label.htmlFor = 'sort-select';
    label.textContent = '並び替え';
    filterGroup.appendChild(label);
    filterGroup.appendChild(sortSelect);
    
    const filterOptions = document.querySelector('.filter-options');
    if (filterOptions) {
        filterOptions.appendChild(filterGroup);
    }
    
    return sortSelect;
}

// ソート関数を取得
function getSortFunction(order) {
    if (order === 'scenario-num') {
        return (a, b) => {
            const idA = parseInt(a.id.match(/scenario(\d+)/)[1]) || 0;
            const idB = parseInt(b.id.match(/scenario(\d+)/)[1]) || 0;
            return idA - idB;
        };
    } else {
        const difficultyMap = {
            'pre-beginner': 1,
            'beginner': 2,
            'intermediate': 3,
            'advanced': 4
        };
        
        return (a, b) => {
            const valueA = difficultyMap[a.difficulty] || 2;
            const valueB = difficultyMap[b.difficulty] || 2;
            return order === 'asc' ? valueA - valueB : valueB - valueA;
        };
    }
}

// フィードバック完了の表示
function showFeedbackThanks() {
    const thanksElement = document.createElement('div');
    thanksElement.className = 'feedback-thanks-notification';
    thanksElement.innerHTML = `
        <div class="thanks-content">
            <i class="fas fa-check-circle"></i>
            <span>フィードバックありがとうございました！</span>
        </div>
    `;
    
    // CSSを動的に追加
    if (!document.querySelector('#feedback-thanks-styles')) {
        const style = document.createElement('style');
        style.id = 'feedback-thanks-styles';
        style.textContent = `
            .feedback-thanks-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1000;
                animation: slideInFromRight 0.3s ease-out;
            }
            
            .feedback-thanks-notification .thanks-content {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            @keyframes slideInFromRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(thanksElement);
    
    // 3秒後に自動削除
    setTimeout(() => {
        thanksElement.style.animation = 'slideInFromRight 0.3s ease-in reverse';
        setTimeout(() => thanksElement.remove(), 300);
    }, 3000);
}