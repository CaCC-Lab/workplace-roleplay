const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const startButton = document.getElementById('start-practice');
const getFeedbackButton = document.getElementById('get-feedback');
const loadingDiv = document.getElementById('loading');
const feedbackArea = document.getElementById('feedback-area');

let conversationStarted = false;

// 会話開始処理
async function startConversation() {
    if (conversationStarted) return;

    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。トップページでモデルを選択してください。", "error-message");
        return;
    }

    const partnerType = document.getElementById('partner-type').value;
    const situation = document.getElementById('situation').value;
    const topic = document.getElementById('topic').value;

    loadingDiv.style.display = 'block';
    startButton.disabled = true;

    try {
        const response = await fetch("/api/start_chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                model: selectedModel,
                partner_type: partnerType,
                situation: situation,
                topic: topic
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        if (data.response) {
            displayMessage("相手: " + data.response, "bot-message");
            messageInput.disabled = false;
            sendButton.disabled = false;
            getFeedbackButton.disabled = false;
            conversationStarted = true;
        }
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    } finally {
        loadingDiv.style.display = 'none';
        startButton.disabled = false;
    }
}

// メッセージ送信処理
async function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg) return;

    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。", "error-message");
        return;
    }

    displayMessage("あなた: " + msg, "user-message");
    messageInput.value = "";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: msg,
                model: selectedModel
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        if (data.response) {
            displayMessage("相手: " + data.response, "bot-message");
        }
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
}

// フィードバック取得処理
async function getFeedback() {
    try {
        getFeedbackButton.disabled = true;
        getFeedbackButton.innerHTML = `
            <span class="icon">📝</span>
            フィードバック生成中...
            <span class="loading-feedback">⌛</span>
        `;
        
        const response = await fetch("/api/chat_feedback", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                partner_type: document.getElementById('partner-type').value,
                situation: document.getElementById('situation').value,
                topic: document.getElementById('topic').value
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        if (data.feedback) {
            const feedbackContent = document.getElementById('feedback-content');
            
            try {
                const parsedHtml = marked.parse(data.feedback);
                feedbackContent.innerHTML = parsedHtml;
                
                feedbackArea.style.display = 'block';
                feedbackContent.style.display = 'block';
                
                feedbackArea.scrollIntoView({ behavior: 'smooth' });
            } catch (parseError) {
                console.error("Error parsing markdown:", parseError);
                feedbackContent.textContent = data.feedback;
            }
        }
    } catch (err) {
        console.error("Error:", err);
        displayMessage("フィードバックの取得に失敗しました: " + err.message, "error-message");
    } finally {
        getFeedbackButton.disabled = false;
        getFeedbackButton.innerHTML = '<span class="icon">📝</span> フィードバックを得る';
    }
}

// 履歴クリア処理
async function clearHistory() {
    try {
        const selectedModel = localStorage.getItem('selectedModel');
        const response = await fetch("/api/clear_history", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                model: selectedModel,
                mode: "chat"
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        chatMessages.innerHTML = '';
        messageInput.disabled = true;
        sendButton.disabled = true;
        getFeedbackButton.disabled = true;
        feedbackArea.style.display = 'none';
        conversationStarted = false;

        displayMessage("会話履歴がクリアされました", "system-message");
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
}

// ユーティリティ関数
function displayMessage(text, className) {
    const div = document.createElement("div");
    div.className = "message " + className;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// イベントリスナーの設定
document.addEventListener('DOMContentLoaded', function() {
    startButton.addEventListener('click', startConversation);
    sendButton.addEventListener('click', sendMessage);
    getFeedbackButton.addEventListener('click', getFeedback);
    document.getElementById('clear-history').addEventListener('click', clearHistory);
    
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}); 