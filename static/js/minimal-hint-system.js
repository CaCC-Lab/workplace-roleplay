/**
 * 最小限のヒントシステム
 * 要件定義書の精神に基づき、事後分析を主軸としながら
 * ユーザーが本当に困った時だけ使える補助機能
 */

class MinimalHintSystem {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.hintUsageCount = 0;
        this.maxHintsPerSession = 3;
        this.hintRequestTimeout = null;
        this.isHintActive = false;
    }

    /**
     * ヒントシステムを初期化
     */
    init(scenarioId) {
        this.scenarioId = scenarioId;
        this.render();
        this.attachEventListeners();
    }

    /**
     * ヒントボタンをレンダリング
     */
    render() {
        const hintHTML = `
            <div class="minimal-hint-system">
                <button id="hint-button" class="hint-button" title="どうしても困った時のヒント">
                    <span class="hint-icon">💡</span>
                    <span class="hint-text">ヒント</span>
                    <span class="hint-count">(残り: ${this.maxHintsPerSession - this.hintUsageCount})</span>
                </button>
                
                <div id="hint-confirmation" class="hint-confirmation" style="display: none;">
                    <p class="confirmation-message">
                        ヒントを使いますか？<br>
                        <small>まずは自分で考えてみることが大切です</small>
                    </p>
                    <div class="confirmation-buttons">
                        <button class="btn-confirm" id="confirm-hint">はい、ヒントが欲しい</button>
                        <button class="btn-cancel" id="cancel-hint">もう少し考えてみる</button>
                    </div>
                </div>
                
                <div id="hint-display" class="hint-display" style="display: none;">
                    <div class="hint-header">
                        <span class="hint-title">💡 ヒント</span>
                        <button class="hint-close" id="close-hint">×</button>
                    </div>
                    <div class="hint-content" id="hint-content"></div>
                    <p class="hint-reminder">
                        このヒントを参考に、自分の言葉で返答してみましょう
                    </p>
                </div>
                
                <div id="hint-exhausted" class="hint-exhausted" style="display: none;">
                    <p>
                        ヒントを使い切りました。<br>
                        残りは自分の力で頑張ってみましょう！
                    </p>
                </div>
            </div>
        `;

        this.container.innerHTML = hintHTML;
    }

    /**
     * イベントリスナーを設定
     */
    attachEventListeners() {
        // ヒントボタン
        document.getElementById('hint-button').addEventListener('click', () => {
            this.requestHint();
        });

        // 確認ボタン
        document.getElementById('confirm-hint').addEventListener('click', () => {
            this.showHint();
        });

        // キャンセルボタン
        document.getElementById('cancel-hint').addEventListener('click', () => {
            this.hideConfirmation();
        });

        // 閉じるボタン
        document.getElementById('close-hint').addEventListener('click', () => {
            this.hideHint();
        });
    }

    /**
     * ヒントをリクエスト
     */
    requestHint() {
        if (this.hintUsageCount >= this.maxHintsPerSession) {
            this.showExhaustedMessage();
            return;
        }

        if (this.isHintActive) {
            return;
        }

        // 確認ダイアログを表示
        this.showConfirmation();
    }

    /**
     * 確認ダイアログを表示
     */
    showConfirmation() {
        const confirmation = document.getElementById('hint-confirmation');
        confirmation.style.display = 'block';
        
        // 一定時間後に自動で閉じる（考え直す時間を与える）
        this.hintRequestTimeout = setTimeout(() => {
            this.hideConfirmation();
        }, 10000); // 10秒
    }

    /**
     * 確認ダイアログを非表示
     */
    hideConfirmation() {
        const confirmation = document.getElementById('hint-confirmation');
        confirmation.style.display = 'none';
        
        if (this.hintRequestTimeout) {
            clearTimeout(this.hintRequestTimeout);
            this.hintRequestTimeout = null;
        }
    }

    /**
     * ヒントを表示
     */
    async showHint() {
        this.hideConfirmation();
        this.isHintActive = true;
        
        // ヒントを取得
        const hint = await this.fetchHint();
        
        if (hint) {
            this.hintUsageCount++;
            this.displayHint(hint);
            this.updateHintButton();
            
            // 使用ログを記録
            this.logHintUsage();
        }
    }

    /**
     * サーバーからヒントを取得
     */
    async fetchHint() {
        try {
            // 現在の会話履歴を取得
            const conversationHistory = this.getCurrentConversationHistory();
            
            // CSRFトークンを取得（非同期）
            let csrfToken = '';
            if (window.csrfManager) {
                try {
                    csrfToken = await window.csrfManager.getToken();
                } catch (error) {
                    console.warn('Failed to get CSRF token:', error);
                    csrfToken = window.csrfManager.getTokenSync() || '';
                }
            }
            
            console.log('CSRF Token:', csrfToken ? csrfToken.substring(0, 8) + '...' : 'none');
            console.log('CSRF Manager exists:', !!window.csrfManager);
            
            const response = await fetch('/api/hint/minimal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    scenarioId: this.scenarioId,
                    conversationHistory: conversationHistory,
                    hintNumber: this.hintUsageCount + 1
                })
            });

            if (response.ok) {
                const data = await response.json();
                return data.hint;
            } else {
                console.error('ヒントの取得に失敗しました', {
                    status: response.status,
                    statusText: response.statusText,
                    headers: Object.fromEntries(response.headers.entries())
                });
                
                // レスポンス内容をログ出力
                try {
                    const errorData = await response.json();
                    console.error('Error response:', errorData);
                } catch (e) {
                    const errorText = await response.text();
                    console.error('Error response text:', errorText);
                }
                
                return null;
            }
        } catch (error) {
            console.error('ヒント取得エラー:', error);
            return null;
        }
    }

    /**
     * 現在の会話履歴を取得（実装はアプリケーションに依存）
     */
    getCurrentConversationHistory() {
        // この部分は実際のアプリケーションの実装に合わせて調整
        // 例: window.conversationManager.getHistory() など
        return [];
    }

    /**
     * ヒントを表示
     */
    displayHint(hint) {
        const hintDisplay = document.getElementById('hint-display');
        const hintContent = document.getElementById('hint-content');
        
        hintContent.innerHTML = `
            <div class="hint-type-${hint.type}">
                <p class="hint-message">${hint.message}</p>
                ${hint.example ? `
                    <div class="hint-example">
                        <strong>例:</strong>
                        <p>${hint.example}</p>
                    </div>
                ` : ''}
                ${hint.considerationPoints ? `
                    <div class="hint-points">
                        <strong>考慮ポイント:</strong>
                        <ul>
                            ${hint.considerationPoints.map(point => `<li>${point}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
        
        hintDisplay.style.display = 'block';
        
        // 30秒後に自動で閉じる
        setTimeout(() => {
            this.hideHint();
        }, 30000);
    }

    /**
     * ヒントを非表示
     */
    hideHint() {
        const hintDisplay = document.getElementById('hint-display');
        hintDisplay.style.display = 'none';
        this.isHintActive = false;
    }

    /**
     * ヒントボタンを更新
     */
    updateHintButton() {
        const hintButton = document.getElementById('hint-button');
        const hintCount = hintButton.querySelector('.hint-count');
        
        const remaining = this.maxHintsPerSession - this.hintUsageCount;
        hintCount.textContent = `(残り: ${remaining})`;
        
        if (remaining === 0) {
            hintButton.disabled = true;
            hintButton.classList.add('disabled');
        }
    }

    /**
     * ヒント使い切りメッセージを表示
     */
    showExhaustedMessage() {
        const exhausted = document.getElementById('hint-exhausted');
        exhausted.style.display = 'block';
        
        setTimeout(() => {
            exhausted.style.display = 'none';
        }, 5000);
    }

    /**
     * ヒント使用をログに記録
     */
    logHintUsage() {
        // セッションストレージに記録
        const usage = {
            scenarioId: this.scenarioId,
            hintNumber: this.hintUsageCount,
            timestamp: new Date().toISOString()
        };
        
        const existingLog = JSON.parse(
            sessionStorage.getItem('hint_usage_log') || '[]'
        );
        existingLog.push(usage);
        sessionStorage.setItem('hint_usage_log', JSON.stringify(existingLog));
    }

    /**
     * ヒント使用状況を取得
     */
    getHintUsageStats() {
        return {
            used: this.hintUsageCount,
            remaining: this.maxHintsPerSession - this.hintUsageCount,
            total: this.maxHintsPerSession
        };
    }

    /**
     * クリーンアップ
     */
    destroy() {
        if (this.hintRequestTimeout) {
            clearTimeout(this.hintRequestTimeout);
        }
    }
}