/**
 * 非同期チャット練習用JavaScript
 * SSEストリーミング対応版
 */

const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const startButton = document.getElementById('start-practice');
const getFeedbackButton = document.getElementById('get-feedback');
const loadingDiv = document.getElementById('loading');
const feedbackArea = document.getElementById('feedback-area');

let conversationStarted = false;
let asyncChatClient = null;
let currentStreamingMessage = null;
let isStreaming = false;

// 非同期チャットクライアントの初期化
function initializeAsyncChat() {
    asyncChatClient = new AsyncChatClient({
        baseUrl: '/api/async',
        onMessage: handleStreamingMessage,
        onError: handleStreamingError,
        onComplete: handleStreamingComplete
    });
}

// ストリーミングメッセージのハンドリング
function handleStreamingMessage(data) {
    if (data.type === 'streaming') {
        if (!currentStreamingMessage) {
            // 新しいメッセージコンテナを作成
            currentStreamingMessage = createMessageElement("相手: ", "bot-message", true);
            chatMessages.appendChild(currentStreamingMessage);
        }
        
        // コンテンツを更新（Markdownをパース）
        const messageContent = currentStreamingMessage.querySelector('.message-content') || currentStreamingMessage;
        messageContent.innerHTML = marked.parse("相手: " + data.fullContent);
        
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
    
    // TTS読み上げ（既存のTTS機能を使用）
    if (currentStreamingMessage && window.ttsSettings && window.ttsSettings.enabled) {
        const textContent = data.content || currentStreamingMessage.textContent.replace('相手: ', '');
        window.speakText(textContent);
    }
    
    currentStreamingMessage = null;
    isStreaming = false;
    updateUIState();
}

// 会話開始処理（非同期版）
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
        // システムプロンプトを構築
        const systemPrompt = buildSystemPrompt(partnerType, situation, topic);
        
        // 非同期チャットで送信
        await asyncChatClient.sendMessage(systemPrompt, selectedModel);
        
        messageInput.disabled = false;
        sendButton.disabled = false;
        getFeedbackButton.disabled = false;
        conversationStarted = true;
        
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    } finally {
        loadingDiv.style.display = 'none';
        startButton.disabled = false;
    }
}

// システムプロンプトの構築
function buildSystemPrompt(partnerType, situation, topic) {
    const partnerDescriptions = {
        'colleague': '同年代の同僚',
        'senior': '経験豊富な先輩社員',
        'junior': '新入社員の後輩',
        'boss': '直属の上司',
        'client': '取引先の担当者'
    };
    
    const situationDescriptions = {
        'lunch': 'ランチ休憩中の社内カフェテリア',
        'break': '休憩時間の給湯室',
        'morning': '始業前のオフィス',
        'evening': '退社時のエレベーターホール',
        'party': '社内の懇親会'
    };
    
    const topicDescriptions = {
        'general': '天気や週末の予定などの一般的な話題',
        'hobby': '趣味や娯楽の話題',
        'news': '最近のニュースや時事問題',
        'food': '食事やグルメの話題',
        'work': '仕事に関する一般的な話題'
    };
    
    return `あなたは${partnerDescriptions[partnerType]}として振る舞い、${situationDescriptions[situation]}で${topicDescriptions[topic]}について雑談を始めてください。自然で親しみやすい会話を心がけてください。`;
}

// メッセージ送信処理（非同期版）
async function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg || isStreaming) return;

    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。", "error-message");
        return;
    }

    displayMessage("あなた: " + msg, "user-message");
    messageInput.value = "";
    isStreaming = true;
    updateUIState();

    try {
        await asyncChatClient.sendMessage(msg, selectedModel);
    } catch (error) {
        console.error("Send message error:", error);
        displayMessage("メッセージの送信に失敗しました: " + error.message, "error-message");
        isStreaming = false;
        updateUIState();
    }
}

// フィードバック取得（非同期版）
async function getFeedback() {
    if (isStreaming) return;
    
    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。", "error-message");
        return;
    }

    loadingDiv.style.display = 'block';
    getFeedbackButton.disabled = true;

    try {
        const result = await asyncChatClient.generateFeedback(selectedModel);
        
        if (result && result.feedback) {
            document.getElementById('feedback-content').innerHTML = marked.parse(result.feedback);
            feedbackArea.style.display = 'block';
            feedbackArea.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (error) {
        console.error("Feedback error:", error);
        displayMessage("フィードバックの取得に失敗しました: " + error.message, "error-message");
    } finally {
        loadingDiv.style.display = 'none';
        getFeedbackButton.disabled = false;
    }
}

// UI状態の更新
function updateUIState() {
    messageInput.disabled = isStreaming;
    sendButton.disabled = isStreaming;
    getFeedbackButton.disabled = isStreaming;
}

// メッセージ要素の作成
function createMessageElement(text, className, isBot = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = className;
    
    if (isBot) {
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = marked.parse(text);
        messageDiv.appendChild(messageContent);
    } else {
        messageDiv.textContent = text;
    }
    
    return messageDiv;
}

// メッセージ表示（既存の関数を維持）
function displayMessage(text, className, isBot = false) {
    const messageElement = createMessageElement(text, className, isBot);
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 履歴クリア処理
async function clearHistory() {
    if (!confirm("会話履歴をクリアしますか？")) return;

    try {
        const response = await fetch("/api/clear_chat_history", {
            method: "POST",
            headers: {"Content-Type": "application/json"}
        });

        if (response.ok) {
            chatMessages.innerHTML = "";
            feedbackArea.style.display = 'none';
            conversationStarted = false;
            messageInput.disabled = true;
            sendButton.disabled = true;
            getFeedbackButton.disabled = true;
            
            // 新しいセッションIDをリセット
            if (asyncChatClient) {
                asyncChatClient.sessionId = null;
            }
        }
    } catch (error) {
        console.error("Clear history error:", error);
        alert("履歴のクリアに失敗しました");
    }
}

// イベントリスナーの設定
document.addEventListener('DOMContentLoaded', function() {
    // 非同期チャットクライアントの初期化
    initializeAsyncChat();
    
    // 既存のイベントリスナー
    startButton.addEventListener('click', startConversation);
    sendButton.addEventListener('click', sendMessage);
    getFeedbackButton.addEventListener('click', getFeedback);
    document.getElementById('clear-history').addEventListener('click', clearHistory);
    
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !isStreaming) {
            sendMessage();
        }
    });

    // 初期状態の設定
    messageInput.disabled = true;
    sendButton.disabled = true;
    getFeedbackButton.disabled = true;
});