const scenarioId = document.currentScript.getAttribute('data-scenario-id');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');

async function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg) return;

    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。トップページでモデルを選択してください。", "error-message");
        return;
    }

    displayMessage("あなた: " + msg, "user-message");
    messageInput.value = "";  // 入力欄をクリア

    try {
        const response = await fetch("/api/scenario_chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: msg,
                scenario_id: scenarioId,
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
            displayMessage("相手役: " + data.response, "bot-message");
        }
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
}

// イベントリスナーの設定
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// 初期メッセージの取得
window.addEventListener('load', async () => {
    try {
        const selectedModel = localStorage.getItem('selectedModel');
        if (!selectedModel) {
            throw new Error("モデルが選択されていません。トップページでモデルを選択してください。");
        }
        
        const response = await fetch("/api/scenario_chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: "",
                scenario_id: scenarioId,
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
            displayMessage("相手役: " + data.response, "bot-message");
        }
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
});

clearButton.addEventListener('click', clearScenarioHistory);

function displayMessage(text, className) {
    const div = document.createElement("div");
    div.className = "message " + className;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearScenarioHistory(){
    fetch("/api/scenario_clear", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ scenario_id: scenarioId })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === "success"){
            chatMessages.innerHTML = "";
            displayMessage("シナリオ履歴がクリアされました", "bot-message");
        } else {
            displayMessage("エラー: " + data.message, "bot-message");
        }
    })
    .catch(err => {
        console.error(err);
        displayMessage("エラーが発生しました", "bot-message");
    });
}

// フィードバック関連の機能
document.getElementById('get-feedback-button').addEventListener('click', async () => {
    try {
        const button = document.getElementById('get-feedback-button');
        const content = document.getElementById('feedback-content');
        
        button.disabled = true;
        button.textContent = "フィードバック生成中...";
        
        const response = await fetch('/api/scenario_feedback', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                scenario_id: scenarioId
            })
        });
        const data = await response.json();
        
        if (data.feedback) {
            content.innerHTML = marked.parse(data.feedback);
            content.classList.add('active');
            document.getElementById('feedback-section').scrollIntoView({ behavior: 'smooth' });
        }
    } catch (error) {
        console.error('フィードバック取得エラー:', error);
        alert('フィードバックの取得に失敗しました');
    } finally {
        const button = document.getElementById('get-feedback-button');
        button.disabled = false;
        button.innerHTML = '<span class="icon">📝</span> フィードバックを取得';
    }
});

// AIアシスト機能
const aiAssistButton = document.getElementById('ai-assist-button');
const aiAssistPopup = document.getElementById('ai-assist-popup');

aiAssistButton.addEventListener('click', async () => {
    try {
        const response = await fetch("/api/get_assist", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                scenario_id: scenarioId,
                current_context: getCurrentContext()
            })
        });

        const data = await response.json();
        if (data.suggestion) {
            document.getElementById('ai-assist-content').textContent = data.suggestion;
            aiAssistPopup.classList.add('active');
            
            setTimeout(() => {
                aiAssistPopup.classList.remove('active');
            }, 5000);
        }
    } catch (error) {
        console.error("AIアシストエラー:", error);
    }
});

function getCurrentContext() {
    const messages = document.querySelectorAll('.message');
    return Array.from(messages).slice(-3).map(msg => msg.textContent).join('\n');
}

document.addEventListener('click', (e) => {
    if (!aiAssistPopup.contains(e.target) && e.target !== aiAssistButton) {
        aiAssistPopup.classList.remove('active');
    }
}); 