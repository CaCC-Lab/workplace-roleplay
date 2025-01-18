const chatMessages = document.getElementById('chat-messages');
const startButton = document.getElementById('start-watch');
const nextButton = document.getElementById('next-message');
const clearButton = document.getElementById('clear-history');
const loadingDiv = document.getElementById('loading');

let conversationStarted = false;
let waitingForNext = false;

startButton.addEventListener('click', async function() {
    if (!conversationStarted) {
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
            const response = await fetch("/api/watch/start", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    model_a: selectedModel,
                    model_b: selectedModel,
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

            if (data.message) {
                displayMessage(data.message, "bot-message");
                nextButton.disabled = false;
                conversationStarted = true;
                waitingForNext = true;
            }
        } catch (err) {
            console.error("Error:", err);
            displayMessage("エラーが発生しました: " + err.message, "error-message");
        } finally {
            loadingDiv.style.display = 'none';
        }
    }
});

nextButton.addEventListener('click', async function() {
    if (waitingForNext) {
        loadingDiv.style.display = 'block';
        nextButton.disabled = true;

        try {
            const response = await fetch("/api/watch/next", {
                method: "POST",
                headers: {"Content-Type": "application/json"}
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }

            if (data.message) {
                displayMessage(data.message, "bot-message");
                nextButton.disabled = false;
                waitingForNext = true;
            }
        } catch (err) {
            console.error("Error:", err);
            displayMessage("エラーが発生しました: " + err.message, "error-message");
        } finally {
            loadingDiv.style.display = 'none';
        }
    }
});

clearButton.addEventListener('click', async function() {
    try {
        const response = await fetch("/api/clear_history", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
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
        nextButton.disabled = true;
        startButton.disabled = false;
        conversationStarted = false;
        waitingForNext = false;
        displayMessage("会話履歴がクリアされました", "system-message");
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
});

function displayMessage(text, className) {
    const div = document.createElement("div");
    div.className = "message " + className;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
} 