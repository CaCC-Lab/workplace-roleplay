/**
 * 仮想スクロール実装
 * 大量のシナリオを効率的に表示するための仮想スクロール機能
 */

class VirtualScroller {
    constructor(options) {
        this.containerSelector = options.containerSelector;
        this.itemHeight = options.itemHeight || 200; // 各シナリオカードの推定高さ
        this.buffer = options.buffer || 5; // 表示領域の前後に余分に表示する項目数
        this.items = [];
        this.filteredItems = [];
        this.visibleRange = { start: 0, end: 0 };
        
        this.container = document.querySelector(this.containerSelector);
        this.scrollContainer = null;
        this.contentContainer = null;
        
        this.renderItem = options.renderItem || this.defaultRenderItem;
        this.onScroll = this.handleScroll.bind(this);
        
        this.initialize();
    }
    
    initialize() {
        if (!this.container) {
            console.error('Virtual scroll container not found');
            return;
        }
        
        // スクロールコンテナの設定
        this.container.classList.add('virtual-scroll-enabled');
        
        // 既存のコンテンツを保存してクリア
        const existingContent = this.container.innerHTML;
        this.container.innerHTML = '';
        
        // コンテンツコンテナの作成
        this.contentContainer = document.createElement('div');
        this.contentContainer.className = 'virtual-scroll-container';
        this.contentContainer.style.position = 'relative';
        this.container.appendChild(this.contentContainer);
        
        // スクロールイベントのリスナー追加
        this.container.addEventListener('scroll', this.onScroll);
        
        // リサイズオブザーバーの設定
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                this.updateView();
            });
            this.resizeObserver.observe(this.container);
        }
    }
    
    setItems(items) {
        this.items = items;
        this.filteredItems = [...items];
        this.updateView();
    }
    
    filterItems(filterFn) {
        this.filteredItems = this.items.filter(filterFn);
        this.container.scrollTop = 0; // フィルター時は先頭にスクロール
        this.updateView();
    }
    
    sortItems(sortFn) {
        this.filteredItems.sort(sortFn);
        this.updateView();
    }
    
    handleScroll() {
        // スクロール処理のデバウンス
        if (this.scrollTimeout) {
            clearTimeout(this.scrollTimeout);
        }
        
        this.scrollTimeout = setTimeout(() => {
            this.updateView();
        }, 16); // 約60fps
    }
    
    updateView() {
        const scrollTop = this.container.scrollTop;
        const containerHeight = this.container.clientHeight;
        
        // 表示範囲の計算
        const startIndex = Math.max(0, Math.floor(scrollTop / this.itemHeight) - this.buffer);
        const endIndex = Math.min(
            this.filteredItems.length,
            Math.ceil((scrollTop + containerHeight) / this.itemHeight) + this.buffer
        );
        
        // 表示範囲が変わった場合のみ再レンダリング
        if (startIndex !== this.visibleRange.start || endIndex !== this.visibleRange.end) {
            this.visibleRange = { start: startIndex, end: endIndex };
            this.render();
        }
    }
    
    render() {
        // コンテンツの総高さを設定
        const totalHeight = this.filteredItems.length * this.itemHeight;
        this.contentContainer.style.height = `${totalHeight}px`;
        
        // 既存の要素をクリア
        this.contentContainer.innerHTML = '';
        
        // 表示範囲の要素のみをレンダリング
        for (let i = this.visibleRange.start; i < this.visibleRange.end; i++) {
            const item = this.filteredItems[i];
            if (!item) continue;
            
            const element = this.renderItem(item, i);
            element.style.position = 'absolute';
            element.style.top = `${i * this.itemHeight}px`;
            element.style.left = '0';
            element.style.right = '0';
            
            this.contentContainer.appendChild(element);
        }
        
        // デバッグ情報
        console.log(`Rendering items ${this.visibleRange.start} to ${this.visibleRange.end} of ${this.filteredItems.length} total`);
    }
    
    defaultRenderItem(item, index) {
        const div = document.createElement('div');
        div.className = 'virtual-scroll-item';
        div.textContent = `Item ${index}`;
        return div;
    }
    
    destroy() {
        if (this.container) {
            this.container.removeEventListener('scroll', this.onScroll);
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        if (this.scrollTimeout) {
            clearTimeout(this.scrollTimeout);
        }
    }
}

// シナリオカード用の仮想スクロール設定
function initializeScenarioVirtualScroll(scenarios) {
    const virtualScroller = new VirtualScroller({
        containerSelector: '.scenarios-list',
        itemHeight: 250, // シナリオカードの推定高さ
        buffer: 3,
        renderItem: (scenario, index) => {
            return createScenarioCard(scenario);
        }
    });
    
    // シナリオデータを設定
    const scenarioArray = Object.entries(scenarios).map(([id, data]) => ({
        id,
        ...data
    }));
    
    virtualScroller.setItems(scenarioArray);
    
    return virtualScroller;
}

// シナリオカードの作成
function createScenarioCard(scenario) {
    const card = document.createElement('div');
    card.className = 'scenario-card';
    
    // カテゴリアイコンの決定
    let categoryIcon = 'fa-briefcase';
    if (scenario.category === 'communication') categoryIcon = 'fa-comments';
    else if (scenario.category === 'conflict') categoryIcon = 'fa-exclamation-triangle';
    else if (scenario.category === 'negotiation') categoryIcon = 'fa-handshake';
    else if (scenario.category === 'leadership') categoryIcon = 'fa-users';
    else if (scenario.category === 'feedback') categoryIcon = 'fa-comment-dots';
    
    // 難易度表示の決定
    let difficultyDisplay = '';
    let difficultyIcon = '';
    if (scenario.difficulty === 'pre-beginner') {
        difficultyDisplay = '入門';
        difficultyIcon = '<i class="fas fa-seedling"></i>';
    } else if (scenario.difficulty === 'beginner') {
        difficultyDisplay = '初級';
        difficultyIcon = '<i class="fas fa-star"></i>';
    } else if (scenario.difficulty === 'intermediate') {
        difficultyDisplay = '中級';
        difficultyIcon = '<i class="fas fa-star"></i><i class="fas fa-star"></i>';
    } else if (scenario.difficulty === 'advanced') {
        difficultyDisplay = '上級';
        difficultyIcon = '<i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i>';
    }
    
    card.innerHTML = `
        <div class="scenario-card-header">
            <h3>
                <i class="fas ${categoryIcon}"></i>
                ${scenario.title}
            </h3>
            <span class="difficulty-badge difficulty-${scenario.difficulty}">
                ${difficultyIcon} ${difficultyDisplay}
            </span>
        </div>
        <div class="scenario-content">
            <p class="scenario-description">${scenario.description}</p>
            <div class="scenario-tags">
                ${scenario.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        </div>
        <div class="scenario-card-footer">
            <a href="/scenario/${scenario.id}" class="primary-button">
                <i class="fas fa-play"></i> 開始
            </a>
        </div>
    `;
    
    return card;
}

// エクスポート（グローバルスコープで利用可能にする）
window.VirtualScroller = VirtualScroller;
window.initializeScenarioVirtualScroll = initializeScenarioVirtualScroll;