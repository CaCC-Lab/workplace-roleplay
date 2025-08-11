// 無限ループ防止フラグとデバウンス機能
let isCurrentlySorting = false;
let sortTimeoutId = null;

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
            // シナリオID順（見出し文字列から抽出）
            const titleA = a.querySelector('h3').textContent.trim();
            const titleB = b.querySelector('h3').textContent.trim();
            return titleA.localeCompare(titleB, 'ja');
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