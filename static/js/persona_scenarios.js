/**
 * ペルソナベースシナリオのフロントエンド実装
 */

// ペルソナシナリオ管理クラス
class PersonaScenarioManager {
    constructor() {
        this.currentScenarioId = null;
        this.currentPersonaCode = null;
        this.sessionId = null;
        this.messageHistory = [];
    }

    /**
     * シナリオに適したペルソナを取得
     */
    async getSuitablePersonas(scenarioId) {
        try {
            const response = await fetch(`/api/persona-scenarios/suitable-personas/${scenarioId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch suitable personas');
            }
            return await response.json();
        } catch (error) {
            console.error('Error getting suitable personas:', error);
            return { personas: [] };
        }
    }

    /**
     * ペルソナベースのシナリオチャットを開始
     */
    async startPersonaScenarioChat(scenarioId, personaCode = null, initialMessage = '') {
        this.currentScenarioId = scenarioId;
        this.currentPersonaCode = personaCode;
        this.messageHistory = [];
        
        // セッションIDを生成
        this.sessionId = 'ps_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        return await this.sendMessage(initialMessage);
    }

    /**
     * メッセージを送信してストリーミングレスポンスを受信
     */
    async sendMessage(message) {
        try {
            const requestData = {
                message: message,
                scenario_id: this.currentScenarioId,
                session_id: this.sessionId
            };
            
            if (this.currentPersonaCode) {
                requestData.persona_code = this.currentPersonaCode;
            }

            const response = await fetch('/api/persona-scenarios/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            // ヘッダーからペルソナ情報を取得
            const personaCode = response.headers.get('X-Persona-Code');
            if (personaCode && !this.currentPersonaCode) {
                this.currentPersonaCode = personaCode;
            }

            // SSEストリームを処理
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';

            return new Promise((resolve, reject) => {
                const processStream = async () => {
                    try {
                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break;

                            const chunk = decoder.decode(value);
                            const lines = chunk.split('\n');
                            
                            for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                    const data = line.slice(6);
                                    if (data === '[DONE]') {
                                        // ストリーミング完了
                                        await this.savePersonaResponse(fullResponse);
                                        resolve({
                                            message: fullResponse,
                                            persona_code: this.currentPersonaCode
                                        });
                                        return;
                                    }
                                    
                                    try {
                                        const parsed = JSON.parse(data);
                                        if (parsed.content) {
                                            fullResponse += parsed.content;
                                            // リアルタイムで表示更新（コールバック）
                                            if (this.onStreamUpdate) {
                                                this.onStreamUpdate(parsed.content);
                                            }
                                        }
                                    } catch (e) {
                                        // JSON解析エラーは無視
                                    }
                                }
                            }
                        }
                    } catch (error) {
                        reject(error);
                    }
                };

                processStream();
            });

        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    /**
     * ペルソナのレスポンスを保存
     */
    async savePersonaResponse(message) {
        if (!message) return;
        
        try {
            await fetch('/api/persona-scenarios/save-response', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    scenario_id: this.currentScenarioId,
                    persona_code: this.currentPersonaCode,
                    message: message
                })
            });
            
            // メッセージ履歴に追加
            this.messageHistory.push({
                role: 'assistant',
                content: message,
                persona_code: this.currentPersonaCode
            });
        } catch (error) {
            console.error('Error saving persona response:', error);
        }
    }

    /**
     * ストリーミング更新時のコールバックを設定
     */
    setStreamUpdateCallback(callback) {
        this.onStreamUpdate = callback;
    }
}

// UI統合の例
class PersonaScenarioUI {
    constructor() {
        this.manager = new PersonaScenarioManager();
        this.initializeUI();
    }

    initializeUI() {
        // ペルソナ選択モーダルの初期化
        this.personaModal = document.getElementById('personaSelectionModal');
        this.personaList = document.getElementById('personaList');
        
        // チャットUI要素
        this.messageContainer = document.getElementById('messageContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        
        // イベントリスナーの設定
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // ストリーミング更新のコールバック設定
        this.manager.setStreamUpdateCallback((content) => {
            this.updateStreamingMessage(content);
        });
    }

    /**
     * シナリオ開始時にペルソナを選択
     */
    async startScenarioWithPersona(scenarioId) {
        // 適切なペルソナを取得
        const { personas } = await this.manager.getSuitablePersonas(scenarioId);
        
        if (personas.length === 0) {
            console.error('No suitable personas found');
            return;
        }
        
        // ペルソナ選択UIを表示
        this.showPersonaSelection(personas, scenarioId);
    }

    /**
     * ペルソナ選択UIを表示
     */
    showPersonaSelection(personas, scenarioId) {
        if (!this.personaList) return;
        
        // ペルソナリストをクリア
        this.personaList.innerHTML = '';
        
        // ペルソナカードを作成
        personas.forEach(persona => {
            const card = document.createElement('div');
            card.className = 'persona-card';
            card.innerHTML = `
                <div class="persona-info">
                    <h4>${persona.name}</h4>
                    <p class="persona-role">${persona.industry} - ${persona.role}</p>
                    <p class="persona-personality">性格: ${persona.personality_type}</p>
                    <p class="persona-experience">経験年数: ${persona.years_experience}年</p>
                </div>
                <button class="select-persona-btn" data-persona-code="${persona.persona_code}">
                    このペルソナと練習
                </button>
            `;
            
            const selectBtn = card.querySelector('.select-persona-btn');
            selectBtn.addEventListener('click', () => {
                this.selectPersona(scenarioId, persona.persona_code);
            });
            
            this.personaList.appendChild(card);
        });
        
        // モーダルを表示
        if (this.personaModal) {
            this.personaModal.style.display = 'block';
        }
    }

    /**
     * ペルソナを選択してシナリオを開始
     */
    async selectPersona(scenarioId, personaCode) {
        // モーダルを閉じる
        if (this.personaModal) {
            this.personaModal.style.display = 'none';
        }
        
        // チャットをクリア
        this.clearChat();
        
        // シナリオを開始
        this.showSystemMessage(`ペルソナとのシナリオを開始しています...`);
        
        try {
            const response = await this.manager.startPersonaScenarioChat(scenarioId, personaCode);
            this.addMessage('assistant', response.message, personaCode);
        } catch (error) {
            this.showErrorMessage('シナリオの開始に失敗しました');
        }
    }

    /**
     * メッセージを送信
     */
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // UIをクリア
        this.messageInput.value = '';
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        
        // ユーザーメッセージを追加
        this.addMessage('user', message);
        
        // ストリーミング用のメッセージコンテナを作成
        this.createStreamingMessageContainer();
        
        try {
            const response = await this.manager.sendMessage(message);
            this.finalizeStreamingMessage(response.message);
        } catch (error) {
            this.showErrorMessage('メッセージの送信に失敗しました');
        } finally {
            this.messageInput.disabled = false;
            this.sendButton.disabled = false;
            this.messageInput.focus();
        }
    }

    /**
     * メッセージを追加
     */
    addMessage(role, content, personaCode = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        if (role === 'assistant' && personaCode) {
            messageDiv.setAttribute('data-persona', personaCode);
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(content)}</div>
            <div class="message-meta">${new Date().toLocaleTimeString()}</div>
        `;
        
        this.messageContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    /**
     * ストリーミングメッセージコンテナを作成
     */
    createStreamingMessageContainer() {
        this.streamingContainer = document.createElement('div');
        this.streamingContainer.className = 'message assistant-message streaming';
        this.streamingContainer.innerHTML = `
            <div class="message-content"></div>
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        
        this.messageContainer.appendChild(this.streamingContainer);
        this.scrollToBottom();
    }

    /**
     * ストリーミングメッセージを更新
     */
    updateStreamingMessage(content) {
        if (this.streamingContainer) {
            const contentDiv = this.streamingContainer.querySelector('.message-content');
            contentDiv.textContent += content;
            this.scrollToBottom();
        }
    }

    /**
     * ストリーミングメッセージを確定
     */
    finalizeStreamingMessage(fullContent) {
        if (this.streamingContainer) {
            const contentDiv = this.streamingContainer.querySelector('.message-content');
            contentDiv.textContent = fullContent;
            this.streamingContainer.classList.remove('streaming');
            
            // タイピングインジケーターを削除
            const indicator = this.streamingContainer.querySelector('.typing-indicator');
            if (indicator) {
                indicator.remove();
            }
            
            // メタ情報を追加
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            metaDiv.textContent = new Date().toLocaleTimeString();
            this.streamingContainer.appendChild(metaDiv);
            
            this.streamingContainer = null;
        }
    }

    /**
     * チャットをクリア
     */
    clearChat() {
        if (this.messageContainer) {
            this.messageContainer.innerHTML = '';
        }
    }

    /**
     * システムメッセージを表示
     */
    showSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        messageDiv.textContent = message;
        this.messageContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    /**
     * エラーメッセージを表示
     */
    showErrorMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message error-message';
        messageDiv.textContent = message;
        this.messageContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    /**
     * 最下部にスクロール
     */
    scrollToBottom() {
        if (this.messageContainer) {
            this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
        }
    }

    /**
     * HTMLエスケープ
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// グローバルインスタンスを作成
let personaScenarioUI;

// DOMContentLoadedで初期化
document.addEventListener('DOMContentLoaded', () => {
    personaScenarioUI = new PersonaScenarioUI();
});

// エクスポート（モジュールとして使用する場合）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PersonaScenarioManager, PersonaScenarioUI };
}