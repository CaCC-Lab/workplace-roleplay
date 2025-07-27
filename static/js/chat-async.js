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
        onComplete: handleStreamingComplete,
        autoReconnect: true,
        maxRetries: 3,
        errorNotifier: showErrorNotification
    });
}

// ストリーミングメッセージのハンドリング
function handleStreamingMessage(data) {
    if (data.type === 'streaming') {
        // AIが入力中インジケーターを非表示
        hideTypingIndicator();
        
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
    
    // AIが入力中インジケーターを非表示
    hideTypingIndicator();
    
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
        
        // AIが入力中インジケーターを表示
        showTypingIndicator();
        
        // 非同期チャットで送信
        await asyncChatClient.sendMessage(systemPrompt, selectedModel);
        
        messageInput.disabled = false;
        sendButton.disabled = false;
        getFeedbackButton.disabled = false;
        conversationStarted = true;
        
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
        hideTypingIndicator();
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
    
    // AIが入力中インジケーターを表示
    showTypingIndicator();

    try {
        await asyncChatClient.sendMessage(msg, selectedModel);
    } catch (error) {
        console.error("Send message error:", error);
        displayMessage("メッセージの送信に失敗しました: " + error.message, "error-message");
        hideTypingIndicator();
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

    getFeedbackButton.disabled = true;

    try {
        // 強み分析の非同期タスクを開始
        showAnalysisProgress("分析を開始しています...", 0);
        
        const startResponse = await fetch('/api/async/strength-analysis/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_type: 'chat',
                session_id: asyncChatClient.sessionId
            })
        });
        
        if (!startResponse.ok) {
            const error = await startResponse.json();
            throw new Error(error.error || '分析の開始に失敗しました');
        }
        
        const { task_id } = await startResponse.json();
        
        // プログレスをポーリング
        const analysisResult = await pollAnalysisProgress(task_id);
        
        if (analysisResult.success) {
            // 分析結果を表示
            displayAnalysisResults(analysisResult);
            
            // 従来のフィードバックも取得
            const feedbackResult = await asyncChatClient.generateFeedback(selectedModel);
            if (feedbackResult && feedbackResult.feedback) {
                document.getElementById('feedback-content').innerHTML = marked.parse(feedbackResult.feedback);
                feedbackArea.style.display = 'block';
                feedbackArea.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            throw new Error('分析に失敗しました');
        }
        
    } catch (error) {
        console.error("Feedback error:", error);
        displayMessage("フィードバックの取得に失敗しました: " + error.message, "error-message");
        hideAnalysisProgress();
    } finally {
        getFeedbackButton.disabled = false;
    }
}

// 分析プログレスの表示
function showAnalysisProgress(message, percentage) {
    let progressContainer = document.getElementById('analysis-progress');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'analysis-progress';
        progressContainer.className = 'analysis-progress-container';
        progressContainer.innerHTML = `
            <div class="progress-header">
                <i class="fas fa-brain"></i> 強み分析中...
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <span class="progress-percentage">0%</span>
            </div>
            <div class="progress-message"></div>
        `;
        
        // フィードバックエリアの前に挿入
        feedbackArea.parentNode.insertBefore(progressContainer, feedbackArea);
    }
    
    progressContainer.style.display = 'block';
    const progressFill = progressContainer.querySelector('.progress-fill');
    const progressPercentage = progressContainer.querySelector('.progress-percentage');
    const progressMessage = progressContainer.querySelector('.progress-message');
    
    progressFill.style.width = `${percentage}%`;
    progressPercentage.textContent = `${percentage}%`;
    progressMessage.textContent = message;
}

// 分析プログレスを非表示
function hideAnalysisProgress() {
    const progressContainer = document.getElementById('analysis-progress');
    if (progressContainer) {
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000);
    }
}

// 分析進捗のポーリング
async function pollAnalysisProgress(taskId) {
    const maxAttempts = 60; // 最大60秒待機
    const pollInterval = 1000; // 1秒ごとにチェック
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            const response = await fetch(`/api/async/strength-analysis/status/${taskId}`);
            const data = await response.json();
            
            if (data.state === 'SUCCESS') {
                showAnalysisProgress('分析が完了しました！', 100);
                setTimeout(() => hideAnalysisProgress(), 1000);
                return data.result;
            } else if (data.state === 'FAILURE' || data.state === 'ERROR') {
                throw new Error(data.error || '分析中にエラーが発生しました');
            } else if (data.state === 'PROGRESS') {
                const percentage = Math.round((data.current / data.total) * 100);
                showAnalysisProgress(data.status, percentage);
            } else {
                // PENDING状態
                showAnalysisProgress('分析を準備中...', 5);
            }
            
            // 次のポーリングまで待機
            await new Promise(resolve => setTimeout(resolve, pollInterval));
            
        } catch (error) {
            console.error('Polling error:', error);
            throw error;
        }
    }
    
    throw new Error('分析がタイムアウトしました');
}

// 分析結果の表示
function displayAnalysisResults(result) {
    if (!result || !result.analysis) return;
    
    const { scores, top_strengths, encouragement_messages } = result.analysis;
    
    // 強みスコアのレーダーチャート風表示を作成
    let strengthsHtml = '<div class="strength-analysis-results">';
    strengthsHtml += '<h3><i class="fas fa-chart-radar"></i> あなたの強み分析結果</h3>';
    
    // トップ強みの表示
    if (top_strengths && top_strengths.length > 0) {
        strengthsHtml += '<div class="top-strengths">';
        strengthsHtml += '<h4>特に優れている点</h4>';
        top_strengths.forEach((strength, index) => {
            const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉';
            strengthsHtml += `
                <div class="strength-item">
                    <span class="medal">${medal}</span>
                    <span class="strength-name">${strength.name}</span>
                    <span class="strength-score">${strength.score}点</span>
                </div>
            `;
        });
        strengthsHtml += '</div>';
    }
    
    // 励ましメッセージの表示
    if (encouragement_messages && encouragement_messages.length > 0) {
        strengthsHtml += '<div class="encouragement-messages">';
        encouragement_messages.forEach(message => {
            strengthsHtml += `<p class="encouragement"><i class="fas fa-star"></i> ${message}</p>`;
        });
        strengthsHtml += '</div>';
    }
    
    strengthsHtml += '</div>';
    
    // 結果を表示
    const resultsContainer = document.createElement('div');
    resultsContainer.innerHTML = strengthsHtml;
    feedbackArea.insertBefore(resultsContainer, feedbackArea.firstChild);
}

// UI状態の更新
function updateUIState() {
    messageInput.disabled = isStreaming;
    sendButton.disabled = isStreaming;
    getFeedbackButton.disabled = isStreaming;
}

// AIが入力中インジケーターを表示
function showTypingIndicator() {
    let typingIndicator = document.getElementById('typing-indicator');
    if (!typingIndicator) {
        typingIndicator = document.createElement('div');
        typingIndicator.id = 'typing-indicator';
        typingIndicator.className = 'typing-indicator bot-message';
        typingIndicator.innerHTML = `
            <div class="typing-content">
                <span class="typing-text">AIが入力中</span>
                <div class="typing-dots">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>
        `;
    }
    
    // 既存のインジケーターがなければ追加
    if (!typingIndicator.parentNode) {
        chatMessages.appendChild(typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    typingIndicator.style.display = 'block';
}

// AIが入力中インジケーターを非表示
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.style.display = 'none';
    }
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

// カスタムエラー通知関数
function showErrorNotification(errorInfo) {
    const errorContainer = document.getElementById('error-container');
    if (!errorContainer) return;
    
    // 既存の再接続通知がある場合は削除
    if (errorInfo.type === 'reconnecting') {
        const existingReconnect = errorContainer.querySelector('.alert-reconnecting');
        if (existingReconnect) {
            existingReconnect.remove();
        }
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${errorInfo.severity}`;
    if (errorInfo.type === 'reconnecting') {
        alertDiv.classList.add('alert-reconnecting');
    }
    
    // XSS対策: DOM操作で安全に要素を構築
    // アイコンの追加
    let iconClass = '';
    switch (errorInfo.severity) {
        case 'critical':
        case 'error':
            iconClass = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-triangle';
            break;
        case 'info':
            iconClass = 'fas fa-info-circle';
            break;
    }
    
    if (iconClass) {
        const icon = document.createElement('i');
        icon.className = iconClass;
        alertDiv.appendChild(icon);
    }
    
    // エラーメッセージの追加
    const errorMessage = document.createElement('span');
    errorMessage.className = 'error-message';
    errorMessage.textContent = errorInfo.userMessage;
    alertDiv.appendChild(errorMessage);
    
    // スピナーの追加（必要な場合）
    if (errorInfo.type === 'reconnecting') {
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        alertDiv.appendChild(spinner);
    }
    
    // 閉じるボタンの追加
    const closeButton = document.createElement('button');
    closeButton.className = 'close-button';
    closeButton.textContent = '×';
    closeButton.addEventListener('click', () => alertDiv.remove());
    alertDiv.appendChild(closeButton);
    
    errorContainer.appendChild(alertDiv);
    
    // 自動的に消える（再接続中とクリティカルエラー以外）
    if (errorInfo.type !== 'reconnecting' && errorInfo.severity !== 'critical') {
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 10000);
    }
    
    // 再接続が成功した場合、再接続通知を削除
    if (errorInfo.type === 'success') {
        const reconnectAlert = errorContainer.querySelector('.alert-reconnecting');
        if (reconnectAlert) {
            reconnectAlert.remove();
        }
    }
}