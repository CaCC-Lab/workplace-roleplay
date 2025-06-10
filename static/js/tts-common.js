/**
 * 共通TTS機能
 * 全ページで統一された音声再生・停止機能を提供
 */

// グローバル変数
window.currentAudio = null;
window.currentPlayingButton = null;

/**
 * 全ての音声再生を停止する統一関数
 */
function stopAllAudio() {
    console.log('[stopAllAudio] 停止処理を実行中...');
    
    // Audio要素による再生を停止
    if (window.currentAudio && !window.currentAudio.paused) {
        console.log('[stopAllAudio] Audio要素を停止');
        window.currentAudio.pause();
        window.currentAudio.currentTime = 0;
        window.currentAudio = null;
    }
    
    // Web Speech APIによる音声合成を停止
    if (window.speechSynthesis && window.speechSynthesis.speaking) {
        console.log('[stopAllAudio] Web Speech APIを停止');
        window.speechSynthesis.cancel();
    }
    
    // 全てのTTSボタンを元の状態に戻す
    document.querySelectorAll('.tts-button').forEach(btn => {
        if (btn.classList.contains('playing')) {
            btn.innerHTML = '<i class="fas fa-volume-up"></i>';
            btn.classList.remove('playing');
            
            // 元の状態に戻す（ready、fallback、またはloading）
            if (!btn.classList.contains('tts-ready') && !btn.classList.contains('tts-fallback') && !btn.classList.contains('tts-loading')) {
                btn.classList.add('tts-ready');
                btn.title = 'Gemini音声で読み上げ（準備完了）';
            } else if (btn.classList.contains('tts-ready')) {
                btn.title = 'Gemini音声で読み上げ（準備完了）';
            } else if (btn.classList.contains('tts-fallback')) {
                btn.title = 'システム音声で読み上げ（フォールバック）';
            }
            
            // ローディング状態でなければ有効化
            if (!btn.classList.contains('tts-loading')) {
                btn.disabled = false;
            }
        }
    });
    
    // 現在の再生ボタンをリセット
    window.currentPlayingButton = null;
    
    console.log('[stopAllAudio] 停止処理完了');
}

/**
 * 統一された音声再生関数
 */
async function playUnifiedTTS(text, button, isPreloaded = false, messageId = null) {
    console.log(`[playUnifiedTTS] ========== 開始 ==========`);
    console.log(`[playUnifiedTTS] テキスト: "${text.substring(0, 30)}..."`);
    console.log(`[playUnifiedTTS] 事前生成: ${isPreloaded}, messageId: ${messageId}`);
    console.log(`[playUnifiedTTS] キャッシュサイズ: ${window.audioCache ? window.audioCache.size : 'なし'}`);
    
    // ボタンが無効の場合は何もしない
    if (button.disabled) {
        console.log('[playUnifiedTTS] ボタンが無効のため処理をスキップ');
        return;
    }
    
    // 何か音声が再生中の場合は停止のみ実行
    if (button.classList.contains('playing') || 
        (window.currentAudio && !window.currentAudio.paused) ||
        (window.speechSynthesis && window.speechSynthesis.speaking)) {
        console.log('[playUnifiedTTS] 音声を停止します');
        stopAllAudio();
        return; // 停止のみ実行して終了
    }
    
    try {
        let audio = null;
        
        // キャッシュ確認（事前生成の場合のみ）
        if (isPreloaded && messageId && window.audioCache) {
            const cachedData = window.audioCache.get(messageId);
            console.log(`[playUnifiedTTS] ========== キャッシュ確認 ==========`);
            console.log(`[playUnifiedTTS] messageId: ${messageId}`);
            console.log(`[playUnifiedTTS] キャッシュデータ存在: ${!!cachedData}`);
            console.log(`[playUnifiedTTS] データタイプ: ${typeof cachedData}`);
            
            if (cachedData) {
                console.log(`[playUnifiedTTS] キャッシュデータ詳細:`, {
                    isLoading: cachedData === 'loading',
                    hasAudio: !!cachedData.audio,
                    hasError: !!cachedData.error,
                    requestedVoice: cachedData.requestedVoice,
                    actualVoice: cachedData.voice,
                    messageId: cachedData.messageId
                });
            }
            
            if (cachedData && cachedData !== 'loading' && cachedData.audio && !cachedData.error) {
                audio = cachedData.audio;
                console.log(`[playUnifiedTTS] ========== キャッシュから音声取得 ==========`);
                console.log(`[playUnifiedTTS] messageId: ${messageId}`);
                console.log(`[playUnifiedTTS] 要求音声: ${cachedData.requestedVoice}`);
                console.log(`[playUnifiedTTS] 実際音声: ${cachedData.voice}`);
            } else if (cachedData === 'loading') {
                console.log(`[playUnifiedTTS] ========== ローディング中のため待機 ==========`);
                console.log(`[playUnifiedTTS] messageId: ${messageId} は音声生成中です`);
                // ローディング中の場合は少し待ってから再試行
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                button.title = '音声生成完了を待機中...';
                
                setTimeout(() => {
                    playUnifiedTTS(text, button, isPreloaded, messageId);
                }, 500);
                return;
            } else if (cachedData && cachedData.error) {
                console.log(`[playUnifiedTTS] ========== キャッシュエラー処理 ==========`);
                console.log(`[playUnifiedTTS] messageId: ${messageId} にエラー情報があります`);
                // エラーがある場合はフォールバック処理
                if (cachedData.fallback && 'speechSynthesis' in window) {
                    console.log('[playUnifiedTTS] Web Speech APIにフォールバック');
                    playTTSWithWebSpeech(text, button);
                    return;
                }
            }
        }
        
        // キャッシュにない場合はリアルタイム生成
        if (!audio) {
            console.log(`[playUnifiedTTS] ========== リアルタイム生成開始 ==========`);
            console.log(`[playUnifiedTTS] 理由: キャッシュなし (messageId: ${messageId}, isPreloaded: ${isPreloaded})`);
            
            // ボタンをローディング状態に
            button.disabled = true;
            button.classList.add('tts-loading');
            button.classList.remove('tts-ready', 'tts-fallback');
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            button.title = '音声を生成中...';
            
            // シナリオ固有の音声選択
            const selectedVoice = getVoiceForScenario();
            console.log(`[playUnifiedTTS] リアルタイム生成詳細:`);
            console.log(`  - scenarioId: ${typeof scenarioId !== 'undefined' ? scenarioId : '未定義'}`);
            console.log(`  - 選択音声: ${selectedVoice}`);
            console.log(`  - messageId: ${messageId}`);
            
            // Gemini TTS APIを呼び出し
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    text: text,
                    voice: selectedVoice
                })
            });
            
            const data = await response.json();
            console.log(`[playUnifiedTTS] リアルタイム生成レスポンス: OK=${response.ok}, 要求音声=${selectedVoice}, 実際音声=${data.voice}`);
            
            if (!response.ok) {
                throw new Error(data.error || 'TTS APIエラー');
            }
            
            // Audio要素を作成
            const audioFormat = data.format || 'wav';
            audio = new Audio(`data:audio/${audioFormat};base64,${data.audio}`);
        } else {
            console.log('[playUnifiedTTS] キャッシュされた音声を使用');
        }
        
        // 音声再生の準備
        window.currentAudio = audio;
        window.currentPlayingButton = button;
        
        // ボタンを停止アイコンに変更
        button.innerHTML = '<i class="fas fa-stop"></i>';
        button.classList.remove('tts-loading', 'tts-ready', 'tts-fallback');
        button.classList.add('playing');
        button.disabled = false;
        button.title = '再生を停止';
        
        // イベントハンドラーを設定
        audio.onended = () => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            button.classList.add(button.classList.contains('tts-fallback') ? 'tts-fallback' : 'tts-ready');
            button.title = button.classList.contains('tts-fallback') ? 'システム音声で読み上げ（フォールバック）' : 'Gemini音声で読み上げ（準備完了）';
            window.currentAudio = null;
            window.currentPlayingButton = null;
            console.log('[playUnifiedTTS] 再生終了');
        };
        
        audio.onerror = () => {
            console.error('[playUnifiedTTS] 音声再生エラー');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            button.classList.add('tts-fallback');
            button.title = 'システム音声で読み上げ（エラー発生）';
            window.currentAudio = null;
            window.currentPlayingButton = null;
        };
        
        // 音声再生開始
        await audio.play();
        console.log('[playUnifiedTTS] 再生開始');
        
    } catch (error) {
        console.error('[playUnifiedTTS] エラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.classList.remove('playing', 'tts-loading');
        button.classList.add('tts-fallback');
        button.title = 'システム音声で読み上げ（エラー発生）';
        window.currentAudio = null;
        window.currentPlayingButton = null;
    }
}

/**
 * シナリオに応じた音声を取得
 */
function getVoiceForScenario() {
    if (typeof scenarioId !== 'undefined') {
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
        return voiceMap[scenarioId] || 'kore';
    }
    return 'kore'; // デフォルト
}

/**
 * Web Speech APIを使用したフォールバック関数
 */
function playTTSWithWebSpeech(text, button) {
    // Web Speech APIがサポートされているか確認
    if (!('speechSynthesis' in window)) {
        console.error('[playTTSWithWebSpeech] Web Speech APIがサポートされていません');
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.classList.add('tts-fallback');
        button.title = '音声読み上げ機能が利用できません';
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
        button.classList.remove('tts-loading', 'tts-ready');
        button.classList.add('tts-fallback');
        button.disabled = false;
        button.title = '再生を停止（システム音声）';
        window.currentPlayingButton = button; // 再生中のボタンを記録
        
        // 再生終了時の処理
        utterance.onend = () => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            button.title = 'システム音声で読み上げ（フォールバック）';
            window.currentPlayingButton = null;
            console.log('[playTTSWithWebSpeech] 再生終了');
        };
        
        // エラー時の処理
        utterance.onerror = (event) => {
            console.error('[playTTSWithWebSpeech] 音声合成エラー:', event);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            button.title = 'システム音声エラー';
            window.currentPlayingButton = null;
        };
        
        // 音声再生を開始
        window.speechSynthesis.speak(utterance);
        console.log('[playTTSWithWebSpeech] 再生開始:', text.substring(0, 20) + '...');
        
    } catch (error) {
        console.error('[playTTSWithWebSpeech] エラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.classList.remove('playing', 'tts-loading');
        button.classList.add('tts-fallback');
        button.title = 'システム音声でエラーが発生';
    }
}

/**
 * Web Speech APIフォールバック関数
 */
function playTTSWithWebSpeech(text, button) {
    console.log('[playTTSWithWebSpeech] Web Speech APIでフォールバック開始');
    
    // Web Speech APIがサポートされているか確認
    if (!('speechSynthesis' in window)) {
        console.error('[playTTSWithWebSpeech] Web Speech APIがサポートされていません');
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.title = 'システム音声で読み上げ（利用不可）';
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
        button.disabled = false;
        window.currentPlayingButton = button; // 再生中のボタンを記録
        
        // 再生終了時の処理
        utterance.onend = () => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            button.classList.add('tts-fallback');
            button.title = 'システム音声で読み上げ（フォールバック）';
            window.currentPlayingButton = null;
            console.log('[playTTSWithWebSpeech] Web Speech API再生終了');
        };
        
        // エラー時の処理
        utterance.onerror = (event) => {
            console.error('[playTTSWithWebSpeech] 音声合成エラー:', event);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.classList.remove('playing');
            button.classList.add('tts-fallback');
            button.title = 'システム音声で読み上げ（エラー）';
            window.currentPlayingButton = null;
        };
        
        // 音声再生を開始
        window.speechSynthesis.speak(utterance);
        console.log('[playTTSWithWebSpeech] Web Speech API再生開始:', text.substring(0, 20) + '...');
        
    } catch (error) {
        console.error('[playTTSWithWebSpeech] エラー:', error);
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        button.classList.add('tts-fallback');
        button.title = 'システム音声で読み上げ（エラー）';
    }
}

// グローバルに公開
window.stopAllAudio = stopAllAudio;
window.playUnifiedTTS = playUnifiedTTS;
window.playTTSWithWebSpeech = playTTSWithWebSpeech;