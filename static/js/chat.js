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
            displayMessage("相手: " + data.response, "bot-message", true);
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
            displayMessage("相手: " + data.response, "bot-message", true);
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
function displayMessage(text, className, enableTTS = false) {
    const div = document.createElement("div");
    div.className = "message " + className;
    
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
        ttsButton.className = "tts-button";
        ttsButton.innerHTML = '<i class="fas fa-volume-up"></i>';
        ttsButton.title = "読み上げ";
        ttsButton.onclick = () => playTTS(text.replace('相手: ', ''), ttsButton);
        messageContainer.appendChild(ttsButton);
    }
    
    div.appendChild(messageContainer);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// AIの応答から感情を検出する関数
function detectEmotion(text) {
    // 感情を示すキーワードと対応する感情
    const emotionPatterns = {
        happy: /嬉し|楽し|喜|笑|幸せ|ワクワク|素晴らし|最高|😊|😄|😃/,
        sad: /悲し|寂し|残念|辛|涙|落ち込|😢|😭|😔/,
        angry: /怒|腹立|イライラ|許せ|ムカ|😠|😡|💢/,
        excited: /興奮|ドキドキ|期待|楽しみ|ワクワク|すごい|やった|😆|🎉/,
        worried: /心配|不安|困|悩|迷|どうし|😟|😰|😨/,
        tired: /疲れ|眠|だる|しんど|ふぅ|はぁ|😪|😴/,
        calm: /落ち着|穏やか|静か|ゆっくり|のんびり|☺️|😌/,
        professional: /申し訳|恐れ入|お願い|いたし|ございま|です|ます/,
        friendly: /ね[！。]|よ[！。]|だね|でしょ|かな[？。]/
    };
    
    // カッコ内の感情表現をチェック
    const emotionInParentheses = text.match(/[（(]([^）)]+)[）)]/g);
    if (emotionInParentheses) {
        for (const match of emotionInParentheses) {
            const innerText = match.slice(1, -1);
            for (const [emotion, pattern] of Object.entries(emotionPatterns)) {
                if (pattern.test(innerText)) {
                    return emotion;
                }
            }
        }
    }
    
    // 本文から感情を検出
    for (const [emotion, pattern] of Object.entries(emotionPatterns)) {
        if (pattern.test(text)) {
            return emotion;
        }
    }
    
    // デフォルトは通常の感情
    return null;
}

// テキスト読み上げ関数
async function playTTS(text, button) {
    // 既に再生中の音声がある場合は停止
    if (window.currentAudio && !window.currentAudio.paused) {
        window.currentAudio.pause();
        window.currentAudio = null;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.disabled = false;
        return;
    }
    
    try {
        // ボタンを無効化してローディング表示
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        // 感情を検出
        const emotion = detectEmotion(text);
        
        // TTSリクエストの準備
        const ttsRequest = {
            text: text
        };
        
        // 感情が検出された場合、リクエストに追加
        if (emotion) {
            ttsRequest.emotion = emotion;
            console.log(`検出された感情: ${emotion}`);
        }
        
        // Gemini TTS APIを呼び出し
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(ttsRequest)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // APIエラーの場合、Web Speech APIにフォールバック
            if (data.fallback === 'Web Speech API') {
                console.log('Gemini TTSが失敗したため、Web Speech APIを使用します');
                playTTSWithWebSpeech(text, button);
                return;
            }
            throw new Error(data.error || 'TTS APIエラー');
        }
        
        // Base64デコードして音声を再生
        const audioFormat = data.format || 'wav';
        const audio = new Audio(`data:audio/${audioFormat};base64,` + data.audio);
        window.currentAudio = audio;
        
        // 再生中のアイコン表示
        button.innerHTML = '<i class="fas fa-pause"></i>';
        
        audio.onended = () => {
            // 再生終了後、元のアイコンに戻す
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            window.currentAudio = null;
        };
        
        audio.onerror = () => {
            console.error('音声再生エラー');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            window.currentAudio = null;
            // エラー時はWeb Speech APIにフォールバック
            playTTSWithWebSpeech(text, button);
        };
        
        await audio.play();
        
    } catch (error) {
        console.error('TTSエラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        // エラー時はWeb Speech APIにフォールバック
        playTTSWithWebSpeech(text, button);
    }
}

// Web Speech APIを使用したフォールバック関数
function playTTSWithWebSpeech(text, button) {
    // Web Speech APIがサポートされているか確認
    if (!('speechSynthesis' in window)) {
        alert('音声読み上げ機能が利用できません');
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        return;
    }
    
    try {
        // 既に再生中の場合は停止
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }
        
        // 音声合成の設定
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ja-JP';  // 日本語を設定
        utterance.rate = 1.0;      // 話す速度
        utterance.pitch = 1.0;     // 音の高さ
        utterance.volume = 1.0;    // 音量
        
        // 日本語の音声を選択（利用可能な場合）
        const voices = window.speechSynthesis.getVoices();
        const japaneseVoice = voices.find(voice => voice.lang === 'ja-JP');
        if (japaneseVoice) {
            utterance.voice = japaneseVoice;
        }
        
        // 再生中のアイコン表示
        button.innerHTML = '<i class="fas fa-pause"></i>';
        
        // 再生終了時の処理
        utterance.onend = () => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
        };
        
        // エラー時の処理
        utterance.onerror = (event) => {
            console.error('音声合成エラー:', event);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
        };
        
        // 音声再生を開始
        window.speechSynthesis.speak(utterance);
        
    } catch (error) {
        console.error('Web Speech TTSエラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        alert('音声読み上げ機能が利用できません');
    }
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