/**
 * 非同期チャット処理用JavaScript
 * Server-Sent Events (SSE) を使用したストリーミング対応
 */

class AsyncChatClient {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '/api/async';
        this.sessionId = options.sessionId || null;
        this.eventSource = null;
        this.isStreaming = false;
        this.currentMessage = '';
        this.onMessage = options.onMessage || this.defaultMessageHandler;
        this.onError = options.onError || this.defaultErrorHandler;
        this.onComplete = options.onComplete || this.defaultCompleteHandler;
        
        // 再接続設定
        this.reconnectConfig = {
            enabled: options.autoReconnect !== false,
            maxRetries: options.maxRetries || 3,
            retryDelay: options.retryDelay || 1000,
            retryCount: 0,
            lastError: null
        };
        
        // エラー通知設定
        this.errorNotifier = options.errorNotifier || this.defaultErrorNotifier;
    }

    /**
     * チャットメッセージをストリーミング送信
     * @param {string} message - 送信するメッセージ
     * @param {string} model - 使用するAIモデル
     * @returns {Promise<void>}
     */
    async sendMessage(message, model = 'gemini/gemini-1.5-flash') {
        if (this.isStreaming) {
            console.warn('Already streaming a message');
            return;
        }
        
        // 最後のメッセージデータを保存（再接続用）
        this.lastMessageData = { message, model };

        try {
            const response = await fetch(`${this.baseUrl}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    message: message,
                    model: model,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'ストリーミング開始エラー');
            }

            // セッションIDとタスクIDを取得
            this.sessionId = response.headers.get('X-Session-ID') || this.sessionId;
            const taskId = response.headers.get('X-Task-ID');

            // SSEストリームを開始
            this.startStreaming(response);

        } catch (error) {
            this.handleStreamError(error);
        }
    }

    /**
     * SSEストリーミングを開始
     * @param {Response} response - Fetchレスポンス
     */
    startStreaming(response) {
        this.isStreaming = true;
        this.currentMessage = '';
        this.reconnectConfig.retryCount = 0; // 成功したので再試行カウントをリセット

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const processStream = async () => {
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    
                    // SSEメッセージをパース
                    const messages = buffer.split('\n\n');
                    buffer = messages.pop() || '';

                    for (const message of messages) {
                        if (message.trim()) {
                            this.processSSEMessage(message);
                        }
                    }
                }
            } catch (error) {
                // エラーを分類して処理
                this.handleStreamError(error);
            } finally {
                this.isStreaming = false;
            }
        };

        processStream();
    }

    /**
     * SSEメッセージを処理
     * @param {string} message - SSEメッセージ
     */
    processSSEMessage(message) {
        const lines = message.split('\n');
        let eventType = 'message';
        let data = '';

        for (const line of lines) {
            if (line.startsWith('event:')) {
                eventType = line.substring(6).trim();
            } else if (line.startsWith('data:')) {
                data = line.substring(5).trim();
            }
        }

        if (!data) return;

        try {
            const parsedData = JSON.parse(data);
            
            switch (parsedData.type || eventType) {
                case 'connected':
                    console.log('SSE connected:', parsedData.channel);
                    break;
                    
                case 'chunk':
                    this.currentMessage += parsedData.content;
                    this.onMessage({
                        type: 'streaming',
                        content: parsedData.content,
                        fullContent: this.currentMessage
                    });
                    break;
                    
                case 'complete':
                    this.onComplete({
                        content: parsedData.total_content || this.currentMessage,
                        tokenCount: parsedData.token_count,
                        responseTime: parsedData.response_time
                    });
                    this.saveResponse(parsedData.total_content || this.currentMessage);
                    break;
                    
                case 'error':
                    this.onError(new Error(parsedData.message || parsedData.error));
                    break;
                    
                case 'heartbeat':
                    // ハートビートは無視
                    break;
                    
                default:
                    console.log('Unknown SSE event:', eventType, parsedData);
            }
        } catch (error) {
            console.error('Failed to parse SSE data:', error);
        }
    }

    /**
     * AIレスポンスを保存
     * @param {string} message - 保存するメッセージ
     */
    async saveResponse(message) {
        try {
            await fetch(`${this.baseUrl}/chat/save-response`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message
                })
            });
        } catch (error) {
            console.error('Failed to save response:', error);
        }
    }

    /**
     * フィードバックを生成
     * @param {string} model - 使用するAIモデル
     * @returns {Promise<Object>}
     */
    async generateFeedback(model = 'gemini/gemini-1.5-flash') {
        try {
            const response = await fetch(`${this.baseUrl}/chat/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    model: model
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'フィードバック生成エラー');
            }

            const result = await response.json();
            
            // タスクの完了を待つ
            if (result.task_id) {
                return await this.waitForTask(result.task_id);
            }
            
            return result;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }

    /**
     * タスクの完了を待つ
     * @param {string} taskId - タスクID
     * @param {number} timeout - タイムアウト（ミリ秒）
     * @returns {Promise<Object>}
     */
    async waitForTask(taskId, timeout = 60000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            try {
                const response = await fetch(`${this.baseUrl}/task/${taskId}/status`);
                const result = await response.json();
                
                if (result.status === 'SUCCESS') {
                    return result.result;
                } else if (result.status === 'FAILURE') {
                    throw new Error(result.error || 'タスク失敗');
                }
                
                // 1秒待機
                await new Promise(resolve => setTimeout(resolve, 1000));
                
            } catch (error) {
                throw error;
            }
        }
        
        throw new Error('タスクタイムアウト');
    }

    /**
     * ストリーミングを停止
     */
    stopStreaming() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isStreaming = false;
    }

    /**
     * シナリオメッセージを送信（ストリーミング）
     * @param {string} message - ユーザーのメッセージ
     * @param {string} model - 使用するモデル
     * @param {string} scenarioId - シナリオID
     */
    async sendScenarioMessage(message, model = 'gemini/gemini-1.5-flash', scenarioId) {
        if (this.isStreaming) {
            console.warn('Already streaming a message');
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/scenario/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    message: message,
                    model: model,
                    scenario_id: scenarioId,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'シナリオメッセージ送信エラー');
            }

            // セッションIDを更新
            this.sessionId = response.headers.get('X-Session-ID') || this.sessionId;

            // SSEストリームを開始
            this.startStreaming(response);

        } catch (error) {
            this.onError(error);
            throw error;
        }
    }

    /**
     * シナリオフィードバックを生成
     * @param {string} model - 使用するモデル
     * @param {string} scenarioId - シナリオID
     * @returns {Promise<Object>} フィードバック結果
     */
    async generateScenarioFeedback(model = 'gemini/gemini-1.5-flash', scenarioId) {
        try {
            const response = await fetch(`${this.baseUrl}/scenario/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    scenario_id: scenarioId,
                    model: model,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'シナリオフィードバック生成エラー');
            }

            const result = await response.json();
            
            // タスクの完了を待つ
            if (result.task_id) {
                return await this.waitForTask(result.task_id);
            }
            
            return result;
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }

    /**
     * シナリオAIアシストを取得
     * @param {string} model - 使用するモデル
     * @param {string} scenarioId - シナリオID
     * @param {string} context - 現在のコンテキスト
     * @returns {Promise<Object>} アシスト結果
     */
    async getScenarioAssist(model = 'gemini/gemini-1.5-flash', scenarioId, context) {
        try {
            const response = await fetch(`${this.baseUrl}/scenario/assist`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    scenario_id: scenarioId,
                    model: model,
                    current_context: context,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'AIアシスト取得エラー');
            }

            return await response.json();
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }

    /**
     * 観戦モードを開始（ストリーミング）
     * @param {Object} settings - 観戦設定
     * @returns {Promise<void>}
     */
    async startWatch(settings) {
        if (this.isStreaming) {
            console.warn('Already streaming a message');
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/watch/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    model_a: settings.model_a,
                    model_b: settings.model_b,
                    partner_type: settings.partner_type,
                    situation: settings.situation,
                    topic: settings.topic,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '観戦開始エラー');
            }

            // セッションIDを更新
            this.sessionId = response.headers.get('X-Session-ID') || this.sessionId;

            // SSEストリームを開始
            this.startStreaming(response);

        } catch (error) {
            this.onError(error);
            throw error;
        }
    }

    /**
     * 観戦モードの次の発言を取得（ストリーミング）
     * @param {string} modelA - モデルA
     * @param {string} modelB - モデルB
     * @returns {Promise<void>}
     */
    async getNextWatchMessage(modelA, modelB) {
        if (this.isStreaming) {
            console.warn('Already streaming a message');
            return;
        }

        try {
            const response = await fetch(`${this.baseUrl}/watch/next`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    model_a: modelA,
                    model_b: modelB
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '次の発言取得エラー');
            }

            // SSEストリームを開始
            this.startStreaming(response);

        } catch (error) {
            this.onError(error);
            throw error;
        }
    }

    /**
     * 観戦モードのメッセージを保存
     * @param {string} speaker - 話者名
     * @param {string} message - メッセージ内容
     * @param {number} practiceSessionId - 練習セッションID（オプション）
     * @returns {Promise<void>}
     */
    async saveWatchMessage(speaker, message, practiceSessionId = null) {
        try {
            await fetch(`${this.baseUrl}/watch/save-message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    speaker: speaker,
                    message: message,
                    practice_session_id: practiceSessionId
                })
            });
        } catch (error) {
            console.error('Failed to save watch message:', error);
        }
    }

    /**
     * セッションIDを確保
     */
    ensureSessionId() {
        if (!this.sessionId) {
            this.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
    }

    // デフォルトハンドラー
    defaultMessageHandler(data) {
        console.log('Message:', data);
    }

    defaultErrorHandler(error) {
        console.error('Error:', error);
    }

    defaultCompleteHandler(data) {
        console.log('Complete:', data);
    }
    
    /**
     * エラーの種類を分類
     * @param {Error} error - エラーオブジェクト
     * @returns {Object} エラー分類情報
     */
    classifyError(error) {
        const errorMessage = error.message ? error.message.toLowerCase() : '';
        
        // Gemini API特有のエラー
        if (errorMessage.includes('api key') || errorMessage.includes('authentication')) {
            return {
                type: 'auth',
                severity: 'critical',
                userMessage: 'APIキーの認証エラーが発生しました。管理者にお問い合わせください。',
                recoverable: false
            };
        }
        
        if (errorMessage.includes('rate limit') || errorMessage.includes('quota')) {
            return {
                type: 'rate_limit',
                severity: 'warning',
                userMessage: 'APIの利用制限に達しました。しばらく待ってから再試行してください。',
                recoverable: true,
                retryAfter: 60000 // 1分後
            };
        }
        
        if (errorMessage.includes('timeout') || errorMessage.includes('timed out')) {
            return {
                type: 'timeout',
                severity: 'warning',
                userMessage: 'サーバーからの応答がありません。自動的に再接続を試みます。',
                recoverable: true
            };
        }
        
        if (errorMessage.includes('network') || errorMessage.includes('failed to fetch')) {
            return {
                type: 'network',
                severity: 'warning',
                userMessage: 'ネットワーク接続に問題があります。接続を確認してください。',
                recoverable: true
            };
        }
        
        // その他のエラー
        return {
            type: 'unknown',
            severity: 'error',
            userMessage: `予期しないエラーが発生しました: ${error.message}`,
            recoverable: true
        };
    }
    
    /**
     * ストリーミングエラーを処理
     * @param {Error} error - エラーオブジェクト
     */
    handleStreamError(error) {
        const errorInfo = this.classifyError(error);
        this.reconnectConfig.lastError = errorInfo;
        
        // エラー通知
        this.errorNotifier(errorInfo);
        
        // 回復可能なエラーの場合、再接続を試みる
        if (errorInfo.recoverable && this.reconnectConfig.enabled && 
            this.reconnectConfig.retryCount < this.reconnectConfig.maxRetries) {
            
            this.reconnectConfig.retryCount++;
            const delay = this.reconnectConfig.retryDelay * Math.pow(2, this.reconnectConfig.retryCount - 1);
            
            this.errorNotifier({
                type: 'reconnecting',
                severity: 'info',
                userMessage: `再接続を試みています... (${this.reconnectConfig.retryCount}/${this.reconnectConfig.maxRetries})`,
                retryIn: delay
            });
            
            setTimeout(() => {
                if (this.lastMessageData) {
                    // 最後のメッセージを再送信
                    this.sendMessage(this.lastMessageData.message, this.lastMessageData.model);
                }
            }, delay);
        } else {
            // 再接続できない場合
            this.onError(error);
        }
    }
    
    /**
     * デフォルトのエラー通知
     * @param {Object} errorInfo - エラー情報
     */
    defaultErrorNotifier(errorInfo) {
        console.log('Error notification:', errorInfo);
        
        // DOMにエラーメッセージを表示する例
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${errorInfo.severity}`;
            alertDiv.innerHTML = `
                <span class="error-message">${errorInfo.userMessage}</span>
                ${errorInfo.type === 'reconnecting' ? '<span class="spinner"></span>' : ''}
                <button class="close-button" onclick="this.parentElement.remove()">×</button>
            `;
            errorContainer.appendChild(alertDiv);
            
            // 自動的に消える（再接続中以外）
            if (errorInfo.type !== 'reconnecting') {
                setTimeout(() => alertDiv.remove(), 10000);
            }
        }
    }
}

// グローバルに公開
window.AsyncChatClient = AsyncChatClient;