/**
 * 会話観戦モード JavaScript
 * 停止ボタン、自動進行モード、速度調整機能を含む
 */

const chatMessages = document.getElementById('chat-messages');
const startButton = document.getElementById('start-watch');
const stopButton = document.getElementById('stop-watch');
const nextButton = document.getElementById('next-message');
const clearButton = document.getElementById('clear-history');
const loadingDiv = document.getElementById('loading');
const autoModeCheckbox = document.getElementById('auto-mode');
const speedSlider = document.getElementById('speed-slider');
const speedValue = document.getElementById('speed-value');

let conversationStarted = false;
let waitingForNext = false;
let autoModeInterval = null;
let isStopped = false;

// モデルの表示名を設定
const modelDisplayNames = {
    "A": "太郎",
    "B": "花子"
};

// 速度スライダーの値を表示
speedSlider.addEventListener('input', function() {
    speedValue.textContent = this.value + '秒';
});

// 自動進行モードの切り替え
autoModeCheckbox.addEventListener('change', function() {
    if (this.checked && conversationStarted && !isStopped) {
        startAutoMode();
    } else {
        stopAutoMode();
    }
});

// 自動進行モードを開始
function startAutoMode() {
    if (autoModeInterval) {
        clearInterval(autoModeInterval);
    }
    const intervalMs = parseInt(speedSlider.value) * 1000;
    autoModeInterval = setInterval(() => {
        if (waitingForNext && !isStopped) {
            fetchNextMessage();
        }
    }, intervalMs);
}

// 自動進行モードを停止
function stopAutoMode() {
    if (autoModeInterval) {
        clearInterval(autoModeInterval);
        autoModeInterval = null;
    }
}

// 速度変更時に自動進行モードを再開
speedSlider.addEventListener('change', function() {
    if (autoModeCheckbox.checked && conversationStarted && !isStopped) {
        startAutoMode();
    }
});

// 観戦開始
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
                isStopped = false;
                
                // UIの状態を更新
                startButton.style.display = 'none';
                stopButton.style.display = 'inline-flex';
                
                // 自動進行モードが有効な場合は開始
                if (autoModeCheckbox.checked) {
                    startAutoMode();
                }
            }
        } catch (err) {
            console.error("Error:", err);
            displayMessage("エラーが発生しました: " + err.message, "error-message");
            startButton.disabled = false;
        } finally {
            loadingDiv.style.display = 'none';
        }
    }
});

// 観戦停止
stopButton.addEventListener('click', function() {
    isStopped = true;
    stopAutoMode();
    
    // UIの状態を更新
    stopButton.style.display = 'none';
    startButton.style.display = 'inline-flex';
    startButton.disabled = false;
    startButton.innerHTML = '<i class="fas fa-play"></i> 観戦を再開';
    nextButton.disabled = true;
    
    displayMessage("観戦を停止しました。「観戦を再開」ボタンで続きを見ることができます。", "system-message");
});

// 次の発言を取得
async function fetchNextMessage() {
    if (!waitingForNext || isStopped) return;
    
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
        stopAutoMode();
        autoModeCheckbox.checked = false;
    } finally {
        loadingDiv.style.display = 'none';
    }
}

// 次の発言ボタン
nextButton.addEventListener('click', function() {
    if (waitingForNext) {
        fetchNextMessage();
    }
});

// 履歴クリア
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
        startButton.style.display = 'inline-flex';
        startButton.innerHTML = '<i class="fas fa-play"></i> 観戦を始める';
        stopButton.style.display = 'none';
        conversationStarted = false;
        waitingForNext = false;
        isStopped = false;
        stopAutoMode();
        autoModeCheckbox.checked = false;
        
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
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ページ離脱時に自動進行を停止
window.addEventListener('beforeunload', function() {
    stopAutoMode();
});
