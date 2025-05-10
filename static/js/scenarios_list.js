document.addEventListener('DOMContentLoaded', function() {
    initializeModal();
    initializeFilters();
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

    function sortScenarios(order = 'asc') {
        const sortedCards = scenarioCards.sort((a, b) => {
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
        });

        scenariosList.innerHTML = '';
        sortedCards.forEach(card => {
            scenariosList.appendChild(card);
        });
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
    sortSelect.innerHTML = `
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

    // 初期ソート
    sortScenarios('asc');
} 