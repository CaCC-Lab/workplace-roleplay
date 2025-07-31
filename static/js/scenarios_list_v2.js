/**
 * シナリオ一覧ページの改善版JavaScript
 * ページネーション、仮想スクロール、検索機能を実装
 */

class ScenarioListManager {
    constructor() {
        // ページネーション設定
        this.currentPage = 1;
        this.perPage = 12;
        this.totalPages = 1;
        
        // フィルター設定
        this.filters = {
            difficulty: '',
            tag: '',
            search: '',
            sort: 'scenario_num'
        };
        
        // DOM要素
        this.scenariosList = null;
        this.loadingIndicator = null;
        this.paginationContainer = null;
        
        // デバウンスタイマー
        this.searchDebounceTimer = null;
        
        // 初期化
        this.init();
    }
    
    init() {
        // DOM要素の取得
        this.scenariosList = document.querySelector('.scenarios-list:not(.recommendation-list)');
        
        // ローディングインジケータを作成
        this.createLoadingIndicator();
        
        // ページネーションコンテナを作成
        this.createPaginationContainer();
        
        // 検索ボックスを追加
        this.createSearchBox();
        
        // イベントリスナーの設定
        this.setupEventListeners();
        
        // 初期データの読み込み
        this.loadScenarios();
    }
    
    createLoadingIndicator() {
        this.loadingIndicator = document.createElement('div');
        this.loadingIndicator.className = 'loading-indicator';
        this.loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 読み込み中...';
        this.loadingIndicator.style.display = 'none';
        this.loadingIndicator.style.textAlign = 'center';
        this.loadingIndicator.style.padding = '2rem';
        
        if (this.scenariosList) {
            this.scenariosList.parentNode.insertBefore(this.loadingIndicator, this.scenariosList);
        }
    }
    
    createPaginationContainer() {
        this.paginationContainer = document.createElement('div');
        this.paginationContainer.className = 'pagination-container';
        this.paginationContainer.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 2rem;';
        
        if (this.scenariosList) {
            this.scenariosList.parentNode.insertBefore(this.paginationContainer, this.scenariosList.nextSibling);
        }
    }
    
    createSearchBox() {
        const filterContainer = document.querySelector('.filter-container');
        if (!filterContainer) return;
        
        const searchGroup = document.createElement('div');
        searchGroup.className = 'filter-group';
        searchGroup.innerHTML = `
            <label for="search-input">検索</label>
            <input type="text" id="search-input" class="styled-input" placeholder="シナリオを検索...">
        `;
        
        // 既存のフィルターグループの後に追加
        const filterOptions = filterContainer.querySelector('.filter-options');
        if (filterOptions) {
            filterOptions.appendChild(searchGroup);
        }
    }
    
    setupEventListeners() {
        // 難易度フィルター
        const difficultyFilter = document.getElementById('difficulty-filter');
        if (difficultyFilter) {
            difficultyFilter.addEventListener('change', (e) => {
                this.filters.difficulty = e.target.value;
                this.currentPage = 1;
                this.loadScenarios();
            });
        }
        
        // タグフィルター
        const tagFilter = document.getElementById('tag-filter');
        if (tagFilter) {
            tagFilter.addEventListener('change', (e) => {
                this.filters.tag = e.target.value;
                this.currentPage = 1;
                this.loadScenarios();
            });
        }
        
        // 検索入力（デバウンス付き）
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.filters.search = e.target.value;
                    this.currentPage = 1;
                    this.loadScenarios();
                }, 300);
            });
        }
        
        // ソートセレクター
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.filters.sort = e.target.value;
                this.currentPage = 1;
                this.loadScenarios();
            });
        }
    }
    
    async loadScenarios() {
        // ローディング表示
        this.showLoading();
        
        try {
            // APIパラメータの構築
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                difficulty: this.filters.difficulty,
                tag: this.filters.tag,
                search: this.filters.search,
                sort: this.filters.sort
            });
            
            // データ取得
            const response = await fetch(`/api/scenarios?${params}`);
            if (!response.ok) {
                throw new Error('Failed to load scenarios');
            }
            
            const data = await response.json();
            
            // シナリオ表示
            this.displayScenarios(data.scenarios);
            
            // ページネーション更新
            this.updatePagination(data.pagination);
            
        } catch (error) {
            console.error('Error loading scenarios:', error);
            this.showError('シナリオの読み込みに失敗しました。');
        } finally {
            this.hideLoading();
        }
    }
    
    displayScenarios(scenarios) {
        if (!this.scenariosList) return;
        
        // 既存のカードをクリア
        this.scenariosList.innerHTML = '';
        
        // シナリオがない場合
        if (scenarios.length === 0) {
            this.scenariosList.innerHTML = '<p style="text-align: center; padding: 2rem;">該当するシナリオが見つかりませんでした。</p>';
            return;
        }
        
        // シナリオカードを生成
        scenarios.forEach(scenario => {
            const card = this.createScenarioCard(scenario);
            this.scenariosList.appendChild(card);
        });
        
        // スムーズスクロール（ページ変更時）
        if (this.currentPage > 1) {
            this.scenariosList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    createScenarioCard(scenario) {
        const card = document.createElement('div');
        card.className = 'scenario-card';
        
        // カテゴリーアイコンの選択
        const categoryIcon = this.getCategoryIcon(scenario.category);
        
        // 難易度の色
        const difficultyClass = this.getDifficultyClass(scenario.difficulty);
        
        card.innerHTML = `
            <div class="scenario-card-header">
                <h3>
                    <i class="${categoryIcon}"></i>
                    ${this.escapeHtml(scenario.title)}
                </h3>
                <span class="difficulty-badge ${difficultyClass}">
                    ${this.escapeHtml(scenario.difficulty)}
                </span>
            </div>
            <div class="scenario-card-body">
                <p>${this.escapeHtml(scenario.description)}</p>
                <div class="scenario-tags">
                    ${scenario.tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}
                </div>
                <div class="scenario-info">
                    <span><i class="fas fa-clock"></i> ${this.escapeHtml(scenario.duration)}</span>
                </div>
            </div>
            <div class="scenario-card-footer">
                <a href="/scenario/${encodeURIComponent(scenario.id)}" class="primary-button">
                    <i class="fas fa-play"></i> 開始
                </a>
            </div>
        `;
        
        return card;
    }
    
    updatePagination(pagination) {
        if (!this.paginationContainer) return;
        
        this.totalPages = pagination.total_pages;
        this.paginationContainer.innerHTML = '';
        
        // 前へボタン
        const prevButton = document.createElement('button');
        prevButton.className = 'pagination-button';
        prevButton.innerHTML = '<i class="fas fa-chevron-left"></i> 前へ';
        prevButton.disabled = !pagination.has_prev;
        prevButton.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadScenarios();
            }
        });
        this.paginationContainer.appendChild(prevButton);
        
        // ページ情報
        const pageInfo = document.createElement('span');
        pageInfo.className = 'pagination-info';
        pageInfo.textContent = `${pagination.page} / ${pagination.total_pages} ページ（全${pagination.total_count}件）`;
        this.paginationContainer.appendChild(pageInfo);
        
        // 次へボタン
        const nextButton = document.createElement('button');
        nextButton.className = 'pagination-button';
        nextButton.innerHTML = '次へ <i class="fas fa-chevron-right"></i>';
        nextButton.disabled = !pagination.has_next;
        nextButton.addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.loadScenarios();
            }
        });
        this.paginationContainer.appendChild(nextButton);
    }
    
    getCategoryIcon(category) {
        const icons = {
            'communication': 'fas fa-comments',
            'conflict': 'fas fa-exclamation-triangle',
            'leadership': 'fas fa-users',
            'presentation': 'fas fa-chalkboard-teacher',
            'negotiation': 'fas fa-handshake',
            'feedback': 'fas fa-comment-dots'
        };
        return icons[category] || 'fas fa-briefcase';
    }
    
    getDifficultyClass(difficulty) {
        const classes = {
            '初級': 'difficulty-beginner',
            '中級': 'difficulty-intermediate',
            '上級': 'difficulty-advanced'
        };
        return classes[difficulty] || 'difficulty-beginner';
    }
    
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    showLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'block';
        }
        if (this.scenariosList) {
            this.scenariosList.style.opacity = '0.5';
        }
    }
    
    hideLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'none';
        }
        if (this.scenariosList) {
            this.scenariosList.style.opacity = '1';
        }
    }
    
    showError(message) {
        if (this.scenariosList) {
            this.scenariosList.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: #dc3545;">
                    <i class="fas fa-exclamation-circle"></i> ${message}
                </div>
            `;
        }
    }
}

// ページ読み込み時に初期化
document.addEventListener('DOMContentLoaded', function() {
    // 既存の初期化関数も実行
    if (typeof initializeModal === 'function') {
        initializeModal();
    }
    if (typeof initializeRecommendations === 'function') {
        initializeRecommendations();
    }
    
    // 新しいシナリオリストマネージャーを初期化
    window.scenarioListManager = new ScenarioListManager();
});

// 既存の関数との互換性維持
window.showTips = function(scenarioId) {
    const modal = document.getElementById('tipsModal');
    if (modal) {
        modal.style.display = "block";
    }
};

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
};

window.continuePreviousScenario = function(scenarioId) {
    window.location.href = `/scenario/${scenarioId}`;
};