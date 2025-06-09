const scenarioId = document.currentScript.getAttribute('data-scenario-id');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');

// 画像生成機能の有効/無効フラグ（一貫性の問題がある場合は無効化可能）
let enableImageGeneration = false;

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
            displayMessage("相手役: " + data.response, "bot-message", true);
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
            displayMessage("相手役: " + data.response, "bot-message", true);
        }
    } catch (err) {
        console.error("Error:", err);
        displayMessage("エラーが発生しました: " + err.message, "error-message");
    }
});

clearButton.addEventListener('click', clearScenarioHistory);

function displayMessage(text, className, enableTTS = false) {
    const div = document.createElement("div");
    div.className = "message " + className;
    
    // AIメッセージの場合は画像を生成（有効な場合のみ）
    if (enableImageGeneration && className.includes('bot')) {
        // 画像コンテナを追加
        const imageContainer = document.createElement("div");
        imageContainer.className = "character-image-container";
        imageContainer.style.display = "none"; // 初期は非表示
        
        // ローディング表示
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "image-loading";
        loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> キャラクター画像を生成中...';
        imageContainer.appendChild(loadingDiv);
        
        div.appendChild(imageContainer);
        
        // 感情を検出
        const emotion = detectEmotion(text.replace('相手役: ', ''));
        
        // 画像生成リクエスト
        generateCharacterImage(scenarioId, emotion || 'neutral', text.replace('相手役: ', ''))
            .then(imageData => {
                if (imageData && imageData.image) {
                    imageContainer.innerHTML = ''; // ローディングをクリア
                    
                    const img = document.createElement("img");
                    img.src = `data:image/${imageData.format || 'png'};base64,${imageData.image}`;
                    img.className = "character-image";
                    img.alt = "相手役の表情";
                    
                    imageContainer.appendChild(img);
                    imageContainer.style.display = "block";
                }
            })
            .catch(error => {
                console.error("画像生成エラー:", error);
                imageContainer.style.display = "none"; // エラー時は非表示
            });
    }
    
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
        ttsButton.onclick = () => playTTS(text.replace('相手役: ', ''), ttsButton);
        messageContainer.appendChild(ttsButton);
    }
    
    div.appendChild(messageContainer);
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
            // キャラクター情報もリセット
            resetCharacterForScenario(scenarioId);
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
        
        if (response.ok && data.feedback) {
            // Markdown変換
            let feedbackHtml = marked.parse(data.feedback);
            
            // モデル情報を追加（もし存在すれば）
            if (data.model_used) {
                feedbackHtml += `<div class="model-info">使用モデル: ${data.model_used}</div>`;
            }
            
            content.innerHTML = feedbackHtml;
            content.classList.add('active');
            document.getElementById('feedback-section').scrollIntoView({ behavior: 'smooth' });
        } else {
            // エラーメッセージの表示
            const errorMsg = data.error || 'フィードバックの取得に失敗しました';
            content.innerHTML = `<div class="error-message">${errorMsg}</div>`;
            content.classList.add('active', 'error');
        }
    } catch (error) {
        console.error('フィードバック取得エラー:', error);
        const content = document.getElementById('feedback-content');
        content.innerHTML = '<div class="error-message">通信エラーが発生しました</div>';
        content.classList.add('active', 'error');
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
        // ボタンを無効化してローディング表示
        aiAssistButton.disabled = true;
        aiAssistButton.classList.add('loading');
        
        const response = await fetch("/api/get_assist", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                scenario_id: scenarioId,
                current_context: getCurrentContext()
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            if (data.suggestion) {
                let content = data.suggestion;
                
                // フォールバックモデルが使用された場合はその情報を表示
                if (data.fallback && data.fallback_model) {
                    content += `\n\n(注: APIクォータ制限のため、${data.fallback_model}モデルを使用しました)`;
                }
                
                document.getElementById('ai-assist-content').textContent = content;
                aiAssistPopup.classList.add('active');
                
                setTimeout(() => {
                    aiAssistPopup.classList.remove('active');
                }, 7000); // 少し長めに表示
            }
        } else {
            // エラーメッセージの表示
            document.getElementById('ai-assist-content').textContent = data.error || "アシスト生成中にエラーが発生しました";
            aiAssistPopup.classList.add('active', 'error');
            
            setTimeout(() => {
                aiAssistPopup.classList.remove('active', 'error');
            }, 5000);
        }
    } catch (error) {
        console.error("AIアシストエラー:", error);
        document.getElementById('ai-assist-content').textContent = "通信エラーが発生しました";
        aiAssistPopup.classList.add('active', 'error');
    } finally {
        // ボタンを再度有効化
        aiAssistButton.disabled = false;
        aiAssistButton.classList.remove('loading');
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
        
        // シナリオIDに基づいて固定の音声を使用
        const voiceMap = {
            // 男性上司系
            'scenario1': 'orus',      // 会社的な男性音声 - 40代男性課長
            'scenario3': 'orus',      // 会社的な男性音声 - 40代男性部長
            'scenario5': 'alnilam',   // プロフェッショナルな男性音声 - 男性課長
            'scenario9': 'charon',    // 深みのある男性音声 - 50代部長
            'scenario11': 'iapetus',  // 威厳のある男性音声 - 役員
            'scenario13': 'rasalgethi', // 独特で印象的な男性音声 - エンジニアリーダー
            'scenario16': 'sadachbia', // 知的な男性音声 - 経営企画部長
            'scenario22': 'gacrux',   // 安定感のある男性音声 - 営業部長
            'scenario29': 'zubenelgenubi', // バランスの取れた男性音声 - ベテラン営業マン
            
            // 女性上司・先輩系
            'scenario7': 'kore',      // 標準的な女性音声 - 女性チームリーダー
            'scenario15': 'schedar',  // 明快な女性音声 - 女性マネージャー
            'scenario17': 'vindemiatrix', // 上品な女性音声 - 女性部長
            'scenario19': 'leda',     // 優しい女性音声 - メンター先輩
            'scenario26': 'pulcherrima', // 美しい女性音声 - 広報部リーダー
            
            // 同僚系（男女混合）
            'scenario2': 'achird',    // フレンドリーな男性音声 - 同僚
            'scenario4': 'aoede',     // 明るい女性音声 - 同僚
            'scenario6': 'fenrir',    // 力強い男性音声 - 同期
            'scenario8': 'callirrhoe', // おおらかな女性音声 - 同僚
            'scenario10': 'algenib',  // 親しみやすい男性音声 - 同期
            'scenario12': 'autonoe',  // 明るい女性音声 - 同僚
            'scenario14': 'sulafat',  // エネルギッシュな男性音声 - 営業同僚
            'scenario18': 'despina',  // 陽気な女性音声 - 企画部同僚
            'scenario20': 'achernar', // 明瞭な男性音声 - エンジニア同僚
            'scenario23': 'laomedeia', // 流暢な女性音声 - マーケティング同僚
            'scenario25': 'erinome',  // 柔らかい女性音声 - 人事同僚
            'scenario27': 'enceladus', // 落ち着いた男性音声 - 経理同僚
            
            // 後輩・新人系
            'scenario21': 'puck',     // 元気な中性的音声 - 新人
            'scenario24': 'zephyr',   // 明るい中性的音声 - 後輩
            'scenario28': 'umbriel',  // 神秘的な中性的音声 - インターン
            'scenario30': 'algieba'   // 温かい女性音声 - 新人
        };
        
        // シナリオIDから音声を取得（デフォルトは kore）
        const fixedVoice = voiceMap[scenarioId] || 'kore';
        
        // TTSリクエストの準備（固定音声を使用）
        const ttsRequest = {
            text: text,
            voice: fixedVoice
        };
        
        console.log(`シナリオ ${scenarioId} の固定音声: ${fixedVoice}`);
        
        // Gemini TTS APIを呼び出し
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(ttsRequest)
        });
        
        const data = await response.json();
        console.log('TTS Response:', {
            ok: response.ok,
            status: response.status,
            hasAudio: !!data.audio,
            audioLength: data.audio ? data.audio.length : 0,
            format: data.format,
            voice: data.voice
        });
        
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
        const audioUrl = `data:audio/${audioFormat};base64,${data.audio}`;
        console.log('Audio URL created, length:', audioUrl.length);
        
        const audio = new Audio(audioUrl);
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
        console.error('Web Speech APIエラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        alert('音声読み上げ機能でエラーが発生しました');
    }
}

// シナリオごとのキャラクター画像履歴を管理
const characterImageHistory = {};
// シナリオごとの基準キャラクター情報を保存
const baseCharacterInfo = {};

// 画像生成関数
async function generateCharacterImage(scenarioId, emotion, text) {
    try {
        // このシナリオで既に画像を生成しているかチェック
        const cacheKey = `${scenarioId}_${emotion}`;
        if (characterImageHistory[cacheKey]) {
            console.log('クライアント側キャッシュヒット:', cacheKey);
            return characterImageHistory[cacheKey];
        }
        
        // 基準キャラクター情報があるか確認
        const hasBaseCharacter = baseCharacterInfo[scenarioId] !== undefined;
        
        const requestBody = {
            scenario_id: scenarioId,
            emotion: emotion,
            text: text
        };
        
        // 基準キャラクター情報がある場合は送信
        if (hasBaseCharacter) {
            requestBody.base_character = baseCharacterInfo[scenarioId];
        }
        
        const response = await fetch('/api/generate_character_image', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            console.error('画像生成APIエラー:', data);
            return null;
        }
        
        // 初回生成時は基準キャラクター情報として保存
        if (!hasBaseCharacter && data.character_info) {
            baseCharacterInfo[scenarioId] = data.character_info;
            console.log('基準キャラクター情報を保存:', scenarioId, data.character_info);
        }
        
        // クライアント側でもキャッシュ
        characterImageHistory[cacheKey] = data;
        
        return data;
        
    } catch (error) {
        console.error('画像生成エラー:', error);
        return null;
    }
}

// シナリオ開始時にキャラクター情報をリセット
function resetCharacterForScenario(scenarioId) {
    // 該当シナリオのキャッシュをクリア
    Object.keys(characterImageHistory).forEach(key => {
        if (key.startsWith(scenarioId + '_')) {
            delete characterImageHistory[key];
        }
    });
    // 基準キャラクター情報もクリア
    delete baseCharacterInfo[scenarioId];
} 