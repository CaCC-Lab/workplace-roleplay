/**
 * Celeryタスクのリトライ処理を管理するJavaScriptモジュール
 * 
 * リアルタイムの進捗表示、カウントダウンタイマー、
 * 部分レスポンス表示、キャンセル機能を提供
 */
class RetryHandler {
    constructor(sessionId, options = {}) {
        this.sessionId = sessionId;
        this.options = {
            showCountdownTimer: true,
            enableCancellation: true,
            showPartialResponse: true,
            retryMessageContainer: '#retry-status',
            countdownContainer: '#retry-countdown',
            partialResponseContainer: '#partial-response',
            cancelButton: '#cancel-retry',
            ...options
        };
        
        this.currentTaskId = null;
        this.retryCount = 0;
        this.maxRetries = 0;
        this.retryDelay = 0;
        this.estimatedRetryTime = null;
        this.countdownInterval = null;
        this.eventSource = null;
        
        this.initializeEventHandlers();
    }
    
    /**
     * イベントハンドラーの初期化
     */
    initializeEventHandlers() {
        // キャンセルボタンのイベントリスナー
        const cancelButton = document.querySelector(this.options.cancelButton);
        if (cancelButton) {
            cancelButton.addEventListener('click', () => this.cancelRetry());
        }
        
        // ページ終了時のクリーンアップ
        window.addEventListener('beforeunload', () => this.cleanup());
    }
    
    /**
     * Server-Sent Eventsでリトライ状態を監視
     * @param {string} taskId - 監視するタスクID
     */
    startMonitoring(taskId) {
        this.currentTaskId = taskId;
        
        // 既存のEventSourceがあればクローズ
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        // SSEストリームを開始
        const streamUrl = `/stream/${this.sessionId}`;
        this.eventSource = new EventSource(streamUrl);
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleStreamEvent(data);
            } catch (error) {
                console.error('Failed to parse SSE event:', error);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.handleConnectionError();
        };
    }
    
    /**
     * ストリーミングイベントを処理
     * @param {Object} data - イベントデータ
     */
    handleStreamEvent(data) {
        switch (data.type) {
            case 'retry':
                this.handleRetryEvent(data);
                break;
            case 'partial_complete':
                this.handlePartialComplete(data);
                break;
            case 'error':
                this.handleFinalError(data);
                break;
            case 'complete':
                this.handleSuccess(data);
                break;
            case 'chunk':
                this.handleChunk(data);
                break;
            default:
                console.debug('Unknown event type:', data.type);
        }
    }
    
    /**
     * リトライイベントの処理
     * @param {Object} data - リトライデータ
     */
    handleRetryEvent(data) {
        this.retryCount = data.retry_count;
        this.maxRetries = data.max_retries;
        this.retryDelay = data.retry_delay;
        this.estimatedRetryTime = data.estimated_retry_time * 1000; // msに変換
        
        this.showRetryMessage(data);
        
        if (this.options.showCountdownTimer) {
            this.startCountdown();
        }
        
        // カスタムイベントを発火
        this.dispatchEvent('retry', data);
    }
    
    /**
     * 部分完了イベントの処理
     * @param {Object} data - 部分完了データ
     */
    handlePartialComplete(data) {
        if (this.options.showPartialResponse && data.content) {
            this.showPartialResponse(data.content);
        }
        
        this.dispatchEvent('partial_complete', data);
    }
    
    /**
     * 最終エラーイベントの処理
     * @param {Object} data - エラーデータ
     */
    handleFinalError(data) {
        this.cleanup();
        
        const errorMessage = this.createErrorMessage(data);
        this.showErrorMessage(errorMessage);
        
        this.dispatchEvent('error', data);
    }
    
    /**
     * 成功イベントの処理
     * @param {Object} data - 成功データ
     */
    handleSuccess(data) {
        this.cleanup();
        this.hideRetryMessage();
        this.dispatchEvent('success', data);
    }
    
    /**
     * チャンクイベントの処理
     * @param {Object} data - チャンクデータ
     */
    handleChunk(data) {
        // 通常のチャンク処理（他のモジュールに委譲）
        this.dispatchEvent('chunk', data);
    }
    
    /**
     * リトライメッセージの表示
     * @param {Object} data - リトライデータ
     */
    showRetryMessage(data) {
        const container = document.querySelector(this.options.retryMessageContainer);
        if (!container) return;
        
        const errorTypeText = this.getErrorTypeText(data.error_type);
        const progressText = `${this.retryCount}/${this.maxRetries}回目の試行`;
        
        container.innerHTML = `
            <div class="retry-notification">
                <div class="retry-header">
                    <i class="fas fa-redo-alt fa-spin"></i>
                    <span class="retry-title">接続を再試行中...</span>
                </div>
                <div class="retry-details">
                    <p class="retry-error-type">${errorTypeText}</p>
                    <p class="retry-progress">${progressText}</p>
                    <p class="retry-message">${data.error}</p>
                </div>
                ${this.options.enableCancellation ? this.createCancelButton() : ''}
            </div>
        `;
        
        container.style.display = 'block';
    }
    
    /**
     * カウントダウンタイマーの開始
     */
    startCountdown() {
        const container = document.querySelector(this.options.countdownContainer);
        if (!container) return;
        
        // 既存のインターバルをクリア
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
        
        this.countdownInterval = setInterval(() => {
            const now = Date.now();
            const remaining = Math.max(0, this.estimatedRetryTime - now);
            
            if (remaining <= 0) {
                clearInterval(this.countdownInterval);
                container.textContent = '再試行中...';
                return;
            }
            
            const seconds = Math.ceil(remaining / 1000);
            container.innerHTML = `
                <div class="countdown-timer">
                    <i class="fas fa-clock"></i>
                    <span>次の試行まで: <strong>${seconds}秒</strong></span>
                </div>
            `;
        }, 1000);
    }
    
    /**
     * 部分レスポンスの表示
     * @param {string} content - 部分コンテンツ
     */
    showPartialResponse(content) {
        const container = document.querySelector(this.options.partialResponseContainer);
        if (!container) return;
        
        container.innerHTML = `
            <div class="partial-response">
                <div class="partial-response-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>部分的な応答</span>
                </div>
                <div class="partial-response-content">
                    ${this.formatContent(content)}
                </div>
                <div class="partial-response-note">
                    <small>エラーにより応答が中断されましたが、ここまでの内容を表示しています。</small>
                </div>
            </div>
        `;
        
        container.style.display = 'block';
    }
    
    /**
     * エラーメッセージの表示
     * @param {string} message - エラーメッセージ
     */
    showErrorMessage(message) {
        const container = document.querySelector(this.options.retryMessageContainer);
        if (!container) return;
        
        container.innerHTML = `
            <div class="error-notification">
                <div class="error-header">
                    <i class="fas fa-exclamation-circle"></i>
                    <span class="error-title">接続に失敗しました</span>
                </div>
                <div class="error-message">${message}</div>
            </div>
        `;
        
        container.style.display = 'block';
    }
    
    /**
     * リトライメッセージの非表示
     */
    hideRetryMessage() {
        const container = document.querySelector(this.options.retryMessageContainer);
        if (container) {
            container.style.display = 'none';
        }
        
        const countdownContainer = document.querySelector(this.options.countdownContainer);
        if (countdownContainer) {
            countdownContainer.style.display = 'none';
        }
    }
    
    /**
     * リトライのキャンセル
     */
    async cancelRetry() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/tasks/${this.currentTaskId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.cleanup();
                this.showCancelMessage();
                this.dispatchEvent('cancelled', { taskId: this.currentTaskId });
            } else {
                console.error('Failed to cancel task:', response.statusText);
            }
        } catch (error) {
            console.error('Error cancelling task:', error);
        }
    }
    
    /**
     * キャンセル完了メッセージの表示
     */
    showCancelMessage() {
        const container = document.querySelector(this.options.retryMessageContainer);
        if (!container) return;
        
        container.innerHTML = `
            <div class="cancel-notification">
                <div class="cancel-header">
                    <i class="fas fa-times-circle"></i>
                    <span class="cancel-title">処理をキャンセルしました</span>
                </div>
            </div>
        `;
        
        setTimeout(() => {
            container.style.display = 'none';
        }, 3000);
    }
    
    /**
     * 接続エラーの処理
     */
    handleConnectionError() {
        this.cleanup();
        this.showErrorMessage('サーバーとの接続が失われました。ページを再読み込みしてください。');
    }
    
    /**
     * リソースのクリーンアップ
     */
    cleanup() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
        
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
    
    /**
     * カスタムイベントの発火
     * @param {string} eventType - イベントタイプ
     * @param {Object} data - イベントデータ
     */
    dispatchEvent(eventType, data) {
        const event = new CustomEvent(`retry:${eventType}`, {
            detail: { sessionId: this.sessionId, ...data }
        });
        document.dispatchEvent(event);
    }
    
    /**
     * エラータイプを人間が読みやすいテキストに変換
     * @param {string} errorType - エラータイプ
     * @returns {string} 表示用テキスト
     */
    getErrorTypeText(errorType) {
        const errorTexts = {
            'RateLimitError': 'API利用制限に達しました',
            'NetworkError': 'ネットワーク接続エラー',
            'ServiceUnavailableError': 'サービスが一時的に利用できません',
            'AuthenticationError': '認証エラー',
            'TemporaryLLMError': '一時的なサーバーエラー'
        };
        
        return errorTexts[errorType] || 'システムエラー';
    }
    
    /**
     * エラーメッセージを作成
     * @param {Object} data - エラーデータ
     * @returns {string} エラーメッセージ
     */
    createErrorMessage(data) {
        const baseMessage = '申し訳ございません。システムエラーが発生しました。';
        
        if (data.reason && data.reason.includes('max_retries_exceeded')) {
            return `${baseMessage} 複数回の再試行を行いましたが、問題が解決しませんでした。しばらく時間をおいてから再度お試しください。`;
        }
        
        return `${baseMessage} エラー: ${data.error}`;
    }
    
    /**
     * キャンセルボタンのHTML生成
     * @returns {string} キャンセルボタンのHTML
     */
    createCancelButton() {
        return `
            <div class="retry-actions">
                <button id="${this.options.cancelButton.replace('#', '')}" class="btn btn-secondary btn-sm">
                    <i class="fas fa-times"></i> キャンセル
                </button>
            </div>
        `;
    }
    
    /**
     * コンテンツのフォーマット
     * @param {string} content - フォーマットするコンテンツ
     * @returns {string} フォーマット済みコンテンツ
     */
    formatContent(content) {
        // 改行をBRタグに変換
        return content.replace(/\n/g, '<br>');
    }
    
    /**
     * CSRFトークンの取得
     * @returns {string} CSRFトークン
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
}

// グローバルに利用可能にする
window.RetryHandler = RetryHandler;

// 使用例とイベントリスナーの設定例
document.addEventListener('DOMContentLoaded', function() {
    // リトライイベントのリスナー例
    document.addEventListener('retry:retry', function(event) {
        console.log('Retry started:', event.detail);
    });
    
    document.addEventListener('retry:error', function(event) {
        console.log('Final error:', event.detail);
    });
    
    document.addEventListener('retry:success', function(event) {
        console.log('Task succeeded:', event.detail);
    });
    
    document.addEventListener('retry:cancelled', function(event) {
        console.log('Task cancelled:', event.detail);
    });
});