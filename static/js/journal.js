document.addEventListener('DOMContentLoaded', function() {
    console.log('Journal.js loaded'); // デバッグ用のログ
    
    // モーダル要素の取得
    const modal = document.getElementById('conversation-modal');
    const conversationHistory = document.getElementById('conversation-history');
    const closeBtn = modal.querySelector('.close');
    
    // タブ切り替え機能の追加
    const tabButtons = document.querySelectorAll('.journal-tabs .tab-button');
    console.log('Found tab buttons:', tabButtons.length); // 見つかったタブボタンの数をログ
    
    if (tabButtons.length > 0) {
        tabButtons.forEach(button => {
            console.log('Tab button found:', button.textContent.trim(), 'data-tab:', button.getAttribute('data-tab'));
        });
    } else {
        console.warn('No tab buttons found in the document. Check HTML structure.');
        // DOM構造をデバッグのためにログ出力
        console.log('Journal tabs container:', document.querySelector('.journal-tabs'));
    }
    
    const tabPanes = document.querySelectorAll('.tab-pane');
    console.log('Found tab panes:', tabPanes.length); // 見つかったタブペインの数をログ
    
    if (tabPanes.length > 0) {
        tabPanes.forEach(pane => {
            console.log('Tab pane found:', pane.id, 'classes:', pane.className);
        });
    } else {
        console.warn('No tab panes found in the document. Check HTML structure.');
    }
    
    // タブボタンのイベントリスナー
    tabButtons.forEach((button, index) => {
        console.log(`Adding click listener to button ${index}:`, button.getAttribute('data-tab')); // 各ボタンにリスナーを追加した証拠をログ
        button.addEventListener('click', function(event) {
            event.preventDefault(); // デフォルトの挙動を防止
            console.log('Button clicked:', this.getAttribute('data-tab')); // クリック時にログを出力
            
            // アクティブクラスをすべてのボタンから削除
            tabButtons.forEach(btn => btn.classList.remove('active'));
            
            // クリックされたボタンにアクティブクラスを追加
            this.classList.add('active');
            
            // クリックされたタブのデータ属性を取得
            const tab = this.getAttribute('data-tab');
            
            // ペインを全て非表示にする
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
                console.log(`Removing active class from: ${pane.id}`);
            });
            
            // 対応するペインをアクティブにする
            const activePane = document.getElementById(`${tab}-tab`);
            console.log('Activating pane:', activePane ? activePane.id : 'Not found');
            if (activePane) {
                activePane.classList.add('active');
            } else {
                console.error(`Tab pane with id '${tab}-tab' not found in the document`);
            }
        });
    });
    
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
    
    // ページ読み込み時にデフォルトタブ（シナリオ）を確実にアクティブにする
    const defaultTab = document.querySelector('.tab-button[data-tab="scenarios"]');
    console.log('Default tab:', defaultTab ? defaultTab.getAttribute('data-tab') : 'Not found');
    if (defaultTab) {
        // 少し遅延を入れてDOM構築完了後に実行
        setTimeout(() => {
            console.log('Triggering default tab click');
            defaultTab.click();
        }, 100);
    } else {
        console.warn('Default tab not found, cannot activate it');
    }
    
    // ブラウザによっては特定のイベントが発火しない場合の対策
    window.addEventListener('load', function() {
        console.log('Window fully loaded, ensuring tab functionality');
        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab) {
            console.log('Active tab found, triggering click event');
            activeTab.click();
        } else if (defaultTab) {
            console.log('No active tab found, activating default tab');
            defaultTab.click();
        }
    });
}); 