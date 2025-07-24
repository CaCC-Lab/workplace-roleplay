/**
 * シナリオ練習用非同期JavaScript
 * SSEストリーミング対応版
 */

const scenarioId = document.currentScript?.getAttribute('data-scenario-id') || 
                  document.querySelector('script[data-scenario-id]')?.getAttribute('data-scenario-id');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');

// 画像生成機能の有効/無効フラグ
let enableImageGeneration = false;

// 音声データのキャッシュ
const audioCache = new Map();
window.audioCache = audioCache;
let messageIdCounter = 0;

// 非同期チャットクライアント
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
            currentStreamingMessage = createStreamingMessage();
            chatMessages.appendChild(currentStreamingMessage);
        }
        
        // コンテンツを更新
        updateStreamingContent(currentStreamingMessage, data.fullContent);
        
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
    
    // TTSとキャラクター画像を処理
    if (currentStreamingMessage) {
        const fullText = data.content || currentStreamingMessage.querySelector('.message-text').textContent;
        
        // TTS読み上げ
        if (window.ttsSettings && window.ttsSettings.enabled) {
            const textContent = fullText.replace('相手役: ', '');
            window.speakText(textContent);
        }
        
        // キャラクター画像生成（有効な場合）
        if (enableImageGeneration) {
            const emotion = detectEmotion(fullText.replace('相手役: ', ''));
            generateCharacterImageAsync(currentStreamingMessage, emotion, fullText.replace('相手役: ', ''));
        }
    }
    
    currentStreamingMessage = null;
    isStreaming = false;
    updateUIState();
}

// ストリーミングメッセージの作成
function createStreamingMessage() {
    const div = document.createElement("div");
    div.className = "message bot-message";
    
    const messageId = `msg-${++messageIdCounter}`;
    div.setAttribute('data-message-id', messageId);
    
    // 画像コンテナ（将来的に使用）
    if (enableImageGeneration) {
        const imageContainer = document.createElement("div");
        imageContainer.className = "character-image-container";
        imageContainer.style.display = "none";
        div.appendChild(imageContainer);
    }
    
    // メッセージコンテナ
    const messageContainer = document.createElement("div");
    messageContainer.className = "message-container";
    
    // テキスト部分
    const textSpan = document.createElement("span");
    textSpan.className = "message-text";
    textSpan.textContent = "相手役: ";
    messageContainer.appendChild(textSpan);
    
    // TTSボタン
    const ttsButton = document.createElement("button");
    ttsButton.className = "tts-button tts-loading";
    ttsButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    ttsButton.title = "音声を生成中...";
    ttsButton.disabled = true;
    ttsButton.setAttribute('data-message-id', messageId);
    messageContainer.appendChild(ttsButton);
    
    div.appendChild(messageContainer);
    return div;
}

// ストリーミングコンテンツの更新
function updateStreamingContent(messageDiv, content) {
    const textSpan = messageDiv.querySelector('.message-text');
    if (textSpan) {
        // Markdownをパースして表示
        const formattedContent = marked.parse("相手役: " + content);
        textSpan.innerHTML = formattedContent;
    }
}

// 非同期でキャラクター画像を生成
async function generateCharacterImageAsync(messageDiv, emotion, text) {
    const imageContainer = messageDiv.querySelector('.character-image-container');
    if (!imageContainer) return;
    
    imageContainer.style.display = "block";
    imageContainer.innerHTML = '<div class="image-loading"><i class="fas fa-spinner fa-spin"></i> キャラクター画像を生成中...</div>';
    
    try {
        const imageData = await generateCharacterImage(scenarioId, emotion || 'neutral', text);
        if (imageData && imageData.image) {
            imageContainer.innerHTML = '';
            
            const img = document.createElement("img");
            img.src = `data:image/${imageData.format || 'png'};base64,${imageData.image}`;
            img.className = "character-image";
            img.alt = "相手役の表情";
            
            imageContainer.appendChild(img);
        } else {
            imageContainer.style.display = "none";
        }
    } catch (error) {
        console.error("画像生成エラー:", error);
        imageContainer.style.display = "none";
    }
}

// メッセージ送信（非同期版）
async function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg || isStreaming) return;

    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。トップページでモデルを選択してください。", "error-message");
        return;
    }

    displayMessage("あなた: " + msg, "user-message");
    messageInput.value = "";
    isStreaming = true;
    updateUIState();

    try {
        await asyncChatClient.sendScenarioMessage(msg, selectedModel, scenarioId);
    } catch (error) {
        console.error("Send message error:", error);
        displayMessage("メッセージの送信に失敗しました: " + error.message, "error-message");
        isStreaming = false;
        updateUIState();
    }
}

// 初期メッセージの取得（非同期版）
async function getInitialMessage() {
    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。トップページでモデルを選択してください。", "error-message");
        return;
    }

    isStreaming = true;
    updateUIState();

    try {
        await asyncChatClient.sendScenarioMessage("", selectedModel, scenarioId);
    } catch (error) {
        console.error("Initial message error:", error);
        displayMessage("初期メッセージの取得に失敗しました: " + error.message, "error-message");
        isStreaming = false;
        updateUIState();
    }
}

// フィードバック取得（非同期版）
async function getScenarioFeedback() {
    if (isStreaming) return;
    
    const button = document.getElementById('get-feedback-button');
    const content = document.getElementById('feedback-content');
    
    button.disabled = true;
    button.textContent = "フィードバック生成中...";
    
    try {
        const selectedModel = localStorage.getItem('selectedModel');
        if (!selectedModel) {
            throw new Error("モデルが選択されていません");
        }

        const result = await asyncChatClient.generateScenarioFeedback(selectedModel, scenarioId);
        
        if (result && result.feedback) {
            // Markdown変換
            let feedbackHtml = marked.parse(result.feedback);
            
            // モデル情報を追加
            if (result.model_used) {
                feedbackHtml += `<div class="model-info">使用モデル: ${result.model_used}</div>`;
            }
            
            content.innerHTML = feedbackHtml;
            
            // 強み分析を表示（存在する場合）
            if (result.strength_analysis) {
                displayStrengthAnalysis(content, result.strength_analysis);
            }
            
            content.classList.add('active');
            document.getElementById('feedback-section').scrollIntoView({ behavior: 'smooth' });
        }
    } catch (error) {
        console.error('フィードバック取得エラー:', error);
        content.innerHTML = '<div class="error-message">フィードバックの取得に失敗しました</div>';
        content.classList.add('active', 'error');
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-clipboard-check"></i> フィードバックを取得';
    }
}

// 強み分析の表示
function displayStrengthAnalysis(container, analysis) {
    const strengthDiv = document.createElement('div');
    strengthDiv.id = 'strengthHighlight';
    strengthDiv.innerHTML = `
        <h3>🌟 あなたの強み</h3>
        <div class="strength-badges">
            ${analysis.top_strengths.map(strength => `
                <div class="strength-badge">
                    <span class="strength-name">${strength.name}</span>
                    <span class="strength-score">${Math.round(strength.score)}点</span>
                </div>
            `).join('')}
        </div>
    `;
    container.appendChild(strengthDiv);
    
    // アニメーション効果
    setTimeout(() => {
        strengthDiv.classList.add('show');
    }, 100);
}

// UI状態の更新
function updateUIState() {
    messageInput.disabled = isStreaming;
    sendButton.disabled = isStreaming;
    document.getElementById('ai-assist-button').disabled = isStreaming;
}

// メッセージ表示（既存の関数を維持）
function displayMessage(text, className, enableTTS = false) {
    const div = document.createElement("div");
    div.className = "message " + className;
    
    const messageId = `msg-${++messageIdCounter}`;
    div.setAttribute('data-message-id', messageId);
    
    // メッセージコンテナ
    const messageContainer = document.createElement("div");
    messageContainer.className = "message-container";
    
    // テキスト部分
    const textSpan = document.createElement("span");
    textSpan.className = "message-text";
    textSpan.textContent = text;
    messageContainer.appendChild(textSpan);
    
    // TTSボタンを追加（AIのメッセージのみ）
    if (enableTTS && className.includes('bot')) {
        const ttsButton = document.createElement("button");
        ttsButton.className = "tts-button tts-loading";
        ttsButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        ttsButton.title = "音声を生成中...";
        ttsButton.disabled = true;
        ttsButton.setAttribute('data-message-id', messageId);
        ttsButton.onclick = async (event) => {
            event.preventDefault();
            event.stopPropagation();
            await window.playUnifiedTTS(text.replace('相手役: ', ''), ttsButton, true, messageId);
        };
        messageContainer.appendChild(ttsButton);
        
        // 音声を事前生成
        preloadScenarioTTS(text.replace('相手役: ', ''), messageId, ttsButton);
    }
    
    div.appendChild(messageContainer);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// シナリオ履歴のクリア
async function clearScenarioHistory() {
    if (!confirm("シナリオの会話履歴をクリアしますか？")) return;

    try {
        const response = await fetch("/api/scenario_clear", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ scenario_id: scenarioId })
        });
        
        const data = await response.json();
        
        if(data.status === "success"){
            chatMessages.innerHTML = "";
            displayMessage("シナリオ履歴がクリアされました", "bot-message");
            // キャラクター情報もリセット
            resetCharacterForScenario(scenarioId);
            // 音声キャッシュもクリア
            audioCache.clear();
            // セッションIDをリセット
            if (asyncChatClient) {
                asyncChatClient.sessionId = null;
            }
        } else {
            displayMessage("エラー: " + data.message, "bot-message");
        }
    } catch (err) {
        console.error(err);
        displayMessage("エラーが発生しました", "bot-message");
    }
}

// AIアシスト機能（非同期版）
async function getAIAssist() {
    if (isStreaming) return;
    
    const button = document.getElementById('ai-assist-button');
    const popup = document.getElementById('ai-assist-popup');
    
    button.disabled = true;
    button.classList.add('loading');
    
    try {
        const selectedModel = localStorage.getItem('selectedModel');
        if (!selectedModel) {
            throw new Error("モデルが選択されていません");
        }

        const result = await asyncChatClient.getScenarioAssist(selectedModel, scenarioId, getCurrentContext());
        
        if (result && result.suggestion) {
            let content = result.suggestion;
            
            // フォールバックモデルが使用された場合
            if (result.fallback && result.fallback_model) {
                content += `\n\n(注: APIクォータ制限のため、${result.fallback_model}モデルを使用しました)`;
            }
            
            document.getElementById('ai-assist-content').textContent = content;
            popup.classList.add('active');
            
            setTimeout(() => {
                popup.classList.remove('active');
            }, 7000);
        }
    } catch (error) {
        console.error("AIアシストエラー:", error);
        document.getElementById('ai-assist-content').textContent = "アシストの取得に失敗しました";
        popup.classList.add('active', 'error');
        
        setTimeout(() => {
            popup.classList.remove('active', 'error');
        }, 5000);
    } finally {
        button.disabled = false;
        button.classList.remove('loading');
    }
}

// 現在のコンテキストを取得
function getCurrentContext() {
    const messages = document.querySelectorAll('.message');
    return Array.from(messages).slice(-3).map(msg => msg.textContent).join('\n');
}

// イベントリスナーの設定
document.addEventListener('DOMContentLoaded', function() {
    // 非同期チャットクライアントの初期化
    initializeAsyncChat();
    
    // イベントリスナー設定
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !isStreaming) {
            sendMessage();
        }
    });
    
    clearButton.addEventListener('click', clearScenarioHistory);
    
    document.getElementById('get-feedback-button').addEventListener('click', getScenarioFeedback);
    document.getElementById('ai-assist-button').addEventListener('click', getAIAssist);
    
    // ポップアップを閉じる
    document.addEventListener('click', (e) => {
        const popup = document.getElementById('ai-assist-popup');
        const button = document.getElementById('ai-assist-button');
        if (!popup.contains(e.target) && e.target !== button) {
            popup.classList.remove('active');
        }
    });
    
    // 初期メッセージの取得（CSRFManager初期化後）
    setTimeout(() => {
        waitForCSRFAndInitialize();
    }, 500);
});

// CSRFManagerの初期化を待って初期メッセージを取得
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
        
        // 初期メッセージを取得
        await getInitialMessage();
        
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
}

// 既存の関数をインポート（scenario.jsから）
// 以下の関数は既存のscenario.jsから共有される想定
// - detectEmotion
// - generateCharacterImage
// - resetCharacterForScenario
// - preloadScenarioTTS
// - cleanupAudioCache