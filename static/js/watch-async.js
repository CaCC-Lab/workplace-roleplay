/**
 * 観戦モード用非同期JavaScript
 * SSEストリーミング対応版
 */

const chatMessages = document.getElementById('chat-messages');
const startButton = document.getElementById('start-watch');
const nextButton = document.getElementById('next-message');
const clearButton = document.getElementById('clear-history');
const loadingDiv = document.getElementById('loading');

// 状態管理
let conversationStarted = false;
let waitingForNext = false;
let isStreaming = false;
let currentStreamingMessage = null;

// 非同期チャットクライアント
let asyncChatClient = null;

// モデルの表示名を設定
const modelDisplayNames = {
    "A": "太郎",
    "B": "花子"
};

// 非同期チャットクライアントの初期化
function initializeAsyncWatch() {
    asyncChatClient = new AsyncChatClient({
        baseUrl: '/api/async',
        onMessage: handleStreamingMessage,
        onError: handleStreamingError,
        onComplete: handleStreamingComplete
    });
    
    // セッションIDを確保
    asyncChatClient.ensureSessionId();
}

// ストリーミングメッセージのハンドリング
function handleStreamingMessage(data) {
    if (data.type === 'streaming') {
        if (!currentStreamingMessage) {
            // 新しいメッセージコンテナを作成
            currentStreamingMessage = createStreamingMessage(data.speaker);
            chatMessages.appendChild(currentStreamingMessage);
        }
        
        // コンテンツを更新
        updateStreamingContent(currentStreamingMessage, data.fullContent, data.speaker);
        
        // スクロール
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// ストリーミングエラーのハンドリング
function handleStreamingError(error) {
    console.error('Streaming error:', error);
    displayMessage("エラーが発生しました: " + error.message, "error-message");
    isStreaming = false;
    updateUIState();
}

// ストリーミング完了のハンドリング
function handleStreamingComplete(data) {
    console.log('Streaming complete:', data);
    
    // メッセージを保存
    if (data.speaker && data.content) {
        asyncChatClient.saveWatchMessage(data.speaker, data.content);
    }
    
    currentStreamingMessage = null;
    isStreaming = false;
    updateUIState();
}

// ストリーミングメッセージの作成
function createStreamingMessage(speaker = '不明') {
    const div = document.createElement("div");
    div.className = "message bot-message";
    
    const textSpan = document.createElement("span");
    textSpan.className = "message-text";
    textSpan.textContent = `${speaker}: `;
    
    div.appendChild(textSpan);
    return div;
}

// ストリーミングコンテンツの更新
function updateStreamingContent(messageDiv, content, speaker = '不明') {
    const textSpan = messageDiv.querySelector('.message-text');
    if (textSpan) {
        // Markdownをパースして表示
        const formattedContent = marked.parse(`${speaker}: ${content}`);
        textSpan.innerHTML = formattedContent;
    }
}

// UI状態の更新
function updateUIState() {
    startButton.disabled = isStreaming || conversationStarted;
    nextButton.disabled = isStreaming || !waitingForNext;
    loadingDiv.style.display = isStreaming ? 'block' : 'none';
}

// 観戦開始
startButton.addEventListener('click', async function() {
    if (!conversationStarted && !isStreaming) {
        // モデル選択はサーバー側で管理されるためnullを使用
        const selectedModel = null;
        if (!selectedModel) {
            displayMessage("エラー: モデルが選択されていません。トップページでモデルを選択してください。", "error-message");
            return;
        }

        const partnerType = document.getElementById('partner-type').value;
        const situation = document.getElementById('situation').value;
        const topic = document.getElementById('topic').value;

        isStreaming = true;
        updateUIState();

        try {
            await asyncChatClient.startWatch({
                model_a: selectedModel,
                model_b: selectedModel,
                partner_type: partnerType,
                situation: situation,
                topic: topic
            });
            
            conversationStarted = true;
            waitingForNext = true;
            
        } catch (err) {
            console.error("Error:", err);
            displayMessage("エラーが発生しました: " + err.message, "error-message");
            isStreaming = false;
            updateUIState();
        }
    }
});

// 次の発言を取得
nextButton.addEventListener('click', async function() {
    if (waitingForNext && !isStreaming) {
        // モデル選択はサーバー側で管理されるためnullを使用
        const selectedModel = null;
        if (!selectedModel) {
            displayMessage("エラー: モデルが選択されていません。", "error-message");
            return;
        }

        isStreaming = true;
        updateUIState();

        try {
            await asyncChatClient.getNextWatchMessage(selectedModel, selectedModel);
            
        } catch (err) {
            console.error("Error:", err);
            displayMessage("エラーが発生しました: " + err.message, "error-message");
            isStreaming = false;
            updateUIState();
        }
    }
});

// 履歴クリア
clearButton.addEventListener('click', async function() {
    try {
        const response = await fetch("/api/clear_history", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                'X-CSRFToken': window.csrfManager ? window.csrfManager.getToken() : ''
            },
            body: JSON.stringify({
                mode: "watch"
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        // UI状態のリセット
        chatMessages.innerHTML = '';
        conversationStarted = false;
        waitingForNext = false;
        isStreaming = false;
        currentStreamingMessage = null;
        
        // セッションIDをリセット
        if (asyncChatClient) {
            asyncChatClient.sessionId = null;
            asyncChatClient.ensureSessionId();
        }
        
        updateUIState();
        displayMessage("会話履歴がクリアされました", "system-message");
        
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
});

// メッセージ表示
function displayMessage(text, className) {
    const div = document.createElement("div");
    div.className = "message " + className;
    
    // Markdownをパースして表示
    const formattedContent = marked.parse(text);
    div.innerHTML = formattedContent;
    
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// CSRFManagerの初期化を待つ
async function waitForCSRFAndInitialize() {
    try {
        // CSRFManagerの初期化を待つ
        let attempts = 0;
        const maxAttempts = 50; // 5秒間待機
        
        while (!window.csrfManager?.token && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (!window.csrfManager?.token) {
            console.warn('CSRF token not available, continuing without it');
        }
        
        // 非同期チャットクライアントの初期化
        initializeAsyncWatch();
        
    } catch (err) {
        console.error("Initialization error:", err);
    }
}

// ページ読み込み完了時の処理
document.addEventListener('DOMContentLoaded', function() {
    // CSRFManagerの初期化を待つ
    setTimeout(() => {
        waitForCSRFAndInitialize();
    }, 500);
});