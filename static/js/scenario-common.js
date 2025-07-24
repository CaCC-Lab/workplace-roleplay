/**
 * シナリオ練習用共通関数
 * scenario.jsとscenario-async.jsで共有される関数群
 */

// 画像生成機能の有効/無効フラグ（グローバル）
window.enableImageGeneration = false;

// シナリオごとのキャラクター画像履歴を管理
window.characterImageHistory = {};
// シナリオごとの基準キャラクター情報を保存
window.baseCharacterInfo = {};

/**
 * AIの応答から感情を検出する関数
 * @param {string} text - 分析するテキスト
 * @returns {string|null} - 検出された感情またはnull
 */
window.detectEmotion = function(text) {
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
};

/**
 * キャラクター画像を生成する関数
 * @param {string} scenarioId - シナリオID
 * @param {string} emotion - 感情
 * @param {string} text - テキスト
 * @returns {Promise<Object|null>} - 画像データまたはnull
 */
window.generateCharacterImage = async function(scenarioId, emotion, text) {
    try {
        // このシナリオで既に画像を生成しているかチェック
        const cacheKey = `${scenarioId}_${emotion}`;
        if (window.characterImageHistory[cacheKey]) {
            console.log('クライアント側キャッシュヒット:', cacheKey);
            return window.characterImageHistory[cacheKey];
        }
        
        // 基準キャラクター情報があるか確認
        const hasBaseCharacter = window.baseCharacterInfo[scenarioId] !== undefined;
        
        const requestBody = {
            scenario_id: scenarioId,
            emotion: emotion,
            text: text
        };
        
        // 基準キャラクター情報がある場合は送信
        if (hasBaseCharacter) {
            requestBody.base_character = window.baseCharacterInfo[scenarioId];
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
            window.baseCharacterInfo[scenarioId] = data.character_info;
            console.log('基準キャラクター情報を保存:', scenarioId, data.character_info);
        }
        
        // クライアント側でもキャッシュ
        window.characterImageHistory[cacheKey] = data;
        
        return data;
        
    } catch (error) {
        console.error('画像生成エラー:', error);
        return null;
    }
};

/**
 * シナリオ開始時にキャラクター情報をリセット
 * @param {string} scenarioId - シナリオID
 */
window.resetCharacterForScenario = function(scenarioId) {
    // 該当シナリオのキャッシュをクリア
    Object.keys(window.characterImageHistory).forEach(key => {
        if (key.startsWith(scenarioId + '_')) {
            delete window.characterImageHistory[key];
        }
    });
    // 基準キャラクター情報もクリア
    delete window.baseCharacterInfo[scenarioId];
};

/**
 * シンプルな事前生成関数（統一された音声選択を使用）
 * @param {string} text - 読み上げるテキスト
 * @param {string} messageId - メッセージID
 * @param {HTMLElement} button - TTSボタン要素
 */
window.preloadScenarioTTS = async function(text, messageId, button) {
    console.log(`[preloadScenarioTTS] 開始: ${messageId}`);
    
    // ローディング状態をマーク
    window.audioCache.set(messageId, 'loading');
    
    try {
        // 統一された音声選択関数を使用（tts-common.jsから）
        const voice = (typeof getVoiceForScenario === 'function') ? getVoiceForScenario() : 'kore';
        
        console.log(`[preloadScenarioTTS] Gemini TTSで生成中: ${messageId}, 音声=${voice}`);
        
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
            
            window.audioCache.set(messageId, { 
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
            messageId: messageId
        };
        
        window.audioCache.set(messageId, cacheEntry);
        
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
        
        window.audioCache.set(messageId, { 
            error: true, 
            fallback: true,
            text: text,
            voice: (typeof getVoiceForScenario === 'function') ? getVoiceForScenario() : 'kore'
        });
    }
};

/**
 * メモリ管理：古い音声データを削除
 */
window.cleanupAudioCache = function() {
    // キャッシュサイズが50を超えたら古いものから削除
    if (window.audioCache.size > 50) {
        const entriesToDelete = window.audioCache.size - 40; // 40個まで減らす
        const iterator = window.audioCache.keys();
        for (let i = 0; i < entriesToDelete; i++) {
            const keyToDelete = iterator.next().value;
            const cachedData = window.audioCache.get(keyToDelete);
            if (cachedData && cachedData.audio) {
                // Audio要素を適切にクリーンアップ
                cachedData.audio.pause();
                cachedData.audio.src = '';
            }
            window.audioCache.delete(keyToDelete);
        }
        console.log(`音声キャッシュをクリーンアップしました: ${entriesToDelete}個削除`);
    }
};

// 定期的にキャッシュをクリーンアップ
setInterval(window.cleanupAudioCache, 60000); // 1分ごと