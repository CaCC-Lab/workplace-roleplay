document.addEventListener('DOMContentLoaded', function() {
    // モーダル要素の取得
    const modal = document.getElementById('conversation-modal');
    const conversationHistory = document.getElementById('conversation-history');
    const closeBtn = modal.querySelector('.close');
    
    // 「会話を見る」ボタンのイベントリスナー
    const viewButtons = document.querySelectorAll('.view-conversation-button');
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            const id = this.getAttribute('data-id');
            
            // モーダルを表示
            modal.style.display = 'block';
            
            // 履歴データを取得
            fetchConversationHistory(type, id);
        });
    });
    
    // モーダルを閉じる
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };
    
    // モーダル外クリックで閉じる
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
    
    // 会話履歴データの取得関数
    async function fetchConversationHistory(type, id) {
        try {
            conversationHistory.innerHTML = '<div class="loading">読み込み中...</div>';
            
            // APIエンドポイントを追加
            let url = '/api/conversation_history';
            let body = { type: type };
            
            // シナリオの場合はIDも送信
            if (type === 'scenario' && id) {
                body.scenario_id = id;
            }
            
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            displayConversationHistory(data.history);
        } catch (error) {
            console.error('Error fetching conversation history:', error);
            conversationHistory.innerHTML = `<div class="error-message">エラーが発生しました: ${error.message}</div>`;
        }
    }
    
    // 履歴データの表示関数
    function displayConversationHistory(history) {
        if (!history || history.length === 0) {
            conversationHistory.innerHTML = '<div class="empty-state">会話履歴がありません</div>';
            return;
        }
        
        // 履歴のHTML構築
        let historyHTML = '<div class="conversation-container">';
        
        history.forEach(entry => {
            const timestamp = entry.timestamp ? new Date(entry.timestamp).toLocaleString('ja-JP') : '';
            
            if (entry.human) {
                historyHTML += `
                    <div class="message-entry">
                        <div class="timestamp">${timestamp}</div>
                        <div class="message user-message">
                            <strong>あなた:</strong> ${entry.human}
                        </div>
                    </div>
                `;
            }
            
            if (entry.ai) {
                historyHTML += `
                    <div class="message-entry">
                        <div class="timestamp">${timestamp}</div>
                        <div class="message bot-message">
                            <strong>相手役:</strong> ${entry.ai}
                        </div>
                    </div>
                `;
            }
        });
        
        historyHTML += '</div>';
        conversationHistory.innerHTML = historyHTML;
    }
}); 