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
                
                // 強み分析を表示（存在する場合）
                if (data.strength_analysis) {
                    const strengthDiv = document.createElement('div');
                    strengthDiv.id = 'strengthHighlight';
                    strengthDiv.innerHTML = `
                        <h3>🌟 あなたの強み</h3>
                        <div class="strength-badges">
                            ${data.strength_analysis.top_strengths.map(strength => `
                                <div class="strength-badge">
                                    <span class="strength-name">${strength.name}</span>
                                    <span class="strength-score">${Math.round(strength.score)}点</span>
                                </div>
                            `).join('')}
                        </div>
                    `;
                    feedbackContent.appendChild(strengthDiv);
                    
                    // アニメーション効果
                    setTimeout(() => {
                        strengthDiv.classList.add('show');
                    }, 100);
                }
                
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
        ttsButton.className = "tts-button tts-loading";
        ttsButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        ttsButton.title = "音声を生成中...";
        ttsButton.disabled = true; // 初期状態では無効
        ttsButton.onclick = async (event) => {
            event.preventDefault();
            event.stopPropagation();
            console.log('[ttsButton.onclick] ボタンがクリックされました');
            await window.playUnifiedTTS(text.replace('相手: ', ''), ttsButton);
        };
        messageContainer.appendChild(ttsButton);
        
        // 雑談モードでは音声を即座生成してボタンを有効化
        preloadChatTTS(text.replace('相手: ', ''), ttsButton);
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

// 全ての音声再生とWeb Speech APIを停止する関数
function stopAllAudio() {
    console.log('[stopAllAudio] 停止処理を実行中...');
    
    // Audio要素による再生を停止
    if (window.currentAudio && !window.currentAudio.paused) {
        console.log('[stopAllAudio] Audio要素を停止');
        window.currentAudio.pause();
        window.currentAudio.currentTime = 0; // 再生位置をリセット
        window.currentAudio = null;
    }
    
    // Web Speech APIによる音声合成を停止
    if (window.speechSynthesis && window.speechSynthesis.speaking) {
        console.log('[stopAllAudio] Web Speech APIを停止');
        window.speechSynthesis.cancel();
    }
    
    // 全てのTTSボタンを元の状態に戻す
    document.querySelectorAll('.tts-button').forEach(btn => {
        btn.innerHTML = '<i class="fas fa-volume-up"></i>';
        btn.disabled = false;
        btn.classList.remove('playing');
    });
    
    // 現在の再生ボタンをリセット
    window.currentPlayingButton = null;
    
    console.log('[stopAllAudio] 停止処理完了');
}

// テキスト読み上げ関数
async function playTTS(text, button) {
    console.log('[playTTS] クリックされました:', text.substring(0, 20) + '...');
    
    // 何か音声が再生中の場合は停止のみ実行
    if (button.classList.contains('playing') || 
        (window.currentAudio && !window.currentAudio.paused) ||
        (window.speechSynthesis && window.speechSynthesis.speaking)) {
        console.log('[playTTS] 音声を停止します');
        stopAllAudio();
        return; // 停止のみ実行して終了
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
        window.currentPlayingButton = button; // 再生中のボタンを記録
        
        // 再生中のアイコン表示
        button.innerHTML = '<i class="fas fa-stop"></i>';
        button.classList.add('playing');
        console.log('[playTTS] Gemini TTSで再生開始:', text.substring(0, 20) + '...');
        
        audio.onended = () => {
            // 再生終了後、元のアイコンに戻す
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            window.currentAudio = null;
        };
        
        audio.onerror = () => {
            console.error('音声再生エラー');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
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
        // 何か音声が再生中の場合は停止のみ実行
        if (button.classList.contains('playing') || window.speechSynthesis.speaking) {
            stopAllAudio();
            return; // 停止のみ実行して終了
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
        button.innerHTML = '<i class="fas fa-stop"></i>';
        button.classList.add('playing');
        window.currentPlayingButton = button; // 再生中のボタンを記録
        
        // 再生終了時の処理
        utterance.onend = () => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            window.currentPlayingButton = null;
        };
        
        // エラー時の処理
        utterance.onerror = (event) => {
            console.error('音声合成エラー:', event);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            window.currentPlayingButton = null;
        };
        
        // 音声再生を開始
        window.speechSynthesis.speak(utterance);
        console.log('[playTTSWithWebSpeech] 再生開始:', text.substring(0, 20) + '...');
        
    } catch (error) {
        console.error('Web Speech TTSエラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        alert('音声読み上げ機能が利用できません');
    }
}

// 雑談モード用の音声事前生成関数
async function preloadChatTTS(text, button) {
    console.log('[preloadChatTTS] 雑談モードで音声生成開始');
    
    try {
        // Gemini TTS APIを呼び出し
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: text,
                voice: 'kore' // 雑談モードはデフォルト音声
            })
        });
        
        const data = await response.json();
        console.log('[preloadChatTTS] APIレスポンス:', response.ok, !!data.audio);
        
        if (response.ok && data.audio) {
            // 成功時: ボタンを有効化
            button.disabled = false;
            button.classList.remove('tts-loading');
            button.classList.add('tts-ready');
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.title = 'Gemini音声で読み上げ（準備完了）';
            console.log('[preloadChatTTS] Gemini TTS生成完了');
        } else {
            // エラー時: フォールバックで有効化
            button.disabled = false;
            button.classList.remove('tts-loading');
            button.classList.add('tts-fallback');
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.title = 'システム音声で読み上げ（フォールバック）';
            console.log('[preloadChatTTS] Gemini TTSエラー、フォールバックで有効化');
        }
        
    } catch (error) {
        console.error('[preloadChatTTS] エラー:', error);
        
        // エラー時もボタンを有効化（フォールバックで再生可能）
        button.disabled = false;
        button.classList.remove('tts-loading');
        button.classList.add('tts-fallback');
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.title = 'システム音声で読み上げ（フォールバック）';
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