const scenarioId = document.currentScript.getAttribute('data-scenario-id');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');

// 画像生成機能の有効/無効フラグ（一貫性の問題がある場合は無効化可能）
let enableImageGeneration = false;

// 音声データのキャッシュ（メッセージIDをキーとして音声データを保存）
const audioCache = new Map();
window.audioCache = audioCache; // 共通関数からアクセスできるように
let messageIdCounter = 0;

async function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg) return;

    // モデル選択はサーバー側で管理されるためnullを使用
    const selectedModel = null;
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
        
        // モデル選択はサーバー側で管理されるためnullを使用
    const selectedModel = null;
        if (!selectedModel) {
            throw new Error("モデルが選択されていません。トップページでモデルを選択してください。");
        }
        
        console.log('Sending initial scenario request with CSRF protection...');
        
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
}

// 初期メッセージの取得（CSRFManager初期化後）
window.addEventListener('load', () => {
    // 少し遅延させてCSRFManagerの初期化を確実に待つ
    setTimeout(waitForCSRFAndInitialize, 500);
});

clearButton.addEventListener('click', clearScenarioHistory);

function displayMessage(text, className, enableTTS = false) {
    const div = document.createElement("div");
    div.className = "message " + className;
    
    // メッセージIDを生成して要素に設定
    const messageId = `msg-${++messageIdCounter}`;
    div.setAttribute('data-message-id', messageId);
    
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
        ttsButton.className = "tts-button tts-loading";
        ttsButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        ttsButton.title = "音声を生成中...";
        ttsButton.disabled = true; // 初期状態では無効
        ttsButton.setAttribute('data-message-id', messageId);
        ttsButton.onclick = async (event) => {
            event.preventDefault();
            event.stopPropagation();
            console.log('[ttsButton.onclick] ボタンがクリックされました:', messageId);
            await window.playUnifiedTTS(text.replace('相手役: ', ''), ttsButton, true, messageId);
        };
        messageContainer.appendChild(ttsButton);
        
        // 音声を事前生成（統一TTS関数を使用）
        console.log(`[displayMessage] 事前生成開始 - messageId: ${messageId}, text: "${text.replace('相手役: ', '').substring(0, 20)}..."`);
        preloadScenarioTTS(text.replace('相手役: ', ''), messageId, ttsButton);
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
            // 音声キャッシュもクリア
            audioCache.clear();
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
                content.appendChild(strengthDiv);
                
                // アニメーション効果
                setTimeout(() => {
                    strengthDiv.classList.add('show');
                }, 100);
            }
            
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

// 注記: playTTS とplayTTSWithWebSpeech 関数は tts-common.js の統一TTS機能に置き換えられました
// 新しい統一TTS機能は playUnifiedTTS 関数として実装されています

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

// シンプルな事前生成関数（統一された音声選択を使用）
async function preloadScenarioTTS(text, messageId, button) {
    console.log(`[preloadScenarioTTS] 開始: ${messageId}`);
    
    // ローディング状態をマーク
    audioCache.set(messageId, 'loading');
    
    try {
        // 統一された音声選択関数を使用（tts-common.jsから）
        const voice = (typeof getVoiceForScenario === 'function') ? getVoiceForScenario() : 'kore';
        
        console.log(`[preloadScenarioTTS] Gemini TTSで生成中: ${messageId}, 音声=${voice}, シナリオ=${scenarioId}`);
        
        // Gemini TTS APIを呼び出し
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                text: text,
                voice: voice
            })
        });
        
        const data = await response.json();
        console.log(`[preloadScenarioTTS] APIレスポンス: ${messageId}, OK=${response.ok}, オーディオあり=${!!data.audio}, 実際の音声=${data.voice}`);
        
        if (!response.ok) {
            console.error(`[preloadScenarioTTS] Gemini TTSエラー: ${messageId}`, data.error);
            // エラー時の処理
            button.disabled = false;
            button.classList.remove('tts-loading');
            button.classList.add('tts-fallback');
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.title = 'システム音声で読み上げ（フォールバック）';
            
            audioCache.set(messageId, { 
                error: true, 
                fallback: data.fallback === 'Web Speech API',
                text: text,
                voice: voice // 要求した音声も記録
            });
            return;
        }
        
        // 音声データをキャッシュに保存
        const audioFormat = data.format || 'wav';
        const audioUrl = `data:audio/${audioFormat};base64,${data.audio}`;
        const audio = new Audio(audioUrl);
        audio.preload = 'auto';
        
        // キャッシュに保存する際に、messageIdとvoiceの組み合わせを確実に記録
        const cacheEntry = {
            audio: audio,
            text: text,
            voice: data.voice, // 実際に使用された音声
            requestedVoice: voice, // 要求した音声
            format: audioFormat,
            messageId: messageId,
            scenarioId: scenarioId
        };
        
        audioCache.set(messageId, cacheEntry);
        
        console.log(`[preloadScenarioTTS] Gemini TTS生成完了: ${messageId}, 要求音声=${voice}, 実際音声=${data.voice}`);
        
        // ボタンを有効化
        button.disabled = false;
        button.classList.remove('tts-loading');
        button.classList.add('tts-ready');
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.title = `Gemini音声で読み上げ（準備完了：${data.voice}）`;
        
    } catch (error) {
        console.error(`[preloadScenarioTTS] 事前生成エラー: ${messageId}`, error);
        
        // エラー時もボタンを有効化
        button.disabled = false;
        button.classList.remove('tts-loading');
        button.classList.add('tts-fallback');
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.title = 'システム音声で読み上げ（フォールバック）';
        
        audioCache.set(messageId, { 
            error: true, 
            fallback: true,
            text: text,
            voice: (typeof getVoiceForScenario === 'function') ? getVoiceForScenario() : 'kore'
        });
    }
}

// 従来のpreloadTTS関数（廃止予定）
async function preloadTTS_DEPRECATED(text, messageId, button) {
    console.log(`[preloadTTS] 開始: ${messageId}`);
    
    // ローディング状態をマーク
    audioCache.set(messageId, 'loading');
    
    try {
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
        
        const fixedVoice = voiceMap[scenarioId] || 'kore';
        
        console.log(`[preloadTTS] Gemini TTSで生成中: ${messageId}, 音声=${fixedVoice}`);
        
        // TTSリクエストの準備
        const ttsRequest = {
            text: text,
            voice: fixedVoice
        };
        
        // Gemini TTS APIを呼び出し
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(ttsRequest)
        });
        
        const data = await response.json();
        console.log(`[preloadTTS] APIレスポンス: ${messageId}, OK=${response.ok}, オーディオあり=${!!data.audio}`);
        
        if (!response.ok) {
            console.error(`[preloadTTS] Gemini TTSエラー: ${messageId}`, data.error);
            // エラーの場合は、ボタンを有効化してフォールバック情報を保存
            button.disabled = false;
            button.classList.remove('tts-loading');
            button.classList.add('tts-fallback');
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.title = 'システム音声で読み上げ（フォールバック）';
            
            audioCache.set(messageId, { 
                error: true, 
                fallback: data.fallback === 'Web Speech API',
                text: text 
            });
            console.log(`[preloadTTS] フォールバック情報を保存: ${messageId}`);
            return;
        }
        
        // 音声データをキャッシュに保存
        const audioFormat = data.format || 'wav';
        const audioUrl = `data:audio/${audioFormat};base64,${data.audio}`;
        
        // Audio要素を作成してキャッシュ
        const audio = new Audio(audioUrl);
        audio.preload = 'auto';
        
        audioCache.set(messageId, {
            audio: audio,
            text: text,
            voice: data.voice,
            format: audioFormat
        });
        
        console.log(`[preloadTTS] Gemini TTS生成完了: ${messageId}`);
        
        // ボタンを有効化し、スタイルを更新（Gemini準備完了を示す）
        button.disabled = false;
        button.classList.remove('tts-loading');
        button.classList.add('tts-ready');
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.title = 'Gemini音声で読み上げ（準備完了）';
        
    } catch (error) {
        console.error(`[preloadTTS] 事前生成エラー: ${messageId}`, error);
        
        // エラー時もボタンを有効化（フォールバックで再生可能）
        button.disabled = false;
        button.classList.remove('tts-loading');
        button.classList.add('tts-fallback');
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.title = 'システム音声で読み上げ（フォールバック）';
        
        audioCache.set(messageId, { 
            error: true, 
            fallback: true,
            text: text 
        });
        console.log(`[preloadTTS] エラー情報を保存: ${messageId}`);
    }
}

// 注記: playPreloadedTTS 関数は tts-common.js の統一TTS機能に置き換えられました
// 現在は playUnifiedTTS 関数がキャッシュされた音声と新規生成音声の両方を処理します

// メモリ管理：古い音声データを削除
function cleanupAudioCache() {
    // キャッシュサイズが50を超えたら古いものから削除
    if (audioCache.size > 50) {
        const entriesToDelete = audioCache.size - 40; // 40個まで減らす
        const iterator = audioCache.keys();
        for (let i = 0; i < entriesToDelete; i++) {
            const keyToDelete = iterator.next().value;
            const cachedData = audioCache.get(keyToDelete);
            if (cachedData && cachedData.audio) {
                // Audio要素を適切にクリーンアップ
                cachedData.audio.pause();
                cachedData.audio.src = '';
            }
            audioCache.delete(keyToDelete);
        }
        console.log(`音声キャッシュをクリーンアップしました: ${entriesToDelete}個削除`);
    }
}

// 定期的にキャッシュをクリーンアップ
setInterval(cleanupAudioCache, 60000); // 1分ごと 