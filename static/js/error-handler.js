/**
 * エラーハンドリングユーティリティ
 */
class ErrorHandler {
    constructor() {
        this.errorLog = [];
        this.maxLogSize = 50;
        this.errorCallbacks = new Map();
    }

    /**
     * エラーを記録
     */
    logError(error, context = {}) {
        const errorEntry = {
            timestamp: new Date().toISOString(),
            message: error.message || String(error),
            stack: error.stack,
            context,
            type: error.name || 'Error'
        };

        this.errorLog.unshift(errorEntry);
        if (this.errorLog.length > this.maxLogSize) {
            this.errorLog.pop();
        }

        // コンソールにも出力
        console.error('Error logged:', errorEntry);

        // コールバックを実行
        this.triggerCallbacks(errorEntry);

        return errorEntry;
    }

    /**
     * エラータイプ別のコールバックを登録
     */
    onError(errorType, callback) {
        if (!this.errorCallbacks.has(errorType)) {
            this.errorCallbacks.set(errorType, []);
        }
        this.errorCallbacks.get(errorType).push(callback);
    }

    /**
     * コールバックをトリガー
     */
    triggerCallbacks(errorEntry) {
        // 全般的なエラーハンドラー
        const allHandlers = this.errorCallbacks.get('*') || [];
        allHandlers.forEach(handler => handler(errorEntry));

        // 特定のエラータイプのハンドラー
        const typeHandlers = this.errorCallbacks.get(errorEntry.type) || [];
        typeHandlers.forEach(handler => handler(errorEntry));
    }

    /**
     * ユーザーフレンドリーなエラーメッセージを生成
     */
    getUserMessage(error) {
        const errorMessages = {
            'NetworkError': 'ネットワーク接続に問題があります。接続を確認してください。',
            'TimeoutError': 'リクエストがタイムアウトしました。もう一度お試しください。',
            'ValidationError': '入力内容に問題があります。確認してください。',
            'AuthenticationError': '認証に失敗しました。ログインし直してください。',
            'ServerError': 'サーバーエラーが発生しました。しばらくしてからお試しください。',
            'RateLimitError': 'リクエストが多すぎます。少し待ってからお試しください。'
        };

        // エラータイプに基づくメッセージ
        if (error.name && errorMessages[error.name]) {
            return errorMessages[error.name];
        }

        // HTTPステータスコードに基づくメッセージ
        if (error.status) {
            switch (Math.floor(error.status / 100)) {
                case 4:
                    return 'リクエストに問題があります。入力内容を確認してください。';
                case 5:
                    return 'サーバーエラーが発生しました。しばらくしてからお試しください。';
            }
        }

        // デフォルトメッセージ
        return 'エラーが発生しました。もう一度お試しください。';
    }

    /**
     * エラーを表示
     */
    displayError(error, elementId = 'error-container') {
        const userMessage = this.getUserMessage(error);
        const errorElement = document.getElementById(elementId);
        
        if (errorElement) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-notification';
            errorDiv.innerHTML = `
                <div class="error-content">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>${userMessage}</span>
                    <button class="error-close" onclick="this.parentElement.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            errorElement.appendChild(errorDiv);
            
            // 5秒後に自動的に削除
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
    }

    /**
     * エラーログをクリア
     */
    clearLog() {
        this.errorLog = [];
    }

    /**
     * エラーログを取得
     */
    getLog() {
        return [...this.errorLog];
    }

    /**
     * エラーレポートを生成
     */
    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            totalErrors: this.errorLog.length,
            errorsByType: {},
            recentErrors: this.errorLog.slice(0, 10)
        };

        // エラータイプ別に集計
        this.errorLog.forEach(error => {
            const type = error.type || 'Unknown';
            report.errorsByType[type] = (report.errorsByType[type] || 0) + 1;
        });

        return report;
    }
}

// グローバルインスタンス
window.errorHandler = new ErrorHandler();

// グローバルエラーハンドラーの設定
window.addEventListener('error', (event) => {
    window.errorHandler.logError(event.error || new Error(event.message), {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
    });
});

// Promise rejectionのハンドリング
window.addEventListener('unhandledrejection', (event) => {
    window.errorHandler.logError(new Error(event.reason), {
        type: 'UnhandledPromiseRejection'
    });
});