/**
 * 会話履歴管理クラス
 * ローカルストレージとサーバーサイドの同期を管理
 */
class ConversationManager {
    constructor() {
        this.currentScenarioId = null;
        this.conversations = new Map();
        this.storageKey = 'workplace_roleplay_conversations';
        this.loadFromStorage();
    }

    /**
     * ローカルストレージから会話履歴を読み込み
     */
    loadFromStorage() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const data = JSON.parse(saved);
                this.conversations = new Map(data);
            }
        } catch (error) {
            console.error('Failed to load conversations from storage:', error);
        }
    }

    /**
     * ローカルストレージに保存
     */
    saveToStorage() {
        try {
            const data = Array.from(this.conversations.entries());
            localStorage.setItem(this.storageKey, JSON.stringify(data));
        } catch (error) {
            console.error('Failed to save conversations to storage:', error);
        }
    }

    /**
     * 新しい会話を開始
     */
    startConversation(scenarioId) {
        this.currentScenarioId = scenarioId;
        if (!this.conversations.has(scenarioId)) {
            this.conversations.set(scenarioId, []);
        }
    }

    /**
     * メッセージを追加
     */
    addMessage(role, content, timestamp = new Date().toISOString()) {
        if (!this.currentScenarioId) return;

        const conversation = this.conversations.get(this.currentScenarioId) || [];
        conversation.push({
            role,
            content,
            timestamp
        });

        this.conversations.set(this.currentScenarioId, conversation);
        this.saveToStorage();
    }

    /**
     * 現在の会話履歴を取得
     */
    getCurrentConversation() {
        if (!this.currentScenarioId) return [];
        return this.conversations.get(this.currentScenarioId) || [];
    }

    /**
     * 特定のシナリオの会話履歴を取得
     */
    getConversation(scenarioId) {
        return this.conversations.get(scenarioId) || [];
    }

    /**
     * 会話履歴をクリア
     */
    clearConversation(scenarioId = null) {
        if (scenarioId) {
            this.conversations.delete(scenarioId);
        } else if (this.currentScenarioId) {
            this.conversations.delete(this.currentScenarioId);
        }
        this.saveToStorage();
    }

    /**
     * すべての会話履歴をクリア
     */
    clearAllConversations() {
        this.conversations.clear();
        this.saveToStorage();
    }

    /**
     * 会話履歴をサーバーと同期
     */
    async syncWithServer() {
        if (!this.currentScenarioId) return;

        const conversation = this.getCurrentConversation();
        if (conversation.length === 0) return;

        try {
            const response = await fetch('/api/async/scenario/sync-history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfManager ? window.csrfManager.getTokenSync() : ''
                },
                body: JSON.stringify({
                    scenario_id: this.currentScenarioId,
                    history: conversation
                })
            });

            if (!response.ok) {
                throw new Error('Failed to sync with server');
            }

            return await response.json();
        } catch (error) {
            console.error('Sync error:', error);
            throw error;
        }
    }

    /**
     * 会話履歴をエクスポート（学習記録用）
     */
    exportConversation(scenarioId = null) {
        const targetId = scenarioId || this.currentScenarioId;
        if (!targetId) return null;

        const conversation = this.getConversation(targetId);
        return {
            scenario_id: targetId,
            timestamp: new Date().toISOString(),
            messages: conversation,
            total_messages: conversation.length,
            user_messages: conversation.filter(m => m.role === 'user').length,
            ai_messages: conversation.filter(m => m.role === 'assistant').length
        };
    }
}

// グローバルインスタンスをエクスポート
window.conversationManager = new ConversationManager();