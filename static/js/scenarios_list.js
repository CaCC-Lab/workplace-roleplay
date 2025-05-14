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

    function sortScenarios(order = 'scenario-num') {
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
                
                if (difficultyA.includes('初級')) {
                    valueA = 1;
                } else if (difficultyA.includes('中級')) {
                    valueA = 2;
                } else if (difficultyA.includes('上級')) {
                    valueA = 3;
                }
                
                if (difficultyB.includes('初級')) {
                    valueB = 1;
                } else if (difficultyB.includes('中級')) {
                    valueB = 2;
                } else if (difficultyB.includes('上級')) {
                    valueB = 3;
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

        // 既存のカードをすべて削除
        while (scenariosList.firstChild) {
            scenariosList.removeChild(scenariosList.firstChild);
        }

        // ソートされたカードを順番に追加
        sortedCards.forEach(card => {
            scenariosList.appendChild(card);
        });
        
        console.log('Sort completed and DOM updated');
    }

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
    
    // DOM変更をトラッキング
    const observer = new MutationObserver((mutations) => {
        // DOMに変更があった場合に再ソート
        if (mutations.some(mutation => mutation.type === 'childList')) {
            console.log('DOM changes detected, reapplying sort');
            sortScenarios(sortSelect.value);
        }
    });
    
    // 監視の開始
    observer.observe(scenariosList, { childList: true });
} 