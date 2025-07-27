// リアルタイムコーチングクライアント

class RealtimeCoachingClient {
    constructor() {
        this.socket = null;
        this.sessionId = null;
        this.coachingEnabled = false;
        this.hintLevel = 'basic';
        this.typingTimer = null;
        this.lastTypingTime = 0;
        this.currentHints = [];
        
        this.init();
    }
    
    init() {
        // Socket.IOの初期化
        if (typeof io !== 'undefined') {
            this.socket = io();
            this.setupSocketHandlers();
            this.setupDOMHandlers();
            console.log('Real-time coaching client initialized');
        } else {
            console.warn('Socket.IO not found, real-time coaching disabled');
        }
    }
    
    setupSocketHandlers() {
        // 接続時の設定受信
        this.socket.on('coaching_config', (config) => {
            this.coachingEnabled = config.enabled;
            this.hintLevel = config.hint_level || 'basic';
            this.sessionId = config.session_id;
            
            console.log('Coaching config received:', config);
            
            if (this.coachingEnabled) {
                this.showCoachingStatus(true);
            }
        });
        
        // 入力中のヒント受信
        this.socket.on('typing_hints', (data) => {
            if (this.coachingEnabled && data.hints && data.hints.length > 0) {
                this.displayTypingHints(data.hints, data.confidence);
            }
        });
        
        // メッセージ分析結果受信
        this.socket.on('message_analysis', (data) => {
            if (this.coachingEnabled) {
                this.displayMessageAnalysis(data.analysis, data.score_impact);
                this.showRecommendations(data.recommendations);
            }
        });
        
        // シナリオ固有ヒント受信
        this.socket.on('scenario_hints', (data) => {
            if (this.coachingEnabled && data.hints && data.hints.length > 0) {
                this.displayScenarioHints(data.hints);
            }
        });
        
        // システムメッセージ受信
        this.socket.on('system_message', (data) => {
            this.showSystemMessage(data.message, data.type);
        });
        
        // エラーハンドリング
        this.socket.on('connect_error', (error) => {
            console.error('Socket connection error:', error);
            this.showCoachingStatus(false, '接続エラー');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Socket disconnected');
            this.showCoachingStatus(false, '切断されました');
        });
    }
    
    setupDOMHandlers() {
        // メッセージ入力時のリアルタイムヒント
        const messageInputs = document.querySelectorAll('textarea[id*="message"], input[id*="message"]');
        messageInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.handleTyping(e.target.value);
            });
            
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    setTimeout(() => {
                        this.handleMessageSent(e.target.value);
                    }, 100);
                }
            });
        });
        
        // 送信ボタンのクリック
        const sendButtons = document.querySelectorAll('button[onclick*="send"], button[id*="send"]');
        sendButtons.forEach(button => {
            button.addEventListener('click', () => {
                setTimeout(() => {
                    const messageInput = this.findMessageInput();
                    if (messageInput) {
                        this.handleMessageSent(messageInput.value);
                    }
                }, 100);
            });
        });
        
        // シナリオ開始時のヒントリクエスト
        const scenarioId = this.getScenarioId();
        if (scenarioId) {
            setTimeout(() => {
                this.requestScenarioHints(scenarioId);
            }, 2000);
        }
    }
    
    handleTyping(message) {
        if (!this.coachingEnabled || !message || message.length < 10) {
            return;
        }
        
        // デバウンス処理
        clearTimeout(this.typingTimer);
        this.typingTimer = setTimeout(() => {
            const now = Date.now();
            if (now - this.lastTypingTime > 1000) { // 1秒間障で送信
                this.sendTypingEvent(message);
                this.lastTypingTime = now;
            }
        }, 500);
    }
    
    sendTypingEvent(message) {
        if (this.socket && this.sessionId) {
            this.socket.emit('message_typing', {
                session_id: this.sessionId,
                message: message,
                context: this.getContext()
            });
        }
    }
    
    handleMessageSent(message) {
        if (!this.coachingEnabled || !message) {
            return;
        }
        
        // 入力中のヒントをクリア
        this.clearTypingHints();
        
        if (this.socket && this.sessionId) {
            this.socket.emit('message_sent', {
                session_id: this.sessionId,
                message: message,
                context: this.getContext()
            });
        }
    }
    
    getContext() {
        return {
            page_type: this.getPageType(),
            scenario_id: this.getScenarioId(),
            chat_type: this.getChatType(),
            timestamp: new Date().toISOString()
        };
    }
    
    getPageType() {
        const path = window.location.pathname;
        if (path.includes('/scenario')) return 'scenario';
        if (path.includes('/chat')) return 'chat';
        if (path.includes('/watch')) return 'watch';
        return 'unknown';
    }
    
    getScenarioId() {
        const match = window.location.pathname.match(/\/scenario\/(\w+)/);
        return match ? match[1] : null;
    }
    
    getChatType() {
        // chat_settingsから取得、またはDOMから推定
        return 'general';
    }
    
    findMessageInput() {
        return document.querySelector('textarea[id*="message"], input[id*="message"]');
    }
    
    displayTypingHints(hints, confidence) {
        // 既存のヒントをクリア
        this.clearTypingHints();
        
        hints.forEach((hint, index) => {
            if (hint.confidence > 0.5) { // 信頼度の闾値
                setTimeout(() => {
                    this.showHint(hint, 'typing');
                }, index * 200); // 遅延表示
            }
        });
    }
    
    displayMessageAnalysis(analysis, scoreImpact) {
        // メッセージ分析結果を表示
        if (analysis.overall_rating === 'needs_improvement') {
            this.showAnalysisFeedback(analysis, scoreImpact);
        } else if (analysis.overall_rating === 'excellent') {
            this.showPositiveFeedback(analysis);
        }
    }
    
    showRecommendations(recommendations) {
        if (recommendations && recommendations.length > 0) {
            recommendations.forEach((rec, index) => {
                if (rec.priority === 'high') {
                    setTimeout(() => {
                        this.showRecommendation(rec);
                    }, (index + 1) * 1000);
                }
            });
        }
    }
    
    displayScenarioHints(hints) {
        hints.forEach((hint, index) => {
            setTimeout(() => {
                this.showHint(hint, 'scenario');
            }, index * 300);
        });
    }
    
    showHint(hint, type) {
        const hintId = `hint-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        const hintElement = document.createElement('div');
        hintElement.id = hintId;
        hintElement.className = `coaching-hint ${type}-hint`;
        hintElement.innerHTML = `
            <div class="hint-content">
                <div class="hint-header">
                    <i class="fas fa-lightbulb"></i>
                    <span class="hint-title">${this.getHintTitle(hint.skill)}</span>
                    <button class="hint-close" onclick="realtimeCoaching.dismissHint('${hintId}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="hint-message">${hint.suggestion}</div>
                ${hint.example ? `<div class="hint-example">例: ${hint.example}</div>` : ''}
                <div class="hint-actions">
                    <button class="hint-action helpful" onclick="realtimeCoaching.hintFeedback('${hintId}', 'helpful')">
                        <i class="fas fa-thumbs-up"></i>
                    </button>
                    <button class="hint-action not-helpful" onclick="realtimeCoaching.hintFeedback('${hintId}', 'not_helpful')">
                        <i class="fas fa-thumbs-down"></i>
                    </button>
                </div>
            </div>
        `;
        
        // ヒントを表示するコンテナを取得または作成
        let hintsContainer = document.getElementById('coaching-hints-container');
        if (!hintsContainer) {
            hintsContainer = document.createElement('div');
            hintsContainer.id = 'coaching-hints-container';
            hintsContainer.className = 'coaching-hints-container';
            document.body.appendChild(hintsContainer);
        }
        
        hintsContainer.appendChild(hintElement);
        this.currentHints.push(hintId);
        
        // 自動消去タイマー
        setTimeout(() => {
            this.dismissHint(hintId);
        }, 15000); // 15秒後に自動消去
        
        // WebSocketにヒント表示を通知
        if (this.socket) {
            this.socket.emit('hint_interaction', {
                session_id: this.sessionId,
                action: 'shown',
                hint_id: hintId
            });
        }
    }
    
    getHintTitle(skill) {
        const titles = {
            'empathy': '🤝 共感力のヒント',
            'clarity': '📝 明確性のヒント',
            'active_listening': '👂 傾聴力のヒント',
            'adaptability': '🔄 適応力のヒント',
            'positivity': '✨ 前向きさのヒント',
            'professionalism': '💼 プロフェッショナリズムのヒント'
        };
        return titles[skill] || '💡 コーチングヒント';
    }
    
    dismissHint(hintId) {
        const hintElement = document.getElementById(hintId);
        if (hintElement) {
            hintElement.classList.add('fade-out');
            setTimeout(() => {
                hintElement.remove();
            }, 300);
            
            // リストから削除
            const index = this.currentHints.indexOf(hintId);
            if (index > -1) {
                this.currentHints.splice(index, 1);
            }
            
            // WebSocketに通知
            if (this.socket) {
                this.socket.emit('hint_interaction', {
                    session_id: this.sessionId,
                    action: 'dismissed',
                    hint_id: hintId
                });
            }
        }
    }
    
    hintFeedback(hintId, feedbackType) {
        // フィードバックを送信
        fetch('/api/feedback/hint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                hint_id: hintId,
                feedback_type: feedbackType,
                context: 'after_coaching_hint'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showFeedbackThanks();
                this.dismissHint(hintId);
                
                // WebSocketに通知
                if (this.socket) {
                    this.socket.emit('hint_interaction', {
                        session_id: this.sessionId,
                        action: 'feedback_submitted',
                        hint_id: hintId,
                        feedback_type: feedbackType
                    });
                }
            }
        })
        .catch(error => {
            console.error('Feedback error:', error);
        });
    }
    
    clearTypingHints() {
        const typingHints = document.querySelectorAll('.typing-hint');
        typingHints.forEach(hint => {
            hint.classList.add('fade-out');
            setTimeout(() => hint.remove(), 300);
        });
    }
    
    showAnalysiseFeedback(analysis, scoreImpact) {
        const feedbackElement = document.createElement('div');
        feedbackElement.className = 'analysis-feedback';
        feedbackElement.innerHTML = `
            <div class="feedback-content">
                <h4>メッセージ分析結果</h4>
                <p>今回のメッセージは改善の余地があります。</p>
                <div class="score-impact">
                    ${Object.entries(scoreImpact).map(([skill, impact]) => 
                        `<div class="impact-item">
                            <span class="skill">${this.getSkillName(skill)}</span>
                            <span class="impact ${impact > 0 ? 'positive' : 'negative'}">
                                ${impact > 0 ? '+' : ''}${impact.toFixed(1)}
                            </span>
                        </div>`
                    ).join('')}
                </div>
            </div>
        `;
        
        this.showTemporaryFeedback(feedbackElement, 8000);
    }
    
    showPositiveFeedback(analysis) {
        const feedbackElement = document.createElement('div');
        feedbackElement.className = 'positive-feedback';
        feedbackElement.innerHTML = `
            <div class="feedback-content">
                <i class="fas fa-star"></i>
                <h4>素晴らしいメッセージです！</h4>
                <p>特にコミュニケーションスキルが光っていました。</p>
            </div>
        `;
        
        this.showTemporaryFeedback(feedbackElement, 5000);
    }
    
    showRecommendation(recommendation) {
        const recElement = document.createElement('div');
        recElement.className = 'coaching-recommendation';
        recElement.innerHTML = `
            <div class="recommendation-content">
                <i class="fas fa-arrow-up"></i>
                <div class="rec-text">
                    <strong>推奨:</strong> ${recommendation.hint}
                    ${recommendation.example ? `<br><em>例: ${recommendation.example}</em>` : ''}
                </div>
            </div>
        `;
        
        this.showTemporaryFeedback(recElement, 6000);
    }
    
    showTemporaryFeedback(element, duration) {
        let feedbackContainer = document.getElementById('coaching-feedback-container');
        if (!feedbackContainer) {
            feedbackContainer = document.createElement('div');
            feedbackContainer.id = 'coaching-feedback-container';
            feedbackContainer.className = 'coaching-feedback-container';
            document.body.appendChild(feedbackContainer);
        }
        
        feedbackContainer.appendChild(element);
        
        setTimeout(() => {
            element.classList.add('fade-out');
            setTimeout(() => element.remove(), 300);
        }, duration);
    }
    
    showFeedbackThanks() {
        const thanksElement = document.createElement('div');
        thanksElement.className = 'feedback-thanks';
        thanksElement.innerHTML = `
            <div class="thanks-content">
                <i class="fas fa-check-circle"></i>
                <p>フィードバックありがとうございます！</p>
            </div>
        `;
        
        this.showTemporaryFeedback(thanksElement, 3000);
    }
    
    showCoachingStatus(enabled, message = '') {
        let statusElement = document.getElementById('coaching-status');
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = 'coaching-status';
            statusElement.className = 'coaching-status';
            document.body.appendChild(statusElement);
        }
        
        statusElement.className = `coaching-status ${enabled ? 'enabled' : 'disabled'}`;
        statusElement.innerHTML = `
            <div class="status-content">
                <i class="fas ${enabled ? 'fa-robot' : 'fa-robot'}"></i>
                <span>${enabled ? 'AIコーチング有効' : 'AIコーチング無効'}</span>
                ${message ? `<small>${message}</small>` : ''}
            </div>
        `;
        
        if (!enabled && message) {
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 5000);
        }
    }
    
    showSystemMessage(message, type) {
        const alertClass = {
            'info': 'alert-info',
            'warning': 'alert-warning',
            'error': 'alert-danger'
        }[type] || 'alert-info';
        
        const messageElement = document.createElement('div');
        messageElement.className = `alert ${alertClass} system-message`;
        messageElement.innerHTML = `
            <i class="fas fa-info-circle"></i>
            <span>${message}</span>
            <button class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(messageElement);
        
        setTimeout(() => {
            messageElement.classList.add('fade-out');
            setTimeout(() => messageElement.remove(), 300);
        }, 8000);
    }
    
    requestScenarioHints(scenarioId) {
        if (this.socket && this.coachingEnabled) {
            this.socket.emit('request_scenario_hints', {
                scenario_id: scenarioId,
                context: this.getContext()
            });
        }
    }
    
    getSkillName(skill) {
        const skillNames = {
            'empathy': '共感力',
            'clarity': '明確性',
            'active_listening': '傾聴力',
            'adaptability': '適応力',
            'positivity': '前向きさ',
            'professionalism': 'プロフェッショナリズム'
        };
        return skillNames[skill] || skill;
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// CSSスタイルを動的に追加
const coachingStyles = document.createElement('style');
coachingStyles.textContent = `
    .coaching-hints-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        max-width: 300px;
    }
    
    .coaching-hint {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        margin-bottom: 10px;
        animation: slideIn 0.3s ease-out;
        border-left: 4px solid #007bff;
    }
    
    .coaching-hint.typing-hint {
        border-left-color: #28a745;
    }
    
    .coaching-hint.scenario-hint {
        border-left-color: #ffc107;
    }
    
    .hint-content {
        padding: 15px;
    }
    
    .hint-header {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        font-weight: bold;
        font-size: 14px;
    }
    
    .hint-header i {
        margin-right: 8px;
        color: #007bff;
    }
    
    .hint-close {
        margin-left: auto;
        background: none;
        border: none;
        color: #999;
        cursor: pointer;
        font-size: 12px;
    }
    
    .hint-message {
        font-size: 13px;
        line-height: 1.4;
        margin-bottom: 8px;
        color: #333;
    }
    
    .hint-example {
        font-size: 12px;
        color: #666;
        font-style: italic;
        background: #f8f9fa;
        padding: 6px 8px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    
    .hint-actions {
        display: flex;
        gap: 8px;
    }
    
    .hint-action {
        padding: 4px 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background: white;
        cursor: pointer;
        font-size: 11px;
        transition: all 0.2s;
    }
    
    .hint-action.helpful:hover {
        background: #d4edda;
        border-color: #28a745;
        color: #28a745;
    }
    
    .hint-action.not-helpful:hover {
        background: #f8d7da;
        border-color: #dc3545;
        color: #dc3545;
    }
    
    .coaching-feedback-container {
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 1000;
        max-width: 350px;
    }
    
    .analysis-feedback, .positive-feedback, .coaching-recommendation {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        padding: 15px;
        margin-bottom: 10px;
        animation: slideIn 0.3s ease-out;
    }
    
    .positive-feedback {
        border-left: 4px solid #28a745;
    }
    
    .positive-feedback i {
        color: #ffc107;
        font-size: 18px;
        margin-right: 8px;
    }
    
    .analysis-feedback {
        border-left: 4px solid #dc3545;
    }
    
    .coaching-recommendation {
        border-left: 4px solid #17a2b8;
    }
    
    .impact-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
        font-size: 12px;
    }
    
    .impact.positive {
        color: #28a745;
        font-weight: bold;
    }
    
    .impact.negative {
        color: #dc3545;
        font-weight: bold;
    }
    
    .coaching-status {
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999;
        background: white;
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 8px 16px;
        font-size: 12px;
    }
    
    .coaching-status.enabled {
        border: 2px solid #28a745;
        color: #28a745;
    }
    
    .coaching-status.disabled {
        border: 2px solid #6c757d;
        color: #6c757d;
    }
    
    .status-content {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .system-message {
        position: fixed;
        top: 60px;
        right: 20px;
        z-index: 1001;
        max-width: 300px;
        animation: slideIn 0.3s ease-out;
    }
    
    .feedback-thanks {
        background: #28a745;
        color: white;
        border-radius: 8px;
        padding: 12px 16px;
        animation: slideIn 0.3s ease-out;
    }
    
    .thanks-content {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .fade-out {
        animation: fadeOut 0.3s ease-in;
    }
    
    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }
    
    @media (max-width: 768px) {
        .coaching-hints-container,
        .coaching-feedback-container {
            left: 10px;
            right: 10px;
            max-width: none;
        }
        
        .coaching-hints-container {
            top: 10px;
        }
        
        .coaching-feedback-container {
            bottom: 10px;
        }
    }
`;
document.head.appendChild(coachingStyles);

// グローバルインスタンスを作成
let realtimeCoaching;

// DOMが読み込まれたら初期化
document.addEventListener('DOMContentLoaded', function() {
    realtimeCoaching = new RealtimeCoachingClient();
});