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
            this.onError(error);
        }
    }

    /**
     * SSEストリーミングを開始
     * @param {Response} response - Fetchレスポンス
     */
    startStreaming(response) {
        this.isStreaming = true;
        this.currentMessage = '';

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
                this.onError(error);
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
}

// グローバルに公開
window.AsyncChatClient = AsyncChatClient;