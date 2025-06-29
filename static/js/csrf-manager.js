/**
 * CSRF（Cross-Site Request Forgery）対策用のトークン管理
 */

class CSRFManager {
    constructor() {
        this.token = null;
        this.tokenExpiry = null;
        this.refreshThreshold = 5 * 60 * 1000; // 5分前にリフレッシュ
        this.apiEndpoints = {
            getToken: '/api/csrf-token',
            protectedPaths: [
                '/api/chat',
                '/api/scenario_chat',
                '/api/clear_history',
                '/api/scenario_clear',
                '/api/watch/start',
                '/api/watch/next',
                '/api/scenario_feedback',
                '/api/chat_feedback',
                '/api/get_assist',
                '/api/start_chat',
                '/api/conversation_history',
                '/api/tts',
                '/api/generate_character_image',
                '/api/strength_analysis'
            ]
        };
        
        // 初期化
        this.initialize();
    }
    
    /**
     * CSRF管理の初期化
     */
    async initialize() {
        try {
            await this.fetchToken();
            this.setupAutoRefresh();
            this.setupRequestInterceptor();
            console.log('CSRF Manager initialized successfully');
        } catch (error) {
            console.error('Failed to initialize CSRF Manager:', error);
            this.handleInitializationError(error);
        }
    }
    
    /**
     * サーバーからCSRFトークンを取得
     */
    async fetchToken() {
        try {
            const response = await fetch(this.apiEndpoints.getToken, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch CSRF token: ${response.status}`);
            }
            
            const data = await response.json();
            this.token = data.csrf_token;
            this.tokenExpiry = new Date(Date.now() + (data.expires_in * 1000));
            
            console.log('CSRF token refreshed');
            return this.token;
            
        } catch (error) {
            console.error('Error fetching CSRF token:', error);
            throw error;
        }
    }
    
    /**
     * 現在のCSRFトークンを取得（必要に応じてリフレッシュ）
     */
    async getToken() {
        if (!this.token || this.isTokenExpiring()) {
            await this.fetchToken();
        }
        return this.token;
    }
    
    /**
     * 現在のCSRFトークンを同期的に取得（キャッシュされたトークンのみ）
     * jQueryのbeforeSend等、同期コールバック用
     */
    getTokenSync() {
        // トークンの期限が切れそうな場合は非同期でリフレッシュを開始
        if (this.isTokenExpiring()) {
            this.fetchToken().catch(error => {
                console.error('Background token refresh failed:', error);
            });
        }
        return this.token;
    }
    
    /**
     * jQueryリクエスト用のトークン確保（必要に応じて即座にリフレッシュ）
     */
    async ensureTokenForJQuery() {
        if (!this.token || this.isTokenExpiring()) {
            try {
                await this.fetchToken();
            } catch (error) {
                console.error('Failed to refresh token for jQuery:', error);
            }
        }
        return this.token;
    }
    
    /**
     * トークンの有効期限が近いかチェック
     */
    isTokenExpiring() {
        if (!this.tokenExpiry) return true;
        return (this.tokenExpiry.getTime() - Date.now()) < this.refreshThreshold;
    }
    
    /**
     * 自動リフレッシュの設定
     */
    setupAutoRefresh() {
        // 1分ごとにトークンをチェック（より頻繁に）
        setInterval(async () => {
            if (this.isTokenExpiring()) {
                try {
                    await this.fetchToken();
                } catch (error) {
                    console.error('Auto-refresh failed:', error);
                }
            }
        }, 1 * 60 * 1000);
        
        // ページが表示状態になった時にもトークンをチェック
        if (typeof document !== 'undefined') {
            document.addEventListener('visibilitychange', async () => {
                if (!document.hidden && this.isTokenExpiring()) {
                    try {
                        await this.fetchToken();
                    } catch (error) {
                        console.error('Visibility change token refresh failed:', error);
                    }
                }
            });
        }
    }
    
    /**
     * fetchリクエストの自動インターセプト設定
     */
    setupRequestInterceptor() {
        // 元のfetch関数を保存
        const originalFetch = window.fetch;
        
        // fetch関数をオーバーライド
        window.fetch = async (url, options = {}) => {
            // URL が保護されたエンドポイントかチェック
            if (this.isProtectedEndpoint(url) && this.isModifyingRequest(options.method)) {
                try {
                    const token = await this.getToken();
                    
                    // ヘッダーにCSRFトークンを追加
                    options.headers = {
                        ...options.headers,
                        'X-CSRFToken': token
                    };
                    
                    console.log(`Added CSRF token to ${options.method || 'GET'} ${url}`);
                    
                } catch (error) {
                    console.error('Failed to add CSRF token:', error);
                    // トークン取得に失敗してもリクエストは継続
                }
            }
            
            // 元のfetch関数を呼び出し
            const response = await originalFetch(url, options);
            
            // CSRFエラーの場合はトークンをリフレッシュして再試行
            if (response.status === 403 && await this.isCSRFError(response)) {
                console.log('CSRF error detected, refreshing token and retrying...');
                try {
                    await this.fetchToken();
                    
                    // 新しいトークンでリトライ
                    if (this.isProtectedEndpoint(url) && this.isModifyingRequest(options.method)) {
                        options.headers = {
                            ...options.headers,
                            'X-CSRFToken': this.token
                        };
                    }
                    
                    return await originalFetch(url, options);
                    
                } catch (retryError) {
                    console.error('Retry with new CSRF token failed:', retryError);
                    return response; // 元のレスポンスを返す
                }
            }
            
            return response;
        };
    }
    
    /**
     * 保護されたエンドポイントかチェック
     */
    isProtectedEndpoint(url) {
        if (typeof url !== 'string') {
            url = url.toString();
        }
        
        return this.apiEndpoints.protectedPaths.some(path => 
            url.includes(path)
        );
    }
    
    /**
     * データを変更するリクエストかチェック
     */
    isModifyingRequest(method) {
        const modifyingMethods = ['POST', 'PUT', 'PATCH', 'DELETE'];
        return modifyingMethods.includes((method || 'GET').toUpperCase());
    }
    
    /**
     * レスポンスがCSRFエラーかチェック
     */
    async isCSRFError(response) {
        try {
            const clone = response.clone();
            const data = await clone.json();
            return data.code === 'CSRF_TOKEN_MISSING' || 
                   data.code === 'CSRF_TOKEN_INVALID' ||
                   (data.error && data.error.toLowerCase().includes('csrf'));
        } catch (error) {
            return false;
        }
    }
    
    /**
     * 手動でリクエストにCSRFトークンを追加
     */
    async addCSRFToken(headers = {}) {
        const token = await this.getToken();
        return {
            ...headers,
            'X-CSRFToken': token
        };
    }
    
    /**
     * フォームデータにCSRFトークンを追加
     */
    async addCSRFTokenToForm(formData) {
        const token = await this.getToken();
        formData.append('csrf_token', token);
        return formData;
    }
    
    /**
     * JSONデータにCSRFトークンを追加
     */
    async addCSRFTokenToJSON(data) {
        const token = await this.getToken();
        return {
            ...data,
            csrf_token: token
        };
    }
    
    /**
     * 初期化エラーのハンドリング
     */
    handleInitializationError(error) {
        // ユーザーに分かりやすいエラーメッセージを表示
        console.warn('CSRF protection may not be available:', error.message);
        
        // フォールバック機能を提供
        this.token = null;
    }
    
    /**
     * デバッグ情報の取得
     */
    getDebugInfo() {
        return {
            token: this.token ? `${this.token.substring(0, 8)}...` : null,
            tokenExpiry: this.tokenExpiry,
            isExpiring: this.isTokenExpiring(),
            protectedPaths: this.apiEndpoints.protectedPaths
        };
    }
    
    /**
     * CSRF管理の無効化（テスト用）
     */
    disable() {
        this.token = null;
        this.tokenExpiry = null;
        console.log('CSRF Manager disabled');
    }
}

// jQuery ajaxのサポート（jQueryが利用可能な場合）
if (typeof $ !== 'undefined' && $.ajaxSetup) {
    $(document).ready(function() {
        // CSRFManagerの初期化を待ってからjQuery設定を適用
        const setupJQueryCSRF = () => {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    // CSRFManagerが利用可能で、保護されたエンドポイントの場合
                    if (window.csrfManager && 
                        window.csrfManager.isProtectedEndpoint(settings.url) &&
                        window.csrfManager.isModifyingRequest(settings.type)) {
                        
                        try {
                            const token = window.csrfManager.getTokenSync();
                            if (token) {
                                xhr.setRequestHeader('X-CSRFToken', token);
                                console.log(`Added CSRF token to jQuery ${settings.type} ${settings.url}`);
                            } else {
                                console.warn('CSRF token not available for jQuery request, may need initialization');
                                // トークンが利用できない場合の警告（開発時のデバッグ用）
                            }
                        } catch (error) {
                            console.error('Failed to add CSRF token to jQuery request:', error);
                        }
                    }
                }
            });
        };
        
        // CSRFManagerが既に利用可能な場合は即座に設定
        if (window.csrfManager) {
            setupJQueryCSRF();
        } else {
            // CSRFManagerの準備ができるまで待機
            const checkInterval = setInterval(() => {
                if (window.csrfManager) {
                    setupJQueryCSRF();
                    clearInterval(checkInterval);
                }
            }, 100);
            
            // 10秒後にタイムアウト
            setTimeout(() => {
                clearInterval(checkInterval);
                console.warn('CSRFManager not available after 10 seconds, jQuery CSRF protection may not work');
            }, 10000);
        }
    });
}

// グローバルインスタンスを作成
window.csrfManager = new CSRFManager();

// デバッグ用のグローバル関数
window.getCSRFDebugInfo = () => window.csrfManager.getDebugInfo();

// エクスポート（ES6モジュールとして使用する場合）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSRFManager;
}