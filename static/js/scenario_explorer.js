/**
 * 高度シナリオ探索・フィルタリングシステム
 * 
 * 5AI協調開発:
 * - Claude 4: 情報アーキテクチャ設計
 * - Gemini 2.5: UXベストプラクティス調査
 * - Qwen3-Coder: JavaScript実装
 * - Codex: 論理的ナビゲーション
 * - Cursor: インタラクティブUI
 */

class ScenarioExplorer {
    constructor() {
        this.scenarios = [];
        this.filteredScenarios = [];
        this.currentFilters = {
            category: null,
            difficulty: null,
            tags: [],
            maxDuration: null,
            searchQuery: ''
        };
        
        this.categories = {
            'basic_comm': {
                name: '基本コミュニケーション',
                icon: '🏢',
                color: 'blue',
                description: '職場での基礎的な対話スキル'
            },
            'leadership': {
                name: 'リーダーシップ',
                icon: '💼', 
                color: 'green',
                description: 'チーム運営と指導力'
            },
            'harassment': {
                name: 'ハラスメント対応',
                icon: '⚖️',
                color: 'red', 
                description: '適切な職場環境維持'
            },
            'special': {
                name: '特殊シチュエーション',
                icon: '🎭',
                color: 'purple',
                description: '複雑な職場状況への対応'
            }
        };
        
        this.init();
    }
    
    async init() {
        await this.loadScenarios();
        this.renderInterface();
        this.attachEventListeners();
        this.renderScenarios();
    }
    
    async loadScenarios() {
        try {
            const response = await fetch('/api/scenarios');
            this.scenarios = await response.json();
            this.filteredScenarios = [...this.scenarios];
        } catch (error) {
            console.error('Failed to load scenarios:', error);
        }
    }
    
    renderInterface() {
        const container = document.getElementById('scenario-explorer');
        container.innerHTML = `
            <div class="scenario-explorer">
                <!-- ヘッダー部分 -->
                <div class="explorer-header">
                    <h2>シナリオを探索</h2>
                    <div class="view-options">
                        <button class="view-btn active" data-view="cards">
                            <i class="icon-grid"></i> カード表示
                        </button>
                        <button class="view-btn" data-view="list">
                            <i class="icon-list"></i> リスト表示
                        </button>
                    </div>
                </div>
                
                <!-- カテゴリ選択 -->
                <div class="category-selector">
                    <div class="category-cards">
                        ${this.renderCategoryCards()}
                    </div>
                </div>
                
                <!-- フィルター・検索バー -->
                <div class="filter-bar">
                    <div class="search-box">
                        <i class="icon-search"></i>
                        <input type="text" id="scenario-search" 
                               placeholder="シナリオを検索...">
                    </div>
                    
                    <div class="filter-controls">
                        <select id="difficulty-filter">
                            <option value="">全ての難易度</option>
                            <option value="初級">初級</option>
                            <option value="中級">中級</option>
                            <option value="上級">上級</option>
                        </select>
                        
                        <select id="duration-filter">
                            <option value="">全ての時間</option>
                            <option value="15">15分以内</option>
                            <option value="30">30分以内</option>
                            <option value="60">1時間以内</option>
                        </select>
                        
                        <button id="clear-filters" class="clear-btn">
                            <i class="icon-x"></i> フィルターをクリア
                        </button>
                    </div>
                </div>
                
                <!-- タグクラウド -->
                <div class="tag-cloud">
                    <div class="tag-container" id="tag-container">
                        ${this.renderTagCloud()}
                    </div>
                </div>
                
                <!-- 結果統計 -->
                <div class="results-info">
                    <span id="results-count">0件のシナリオが見つかりました</span>
                    <div class="sort-options">
                        <label>並び順:</label>
                        <select id="sort-select">
                            <option value="relevance">関連度</option>
                            <option value="difficulty">難易度</option>
                            <option value="duration">所要時間</option>
                            <option value="title">タイトル順</option>
                        </select>
                    </div>
                </div>
                
                <!-- シナリオ表示エリア -->
                <div class="scenarios-container" id="scenarios-container">
                    <!-- ここにシナリオが表示される -->
                </div>
                
                <!-- ページネーション -->
                <div class="pagination" id="pagination">
                    <!-- ページネーションボタン -->
                </div>
            </div>
        `;
    }
    
    renderCategoryCards() {
        return Object.entries(this.categories).map(([key, category]) => `
            <div class="category-card" data-category="${key}">
                <div class="category-icon ${category.color}">${category.icon}</div>
                <h3>${category.name}</h3>
                <p>${category.description}</p>
                <div class="scenario-count">
                    ${this.getScenarioCountByCategory(key)}件のシナリオ
                </div>
            </div>
        `).join('');
    }
    
    renderTagCloud() {
        const allTags = this.getAllTags();
        const tagCounts = this.getTagCounts(allTags);
        
        return Object.entries(tagCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 20)  // 上位20タグを表示
            .map(([tag, count]) => `
                <span class="tag-item" data-tag="${tag}">
                    ${tag} <span class="tag-count">(${count})</span>
                </span>
            `).join('');
    }
    
    renderScenarios() {
        const container = document.getElementById('scenarios-container');
        const viewMode = document.querySelector('.view-btn.active').dataset.view;
        
        if (this.filteredScenarios.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <h3>該当するシナリオが見つかりません</h3>
                    <p>フィルター条件を変更して再度お試しください</p>
                </div>
            `;
            return;
        }
        
        if (viewMode === 'cards') {
            container.innerHTML = this.renderScenarioCards();
        } else {
            container.innerHTML = this.renderScenarioList();
        }
        
        // 結果数の更新
        document.getElementById('results-count').textContent = 
            `${this.filteredScenarios.length}件のシナリオが見つかりました`;
    }
    
    renderScenarioCards() {
        return `
            <div class="scenario-cards">
                ${this.filteredScenarios.map(scenario => `
                    <div class="scenario-card" data-scenario-id="${scenario.id}">
                        <div class="card-header">
                            <div class="difficulty-badge ${scenario.difficulty}">
                                ${scenario.difficulty}
                            </div>
                            <div class="duration-badge">
                                <i class="icon-clock"></i>
                                ${scenario.estimated_duration || 15}分
                            </div>
                        </div>
                        
                        <div class="card-content">
                            <h3 class="scenario-title">${scenario.title}</h3>
                            <p class="scenario-description">
                                ${scenario.description.substring(0, 100)}...
                            </p>
                            
                            <div class="scenario-meta">
                                <div class="roles">
                                    <span class="user-role">あなた: ${scenario.user_role || 'プレイヤー'}</span>
                                    <span class="ai-role">相手: ${scenario.ai_role || 'AI'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card-tags">
                            ${(scenario.tags || []).map(tag => 
                                `<span class="tag">${tag}</span>`
                            ).join('')}
                        </div>
                        
                        <div class="card-actions">
                            <button class="btn btn-primary start-scenario" 
                                    data-scenario-id="${scenario.id}">
                                <i class="icon-play"></i> 開始
                            </button>
                            <button class="btn btn-secondary scenario-details" 
                                    data-scenario-id="${scenario.id}">
                                <i class="icon-info"></i> 詳細
                            </button>
                            <button class="btn btn-ghost bookmark-scenario"
                                    data-scenario-id="${scenario.id}">
                                <i class="icon-bookmark"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    renderScenarioList() {
        return `
            <div class="scenario-list">
                ${this.filteredScenarios.map(scenario => `
                    <div class="scenario-list-item" data-scenario-id="${scenario.id}">
                        <div class="list-item-main">
                            <div class="item-header">
                                <h3 class="scenario-title">${scenario.title}</h3>
                                <div class="item-badges">
                                    <span class="difficulty-badge ${scenario.difficulty}">
                                        ${scenario.difficulty}
                                    </span>
                                    <span class="duration-badge">
                                        ${scenario.estimated_duration || 15}分
                                    </span>
                                </div>
                            </div>
                            
                            <p class="scenario-description">${scenario.description}</p>
                            
                            <div class="item-tags">
                                ${(scenario.tags || []).map(tag => 
                                    `<span class="tag">${tag}</span>`
                                ).join('')}
                            </div>
                        </div>
                        
                        <div class="list-item-actions">
                            <button class="btn btn-primary start-scenario" 
                                    data-scenario-id="${scenario.id}">
                                開始
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    attachEventListeners() {
        // カテゴリ選択
        document.addEventListener('click', (e) => {
            if (e.target.closest('.category-card')) {
                const categoryKey = e.target.closest('.category-card').dataset.category;
                this.setFilter('category', categoryKey);
            }
        });
        
        // 検索
        document.getElementById('scenario-search').addEventListener('input', (e) => {
            this.setFilter('searchQuery', e.target.value);
        });
        
        // フィルター
        document.getElementById('difficulty-filter').addEventListener('change', (e) => {
            this.setFilter('difficulty', e.target.value);
        });
        
        document.getElementById('duration-filter').addEventListener('change', (e) => {
            this.setFilter('maxDuration', parseInt(e.target.value) || null);
        });
        
        // タグクリック
        document.addEventListener('click', (e) => {
            if (e.target.closest('.tag-item')) {
                const tag = e.target.closest('.tag-item').dataset.tag;
                this.toggleTag(tag);
            }
        });
        
        // フィルタークリア
        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });
        
        // 表示モード切り替え
        document.addEventListener('click', (e) => {
            if (e.target.closest('.view-btn')) {
                const viewBtn = e.target.closest('.view-btn');
                document.querySelectorAll('.view-btn').forEach(btn => 
                    btn.classList.remove('active'));
                viewBtn.classList.add('active');
                this.renderScenarios();
            }
        });
        
        // ソート
        document.getElementById('sort-select').addEventListener('change', (e) => {
            this.sortScenarios(e.target.value);
        });
        
        // シナリオアクション
        document.addEventListener('click', (e) => {
            if (e.target.closest('.start-scenario')) {
                const scenarioId = e.target.closest('.start-scenario').dataset.scenarioId;
                this.startScenario(scenarioId);
            }
            
            if (e.target.closest('.scenario-details')) {
                const scenarioId = e.target.closest('.scenario-details').dataset.scenarioId;
                this.showScenarioDetails(scenarioId);
            }
        });
    }
    
    setFilter(filterType, value) {
        this.currentFilters[filterType] = value;
        this.applyFilters();
        this.renderScenarios();
        this.updateURL();
    }
    
    toggleTag(tag) {
        const tagIndex = this.currentFilters.tags.indexOf(tag);
        if (tagIndex === -1) {
            this.currentFilters.tags.push(tag);
        } else {
            this.currentFilters.tags.splice(tagIndex, 1);
        }
        this.applyFilters();
        this.renderScenarios();
        this.updateTagVisuals();
    }
    
    applyFilters() {
        this.filteredScenarios = this.scenarios.filter(scenario => {
            // カテゴリフィルター
            if (this.currentFilters.category && 
                scenario.category !== this.currentFilters.category) {
                return false;
            }
            
            // 難易度フィルター
            if (this.currentFilters.difficulty && 
                scenario.difficulty !== this.currentFilters.difficulty) {
                return false;
            }
            
            // 時間フィルター
            if (this.currentFilters.maxDuration && 
                scenario.estimated_duration > this.currentFilters.maxDuration) {
                return false;
            }
            
            // タグフィルター
            if (this.currentFilters.tags.length > 0) {
                const hasMatchingTag = this.currentFilters.tags.some(tag => 
                    scenario.tags && scenario.tags.includes(tag));
                if (!hasMatchingTag) return false;
            }
            
            // 検索クエリ
            if (this.currentFilters.searchQuery) {
                const query = this.currentFilters.searchQuery.toLowerCase();
                const searchableText = [
                    scenario.title,
                    scenario.description,
                    ...(scenario.tags || [])
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(query)) return false;
            }
            
            return true;
        });
    }
    
    clearFilters() {
        this.currentFilters = {
            category: null,
            difficulty: null,
            tags: [],
            maxDuration: null,
            searchQuery: ''
        };
        
        // UI要素のリセット
        document.getElementById('scenario-search').value = '';
        document.getElementById('difficulty-filter').value = '';
        document.getElementById('duration-filter').value = '';
        
        this.applyFilters();
        this.renderScenarios();
        this.updateTagVisuals();
        this.updateURL();
    }
    
    sortScenarios(sortBy) {
        switch (sortBy) {
            case 'difficulty':
                const difficultyOrder = {'初級': 1, '中級': 2, '上級': 3};
                this.filteredScenarios.sort((a, b) => 
                    difficultyOrder[a.difficulty] - difficultyOrder[b.difficulty]);
                break;
                
            case 'duration':
                this.filteredScenarios.sort((a, b) => 
                    (a.estimated_duration || 15) - (b.estimated_duration || 15));
                break;
                
            case 'title':
                this.filteredScenarios.sort((a, b) => 
                    a.title.localeCompare(b.title, 'ja'));
                break;
                
            default: // relevance
                // 関連度ソート（検索クエリがある場合）
                if (this.currentFilters.searchQuery) {
                    this.sortByRelevance();
                }
                break;
        }
        
        this.renderScenarios();
    }
    
    sortByRelevance() {
        const query = this.currentFilters.searchQuery.toLowerCase();
        this.filteredScenarios.sort((a, b) => {
            const scoreA = this.calculateRelevanceScore(a, query);
            const scoreB = this.calculateRelevanceScore(b, query);
            return scoreB - scoreA;
        });
    }
    
    calculateRelevanceScore(scenario, query) {
        let score = 0;
        
        // タイトル一致（最高点）
        if (scenario.title.toLowerCase().includes(query)) {
            score += 10;
        }
        
        // 説明文一致
        if (scenario.description.toLowerCase().includes(query)) {
            score += 5;
        }
        
        // タグ一致
        if (scenario.tags && scenario.tags.some(tag => 
            tag.toLowerCase().includes(query))) {
            score += 3;
        }
        
        return score;
    }
    
    // ヘルパーメソッド
    getScenarioCountByCategory(categoryKey) {
        return this.scenarios.filter(s => s.category === categoryKey).length;
    }
    
    getAllTags() {
        const tags = new Set();
        this.scenarios.forEach(scenario => {
            if (scenario.tags) {
                scenario.tags.forEach(tag => tags.add(tag));
            }
        });
        return Array.from(tags);
    }
    
    getTagCounts(tags) {
        const counts = {};
        tags.forEach(tag => {
            counts[tag] = this.scenarios.filter(scenario => 
                scenario.tags && scenario.tags.includes(tag)
            ).length;
        });
        return counts;
    }
    
    updateTagVisuals() {
        document.querySelectorAll('.tag-item').forEach(tagElement => {
            const isSelected = this.currentFilters.tags.includes(tagElement.dataset.tag);
            tagElement.classList.toggle('selected', isSelected);
        });
    }
    
    updateURL() {
        const params = new URLSearchParams();
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            if (value !== null && value !== '' && 
                !(Array.isArray(value) && value.length === 0)) {
                if (Array.isArray(value)) {
                    params.set(key, value.join(','));
                } else {
                    params.set(key, value);
                }
            }
        });
        
        const newURL = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newURL);
    }
    
    startScenario(scenarioId) {
        // シナリオ開始処理
        window.location.href = `/scenario/${scenarioId}`;
    }
    
    showScenarioDetails(scenarioId) {
        // 詳細モーダル表示
        const scenario = this.scenarios.find(s => s.id === scenarioId);
        if (scenario) {
            this.showModal(this.renderScenarioModal(scenario));
        }
    }
    
    renderScenarioModal(scenario) {
        return `
            <div class="scenario-modal">
                <div class="modal-header">
                    <h2>${scenario.title}</h2>
                    <button class="modal-close">&times;</button>
                </div>
                
                <div class="modal-content">
                    <div class="scenario-details">
                        <div class="detail-section">
                            <h3>概要</h3>
                            <p>${scenario.description}</p>
                        </div>
                        
                        <div class="detail-section">
                            <h3>学習目標</h3>
                            <ul>
                                ${(scenario.learning_points || []).map(point => 
                                    `<li>${point}</li>`
                                ).join('')}
                            </ul>
                        </div>
                        
                        <div class="detail-section">
                            <h3>役割設定</h3>
                            <div class="roles-detail">
                                <div class="role-item">
                                    <strong>あなたの役割:</strong> ${scenario.user_role || 'プレイヤー'}
                                </div>
                                <div class="role-item">
                                    <strong>相手の役割:</strong> ${scenario.ai_role || 'AI'}
                                </div>
                            </div>
                        </div>
                        
                        <div class="detail-meta">
                            <div class="meta-item">
                                <strong>難易度:</strong> 
                                <span class="difficulty-badge ${scenario.difficulty}">
                                    ${scenario.difficulty}
                                </span>
                            </div>
                            <div class="meta-item">
                                <strong>推定時間:</strong> ${scenario.estimated_duration || 15}分
                            </div>
                            <div class="meta-item">
                                <strong>タグ:</strong>
                                <div class="tags">
                                    ${(scenario.tags || []).map(tag => 
                                        `<span class="tag">${tag}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="modal-actions">
                    <button class="btn btn-primary" onclick="scenarioExplorer.startScenario('${scenario.id}')">
                        <i class="icon-play"></i> このシナリオを開始
                    </button>
                    <button class="btn btn-secondary modal-close">
                        キャンセル
                    </button>
                </div>
            </div>
        `;
    }
    
    showModal(content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = content;
        
        document.body.appendChild(modal);
        
        // モーダルクローズイベント
        modal.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay') || 
                e.target.classList.contains('modal-close')) {
                modal.remove();
            }
        });
    }
}

// グローバル初期化
let scenarioExplorer;
document.addEventListener('DOMContentLoaded', () => {
    scenarioExplorer = new ScenarioExplorer();
});