/**
 * リバースロール・シナリオ専用JavaScript
 * パワーハラスメント防止訓練モード
 * Cursor による統合設計
 */

// グローバル変数
const scenarioId = document.currentScript.getAttribute('data-scenario-id');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');

// リバースロール専用要素
const harassmentAlert = document.getElementById('harassment-alert');
const warningCounter = document.getElementById('warning-counter');
const feedbackPanel = document.getElementById('feedback-panel');
const terminateButton = document.getElementById('terminate-button');

// 状態管理
let warningCount = 0;
let maxWarnings = 3;
let sessionActive = true;
let evaluationCount = 0;
const evaluationIntervals = [3, 6, 9]; // 何回目で評価するか

// 音声機能
const audioCache = new Map();
let messageIdCounter = 0;

/**
 * リバースロール専用メッセージ送信
 */
async function sendMessage() {
    if (!sessionActive) {
        displayMessage("セッションが終了しています。", "error-message");
        return;
    }

    const msg = messageInput.value.trim();
    if (!msg) {
        displayWarning("メッセージを入力してください。", "input-validation");
        return;
    }

    const selectedModel = localStorage.getItem('selectedModel');
    if (!selectedModel) {
        displayMessage("エラー: モデルが選択されていません。", "error-message");
        return;
    }

    // ユーザーメッセージ表示（上司役として）
    displayMessage("あなた（上司役）: " + msg, "user-message manager-role");
    messageInput.value = "";
    
    // ボタン無効化
    sendButton.disabled = true;
    
    try {
        // ハラスメント検出とAI応答を同時に処理
        const [harassmentResult, aiResponse] = await Promise.all([
            checkForHarassment(msg),
            getAIResponse(msg, selectedModel)
        ]);
        
        // ハラスメント検出結果の処理
        if (harassmentResult.status === 'terminate') {
            await handleSessionTermination(harassmentResult);
            return;
        } else if (harassmentResult.status === 'warning') {
            displayHarassmentWarning(harassmentResult);
        }
        
        // AI（部下）からの応答表示
        if (aiResponse.response) {
            const aiState = aiResponse.ai_emotional_state || 'normal';
            displayMessage(
                `部下（田中さん）: ${aiResponse.response}`, 
                `bot-message subordinate-role state-${aiState}`,
                true,
                aiResponse.non_verbal_cues
            );
        }
        
        // 定期評価の実行
        evaluationCount++;
        if (evaluationIntervals.includes(evaluationCount)) {
            await performPeriodicEvaluation();
        }
        
    } catch (error) {
        console.error('Error in sendMessage:', error);
        displayMessage(`エラーが発生しました: ${error.message}`, "error-message");
    } finally {
        sendButton.disabled = false;
        messageInput.focus();
    }
}

/**
 * ハラスメント検出API呼び出し
 */
async function checkForHarassment(message) {
    try {
        const response = await fetch("/api/harassment_check", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: message,
                scenario_id: scenarioId,
                session_id: getSessionId()
            })
        });
        
        if (!response.ok) {
            throw new Error(`Harassment check failed: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Harassment detection error:', error);
        return { status: 'error', message: error.message };
    }
}

/**
 * AI（部下役）からの応答取得
 */
async function getAIResponse(message, model) {
    const response = await fetch("/api/reverse_scenario_chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            message: message,
            scenario_id: scenarioId,
            model: model,
            user_role: "manager",
            ai_role: "subordinate",
            warning_count: warningCount
        })
    });
    
    if (!response.ok) {
        throw new Error(`AI response failed: ${response.status}`);
    }
    
    return await response.json();
}

/**
 * ハラスメント警告表示
 */
function displayHarassmentWarning(result) {
    warningCount = result.warning_count || warningCount + 1;
    updateWarningCounter();

    const alertContainer = document.createElement('div');
    alertContainer.className = 'harassment-warning';

    result.alerts.forEach(alert => {
        const alertElement = document.createElement('div');
        alertElement.className = `alert-item severity-${alert.severity}`;

        const header = document.createElement('div');
        header.className = 'alert-header';
        const icon = document.createElement('i');
        icon.className = 'warning-icon';
        icon.textContent = '⚠️';
        header.appendChild(icon);
        const category = document.createElement('span');
        category.className = 'alert-category';
        category.textContent = getCategoryName(alert.category);
        header.appendChild(category);
        const severity = document.createElement('span');
        severity.className = 'alert-severity';
        severity.textContent = getSeverityLabel(alert.severity);
        header.appendChild(severity);
        alertElement.appendChild(header);

        const explanation = document.createElement('div');
        explanation.className = 'alert-explanation';
        explanation.textContent = alert.explanation;
        alertElement.appendChild(explanation);

        const suggestion = document.createElement('div');
        suggestion.className = 'alert-suggestion';
        const strong = document.createElement('strong');
        strong.textContent = '改善案: ';
        suggestion.appendChild(strong);
        suggestion.appendChild(document.createTextNode(alert.suggested_alternative));
        alertElement.appendChild(suggestion);

        if (alert.legal_note) {
            const legal = document.createElement('div');
            legal.className = 'alert-legal';
            const strong_legal = document.createElement('strong');
            strong_legal.textContent = '法的観点: ';
            legal.appendChild(strong_legal);
            legal.appendChild(document.createTextNode(alert.legal_note));
            alertElement.appendChild(legal);
        }

        alertContainer.appendChild(alertElement);
    });

    chatMessages.appendChild(alertContainer);
    scrollToBottom();

    // 3秒後にハイライト解除
    setTimeout(() => {
        alertContainer.classList.add('fade-out');
    }, 3000);
}

/**
 * セッション終了処理
 */
async function handleSessionTermination(result) {
    sessionActive = false;
    sendButton.disabled = true;
    messageInput.disabled = true;

    const terminationMessage = document.createElement('div');
    terminationMessage.className = 'session-termination critical';

    const header = document.createElement('div');
    header.className = 'termination-header';
    const icon = document.createElement('i');
    icon.className = 'stop-icon';
    icon.textContent = '🛑';
    header.appendChild(icon);
    const h3 = document.createElement('h3');
    h3.textContent = 'セッション終了';
    header.appendChild(h3);
    terminationMessage.appendChild(header);

    const reason = document.createElement('div');
    reason.className = 'termination-reason';
    reason.textContent = result.reason;
    terminationMessage.appendChild(reason);

    const action = document.createElement('div');
    action.className = 'termination-action';
    const p1 = document.createElement('p');
    p1.textContent = 'このようなコミュニケーションは職場では不適切です。';
    action.appendChild(p1);
    const p2 = document.createElement('p');
    p2.textContent = '適切なマネジメント方法について学習し、再度チャレンジしてください。';
    action.appendChild(p2);
    terminationMessage.appendChild(action);

    const buttons = document.createElement('div');
    buttons.className = 'termination-buttons';
    const restartButton = document.createElement('button');
    restartButton.className = 'restart-button';
    restartButton.textContent = 'シナリオを再開';
    restartButton.onclick = restartScenario;
    buttons.appendChild(restartButton);
    const learningButton = document.createElement('button');
    learningButton.className = 'learning-button';
    learningButton.textContent = '学習リソースを見る';
    learningButton.onclick = goToLearningResources;
    buttons.appendChild(learningButton);
    terminationMessage.appendChild(buttons);

    chatMessages.appendChild(terminationMessage);
    scrollToBottom();

    // 終了レポート生成
    await generateTerminationReport(result);
}

/**
 * 定期評価実行
 */
async function performPeriodicEvaluation() {
    try {
        const response = await fetch("/api/periodic_evaluation", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                scenario_id: scenarioId,
                evaluation_count: evaluationCount,
                session_id: getSessionId()
            })
        });
        
        if (response.ok) {
            const evaluation = await response.json();
            displayPeriodicFeedback(evaluation);
        }
    } catch (error) {
        console.error('Periodic evaluation error:', error);
    }
}

/**
 * 定期フィードバック表示
 */
function displayPeriodicFeedback(evaluation) {
    const feedbackElement = document.createElement('div');
    feedbackElement.className = `periodic-feedback ${evaluation.level}`;
    feedbackElement.innerHTML = `
        <div class="feedback-header">
            <i class="feedback-icon">${getFeedbackIcon(evaluation.level)}</i>
            <h4>コミュニケーション評価 (${evaluationCount}回目)</h4>
        </div>
        <div class="feedback-score">
            総合評価: <span class="score-${evaluation.level}">${evaluation.score_label}</span>
        </div>
        <div class="feedback-details">
            <div class="good-points">
                <h5>良い点:</h5>
                <ul>
                    ${evaluation.good_points.map(point => `<li>${point}</li>`).join('')}
                </ul>
            </div>
            <div class="improvement-points">
                <h5>改善点:</h5>
                <ul>
                    ${evaluation.improvement_points.map(point => `<li>${point}</li>`).join('')}
                </ul>
            </div>
        </div>
        <div class="feedback-suggestions">
            <h5>次の会話での心がけ:</h5>
            <p>${evaluation.next_focus}</p>
        </div>
    `;
    
    chatMessages.appendChild(feedbackElement);
    scrollToBottom();
}

/**
 * メッセージ表示（拡張版）
 */
function displayMessage(message, className, withAudio = false, nonVerbalCues = null) {
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${className}`;
    
    // メインメッセージ
    const textElement = document.createElement('div');
    textElement.className = 'message-text';
    textElement.textContent = message;
    messageElement.appendChild(textElement);
    
    // 非言語的手がかり（表情、身振りなど）
    if (nonVerbalCues) {
        const cuesElement = document.createElement('div');
        cuesElement.className = 'non-verbal-cues';
        cuesElement.innerHTML = `<small>📝 ${nonVerbalCues}</small>`;
        messageElement.appendChild(cuesElement);
    }
    
    // タイムスタンプ
    const timestamp = new Date().toLocaleTimeString();
    const timestampElement = document.createElement('div');
    timestampElement.className = 'message-timestamp';
    timestampElement.textContent = timestamp;
    messageElement.appendChild(timestampElement);
    
    chatMessages.appendChild(messageElement);
    scrollToBottom();
    
    // 音声機能（AIメッセージの場合）
    if (withAudio && className.includes('bot-message')) {
        addAudioControls(messageElement, message);
    }
}

/**
 * ユーティリティ関数群
 */
function updateWarningCounter() {
    if (warningCounter) {
        warningCounter.textContent = `警告: ${warningCount}/${maxWarnings}`;
        warningCounter.className = warningCount >= maxWarnings ? 'warning-critical' : 'warning-normal';
    }
}

function getCategoryName(category) {
    const names = {
        'physical_threat': '身体的威嚇',
        'personal_attack': '人格否定',
        'intimidation': '威圧・脅迫',
        'excessive_demands': '過大要求',
        'privacy_invasion': 'プライバシー侵害',
        'escalation': '会話エスカレーション'
    };
    return names[category] || category;
}

function getSeverityLabel(severity) {
    const labels = {
        'low': '軽微',
        'medium': '注意',
        'high': '深刻',
        'critical': '重大'
    };
    return labels[severity] || severity;
}

function getFeedbackIcon(level) {
    const icons = {
        'excellent': '🌟',
        'good': '👍', 
        'needs_improvement': '📈',
        'problematic': '⚠️'
    };
    return icons[level] || '💭';
}

function getSessionId() {
    let sessionId = localStorage.getItem('reverse_scenario_session_id');
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('reverse_scenario_session_id', sessionId);
    }
    return sessionId;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * イベントリスナー設定
 */
document.addEventListener('DOMContentLoaded', function() {
    // 送信ボタン
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    // Enter キー送信
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // クリアボタン
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            if (confirm('会話履歴をクリアしますか？')) {
                chatMessages.innerHTML = '';
                warningCount = 0;
                evaluationCount = 0;
                updateWarningCounter();
            }
        });
    }
    
    // 終了ボタン
    if (terminateButton) {
        terminateButton.addEventListener('click', function() {
            if (confirm('セッションを終了しますか？')) {
                handleVoluntaryTermination();
            }
        });
    }
    
    // 初期表示
    displayInitialInstructions();
});

/**
 * 初期説明表示
 */
function displayInitialInstructions() {
    const instructions = document.createElement('div');
    instructions.className = 'initial-instructions';
    instructions.innerHTML = `
        <div class="instructions-header">
            <i class="role-icon">👔</i>
            <h3>パワーハラスメント防止訓練</h3>
        </div>
        <div class="role-explanation">
            <p><strong>あなたの役割:</strong> 上司・管理職として部下とコミュニケーションを取ります</p>
            <p><strong>AIの役割:</strong> 部下として現実的に反応し、あなたの対応を評価します</p>
        </div>
        <div class="training-goals">
            <h4>学習目標:</h4>
            <ul>
                <li>適切な指示の伝え方を身につける</li>
                <li>部下の立場を理解したコミュニケーション</li>
                <li>パワーハラスメントを回避する意識向上</li>
                <li>建設的なフィードバック方法の習得</li>
            </ul>
        </div>
        <div class="warning-system">
            <p><strong>⚠️ 警告システム:</strong> 不適切な発言は即座に検出され、3回の警告でセッション終了となります</p>
        </div>
    `;
    
    chatMessages.appendChild(instructions);
    scrollToBottom();
}

// 追加のヘルパー関数
function restartScenario() {
    location.reload();
}

function goToLearningResources() {
    window.open('/learning_resources', '_blank');
}

async function handleVoluntaryTermination() {
    sessionActive = false;
    
    // 任意終了の処理
    const response = await fetch("/api/voluntary_termination", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            scenario_id: scenarioId,
            session_id: getSessionId(),
            evaluation_count: evaluationCount
        })
    });
    
    if (response.ok) {
        const report = await response.json();
        displayFinalReport(report);
    }
}

function displayFinalReport(report) {
    const reportElement = document.createElement('div');
    reportElement.className = 'final-report';
    reportElement.innerHTML = `
        <h3>セッション完了レポート</h3>
        <div class="report-summary">
            <p>会話回数: ${report.total_exchanges}回</p>
            <p>警告回数: ${report.warning_count}回</p>
            <p>総合評価: ${report.overall_score}</p>
        </div>
        <div class="report-feedback">
            <h4>学習成果:</h4>
            <p>${report.learning_summary}</p>
        </div>
        <div class="report-recommendations">
            <h4>今後の学習推奨事項:</h4>
            <ul>
                ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        </div>
    `;
    
    chatMessages.appendChild(reportElement);
    scrollToBottom();
}