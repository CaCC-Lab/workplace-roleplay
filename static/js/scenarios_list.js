// 無限ループ防止フラグとデバウンス機能
let isCurrentlySorting = false;
let sortTimeoutId = null;

// ===== 状態保持機能 =====
const STATE_STORAGE_KEY = 'scenarios-list-state';

// フィルター状態を保存
function saveFilterState() {
    const difficultyFilter = document.getElementById('difficulty-filter');
    const tagFilter = document.getElementById('tag-filter');
    
    const state = {
        difficulty: difficultyFilter ? difficultyFilter.value : '',
        tag: tagFilter ? tagFilter.value : '',
        timestamp: Date.now()
    };
    
    try {
        localStorage.setItem(STATE_STORAGE_KEY, JSON.stringify(state));
        console.log('[saveFilterState] フィルター状態を保存:', state);
    } catch (error) {
        console.warn('[saveFilterState] 状態保存に失敗:', error);
    }
}

// フィルター状態を復元
function restoreFilterState() {
    try {
        const savedState = localStorage.getItem(STATE_STORAGE_KEY);
        if (!savedState) return false;
        
        const state = JSON.parse(savedState);
        
        // 1時間以内の状態のみ復元
        const oneHour = 60 * 60 * 1000;
        if (Date.now() - state.timestamp > oneHour) {
            localStorage.removeItem(STATE_STORAGE_KEY);
            return false;
        }
        
        const difficultyFilter = document.getElementById('difficulty-filter');
        const tagFilter = document.getElementById('tag-filter');
        
        if (difficultyFilter && state.difficulty) {
            difficultyFilter.value = state.difficulty;
        }
        if (tagFilter && state.tag) {
            tagFilter.value = state.tag;
        }
        
        console.log('[restoreFilterState] フィルター状態を復元:', state);
        
        // フィルターを適用
        if (state.difficulty || state.tag) {
            // 少し遅延させてDOMの準備を待つ
            setTimeout(() => {
                filterScenarios();
            }, 100);
        }
        
        return true;
    } catch (error) {
        console.warn('[restoreFilterState] 状態復元に失敗:', error);
        localStorage.removeItem(STATE_STORAGE_KEY);
        return false;
    }
}

// 状態をクリア
function clearFilterState() {
    localStorage.removeItem(STATE_STORAGE_KEY);
}

// デバウンス関数
function debounce(func, wait) {
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(sortTimeoutId);
            func(...args);
        };
        clearTimeout(sortTimeoutId);
        sortTimeoutId = setTimeout(later, wait);
    };
}

// シナリオIDから数値部分を抽出する関数
function extractScenarioNumber(scenarioId) {
    const match = scenarioId.match(/(\d+)$/);
    return match ? parseInt(match[1]) : 0;
}

// グローバル関数として定義
function sortScenarios(sortType) {
    // 無限ループ防止
    if (isCurrentlySorting) {
        console.log(`[sortScenarios] ソート処理中のため中断: ${sortType}`);
        return;
    }
    
    isCurrentlySorting = true;
    
    const scenariosList = document.querySelector('.scenarios-list');
    const scenarioCards = Array.from(document.querySelectorAll('.scenario-card'));
    
    console.log(`[sortScenarios] ソート開始: ${sortType}, カード数: ${scenarioCards.length}`);
    
    if (scenarioCards.length === 0) {
        console.log('[sortScenarios] シナリオカードが見つかりません');
        isCurrentlySorting = false;
        return;
    }
    
    // 難易度の重み
    const difficultyWeights = {
        '初級': 1,
        '中級': 2,
        '上級': 3
    };
    
    scenarioCards.sort((a, b) => {
        if (sortType === 'scenario-num') {
            // シナリオID順（data属性から直接取得して数値比較）
            const idA = a.getAttribute('data-scenario-id') || '';
            const idB = b.getAttribute('data-scenario-id') || '';
            const numA = extractScenarioNumber(idA);
            const numB = extractScenarioNumber(idB);
            
            // 数値が同じ場合は文字列全体で比較（フォールバック）
            if (numA === numB) {
                return idA.localeCompare(idB);
            }
            
            console.log(`[sortScenarios] 比較: ${idA}(${numA}) vs ${idB}(${numB})`);
            return numA - numB;
        } else {
            // 難易度でソート
            const diffA = a.querySelector('.difficulty-badge').textContent.replace('難易度: ', '').trim();
            const diffB = b.querySelector('.difficulty-badge').textContent.replace('難易度: ', '').trim();
            
            const weightA = difficultyWeights[diffA] || 0;
            const weightB = difficultyWeights[diffB] || 0;
            
            if (sortType === 'asc') {
                return weightA - weightB;
            } else {
                return weightB - weightA;
            }
        }
    });
    
    // DOMを効率的に再配置（DocumentFragment使用）
    const fragment = document.createDocumentFragment();
    scenarioCards.forEach(card => {
        fragment.appendChild(card);
    });
    scenariosList.appendChild(fragment);
    
    console.log(`[sortScenarios] ソート完了: ${sortType}`);
    
    // フラグをリセット（requestAnimationFrameで次のフレームで解除）
    requestAnimationFrame(() => {
        isCurrentlySorting = false;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initializeModal();
    initializeFilters();
    
    // ページロード完了後に強制的に初期ソートを実行
    // DOMの準備ができていることを確認してからソート
    setTimeout(() => {
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            sortScenarios('scenario-num');  // デフォルトではシナリオID順にソート
            console.log('Applied initial sort on page load completion');
        }
    }, 200);
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
    const scenariosList = document.querySelector('.scenarios-list');
    const scenarioCards = Array.from(document.querySelectorAll('.scenario-card'));

    function filterScenarios() {
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
    
    // MutationObserver: 条件付きで有効化（将来の動的追加に対応）
    // 現在は無効化されているが、必要に応じて有効化可能
    const ENABLE_DYNAMIC_SCENARIOS = false; // 動的シナリオ追加が必要な場合はtrueに
    
    if (ENABLE_DYNAMIC_SCENARIOS) {
        // デバウンス処理を適用したMutationObserver
        const debouncedSort = debounce(() => {
            if (!isCurrentlySorting) {
                sortScenarios(sortSelect.value);
            }
        }, 200);
        
        const observer = new MutationObserver((mutations) => {
            // ソート処理中は完全に無視
            if (isCurrentlySorting) {
                return;
            }
            
            // 新しいシナリオカードの追加のみを検知
            const hasNewCards = mutations.some(mutation => {
                if (mutation.type !== 'childList') return false;
                
                return Array.from(mutation.addedNodes).some(node => {
                    // テキストノードなどを除外
                    if (node.nodeType !== Node.ELEMENT_NODE) return false;
                    // scenario-cardクラスを持つ要素のみ
                    return node.classList && node.classList.contains('scenario-card');
                });
            });
            
            if (hasNewCards) {
                console.log('New scenario cards detected, scheduling sort');
                debouncedSort();
            }
        });
        
        // より制限的な監視オプション
        observer.observe(scenariosList, { 
            childList: true, 
            subtree: false,
            attributes: false,
            characterData: false
        });
    }
}

// ===== 状態保持機能の初期化 =====
document.addEventListener('DOMContentLoaded', function() {
    // フィルター状態を復元
    const stateRestored = restoreFilterState();
    
    // フィルター変更時に状態を保存
    const difficultyFilter = document.getElementById('difficulty-filter');
    const tagFilter = document.getElementById('tag-filter');
    
    if (difficultyFilter) {
        difficultyFilter.addEventListener('change', function() {
            saveFilterState();
            filterScenarios(); // フィルターを適用
        });
    }
    
    if (tagFilter) {
        tagFilter.addEventListener('change', function() {
            saveFilterState();
            filterScenarios(); // フィルターを適用
        });
    }
    
    // ナビゲーションリンクでの状態保持確認
    const navLinks = document.querySelectorAll('.navigation a, .nav-button');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const difficultyValue = difficultyFilter ? difficultyFilter.value : '';
            const tagValue = tagFilter ? tagFilter.value : '';
            
            // フィルターが設定されている場合に確認ダイアログ表示
            if ((difficultyValue || tagValue) && !link.href.includes('/scenario/')) {
                const confirmed = confirm('フィルター設定が失われます。続行しますか？');
                if (confirmed) {
                    // 明示的に離脱する場合は状態をクリア
                    if (link.href.includes('/')) {
                        clearFilterState();
                    }
                } else {
                    e.preventDefault();
                }
            }
        });
    });
    
    console.log('[scenarios_list] 状態保持機能を初期化完了');
}); 