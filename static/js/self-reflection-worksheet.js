/**
 * 自己分析ワークシート機能
 * 要件定義書「職場のあなた再現シート」の自己分析を促進
 */

class SelfReflectionWorksheet {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.reflectionData = {
            scenarioId: null,
            conversationId: null,
            responses: {},
            emotions: [],
            timestamp: new Date().toISOString()
        };
        this.isCompleted = false;
    }

    /**
     * ワークシートを初期化
     */
    init(scenarioId, conversationId) {
        this.reflectionData.scenarioId = scenarioId;
        this.reflectionData.conversationId = conversationId;
        this.render();
        this.attachEventListeners();
    }

    /**
     * ワークシートのUIをレンダリング
     */
    render() {
        const worksheetHTML = `
            <div class="self-reflection-worksheet">
                <h2>振り返りワークシート</h2>
                <p class="worksheet-intro">
                    今回の練習を振り返って、自分の対応について考えてみましょう。
                    正解はありません。あなたの素直な気持ちを記入してください。
                </p>

                <!-- 感情の記録 -->
                <section class="emotion-section">
                    <h3>1. この場面での感情</h3>
                    <p>この場面で、あなたはどのような感情を感じましたか？（複数選択可）</p>
                    <div class="emotion-buttons">
                        <button class="emotion-btn" data-emotion="緊張">😰 緊張</button>
                        <button class="emotion-btn" data-emotion="不安">😟 不安</button>
                        <button class="emotion-btn" data-emotion="困惑">😕 困惑</button>
                        <button class="emotion-btn" data-emotion="冷静">😌 冷静</button>
                        <button class="emotion-btn" data-emotion="自信">😊 自信</button>
                        <button class="emotion-btn" data-emotion="怒り">😠 怒り</button>
                        <button class="emotion-btn" data-emotion="悲しみ">😢 悲しみ</button>
                        <button class="emotion-btn" data-emotion="安心">😊 安心</button>
                    </div>
                    <div class="selected-emotions"></div>
                </section>

                <!-- なぜその対応を選んだか -->
                <section class="reason-section">
                    <h3>2. なぜその対応を選びましたか？</h3>
                    <p>あなたがそのような返答をした理由を、自由に書いてください。</p>
                    <textarea 
                        id="reason-response" 
                        class="reflection-textarea"
                        placeholder="例：上司に失礼にならないようにしたかったから...
相手の気持ちを考えて...
自分の意見も伝えたかったから..."
                        rows="5"
                    ></textarea>
                </section>

                <!-- 相手の反応をどう感じたか -->
                <section class="perception-section">
                    <h3>3. 相手の反応をどう感じましたか？</h3>
                    <p>AIの相手があなたの対応にどう反応したか、どう感じたか書いてください。</p>
                    <textarea 
                        id="perception-response" 
                        class="reflection-textarea"
                        placeholder="例：理解してもらえたと思う...
もっと詳しく説明すべきだったかも...
予想と違う反応だった..."
                        rows="4"
                    ></textarea>
                </section>

                <!-- 次回はどうしたいか -->
                <section class="future-section">
                    <h3>4. 次回同じ場面に遭遇したら？</h3>
                    <p>もし同じような状況になったら、どのように対応したいですか？</p>
                    <textarea 
                        id="future-response" 
                        class="reflection-textarea"
                        placeholder="例：もっとはっきりと自分の意見を言いたい...
相手の話をもっとよく聞いてから返答したい...
落ち着いて対応したい..."
                        rows="4"
                    ></textarea>
                </section>

                <!-- 学んだこと -->
                <section class="learning-section">
                    <h3>5. 今回の練習で学んだこと</h3>
                    <p>この練習を通じて気づいたことや学んだことを書いてください。</p>
                    <textarea 
                        id="learning-response" 
                        class="reflection-textarea"
                        placeholder="例：自分は緊張すると早口になることに気づいた...
相手の立場を考えることの大切さを学んだ...
準備しておくことで落ち着いて対応できると分かった..."
                        rows="4"
                    ></textarea>
                </section>

                <!-- 提出ボタン -->
                <div class="worksheet-actions">
                    <button id="save-draft-btn" class="btn btn-secondary">
                        下書き保存
                    </button>
                    <button id="submit-worksheet-btn" class="btn btn-primary">
                        振り返りを完了する
                    </button>
                </div>

                <!-- 完了メッセージ -->
                <div id="completion-message" class="completion-message" style="display: none;">
                    <h3>🎉 振り返りお疲れ様でした！</h3>
                    <p>
                        自分の対応を振り返ることは、成長への第一歩です。
                        今回の気づきを、次の練習に活かしていきましょう。
                    </p>
                    <button id="view-analysis-btn" class="btn btn-primary">
                        詳細な分析結果を見る
                    </button>
                </div>
            </div>
        `;

        this.container.innerHTML = worksheetHTML;
    }

    /**
     * イベントリスナーを設定
     */
    attachEventListeners() {
        // 感情ボタンのクリックイベント
        document.querySelectorAll('.emotion-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.toggleEmotion(e.target));
        });

        // 下書き保存
        document.getElementById('save-draft-btn').addEventListener('click', () => {
            this.saveDraft();
        });

        // ワークシート提出
        document.getElementById('submit-worksheet-btn').addEventListener('click', () => {
            this.submitWorksheet();
        });

        // 分析結果表示
        document.getElementById('view-analysis-btn')?.addEventListener('click', () => {
            this.viewAnalysis();
        });

        // 自動保存（30秒ごと）
        this.autoSaveInterval = setInterval(() => {
            if (!this.isCompleted) {
                this.saveDraft(true);
            }
        }, 30000);
    }

    /**
     * 感情ボタンの選択状態を切り替え
     */
    toggleEmotion(button) {
        button.classList.toggle('selected');
        
        const emotion = button.getAttribute('data-emotion');
        const index = this.reflectionData.emotions.indexOf(emotion);
        
        if (index > -1) {
            this.reflectionData.emotions.splice(index, 1);
        } else {
            this.reflectionData.emotions.push(emotion);
        }

        this.updateSelectedEmotions();
    }

    /**
     * 選択された感情を表示
     */
    updateSelectedEmotions() {
        const container = document.querySelector('.selected-emotions');
        if (this.reflectionData.emotions.length > 0) {
            container.innerHTML = `
                <p class="selected-emotions-text">
                    選択された感情: ${this.reflectionData.emotions.join('、')}
                </p>
            `;
        } else {
            container.innerHTML = '';
        }
    }

    /**
     * 下書きを保存
     */
    saveDraft(isAutoSave = false) {
        this.collectResponses();
        
        // ローカルストレージに保存
        localStorage.setItem(
            `worksheet_draft_${this.reflectionData.scenarioId}`,
            JSON.stringify(this.reflectionData)
        );

        if (!isAutoSave) {
            this.showNotification('下書きを保存しました', 'success');
        }
    }

    /**
     * フォームデータを収集
     */
    collectResponses() {
        this.reflectionData.responses = {
            reason: document.getElementById('reason-response').value,
            perception: document.getElementById('perception-response').value,
            future: document.getElementById('future-response').value,
            learning: document.getElementById('learning-response').value
        };
    }

    /**
     * ワークシートを提出
     */
    async submitWorksheet() {
        this.collectResponses();

        // バリデーション
        if (!this.validateResponses()) {
            this.showNotification('すべての項目を記入してください', 'warning');
            return;
        }

        try {
            // APIに送信
            const response = await fetch('/api/self-reflection/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.reflectionData)
            });

            if (response.ok) {
                this.isCompleted = true;
                this.showCompletionMessage();
                
                // 下書きを削除
                localStorage.removeItem(`worksheet_draft_${this.reflectionData.scenarioId}`);
                
                // 自動保存を停止
                clearInterval(this.autoSaveInterval);
            } else {
                throw new Error('提出に失敗しました');
            }
        } catch (error) {
            console.error('ワークシート提出エラー:', error);
            this.showNotification('提出に失敗しました。もう一度お試しください。', 'error');
        }
    }

    /**
     * 入力内容のバリデーション
     */
    validateResponses() {
        const responses = this.reflectionData.responses;
        return (
            this.reflectionData.emotions.length > 0 &&
            responses.reason?.trim().length > 10 &&
            responses.perception?.trim().length > 10 &&
            responses.future?.trim().length > 10 &&
            responses.learning?.trim().length > 10
        );
    }

    /**
     * 完了メッセージを表示
     */
    showCompletionMessage() {
        // ワークシートセクションを非表示
        document.querySelectorAll('.self-reflection-worksheet > section').forEach(section => {
            section.style.display = 'none';
        });
        document.querySelector('.worksheet-actions').style.display = 'none';

        // 完了メッセージを表示
        document.getElementById('completion-message').style.display = 'block';

        // 上部にスクロール
        this.container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * 分析結果画面へ遷移
     */
    viewAnalysis() {
        window.location.href = `/analysis/${this.reflectionData.conversationId}`;
    }

    /**
     * 通知を表示
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    /**
     * 下書きを読み込み
     */
    loadDraft() {
        const draftData = localStorage.getItem(`worksheet_draft_${this.reflectionData.scenarioId}`);
        if (draftData) {
            const draft = JSON.parse(draftData);
            this.reflectionData = draft;
            
            // フォームに反映
            if (draft.responses) {
                document.getElementById('reason-response').value = draft.responses.reason || '';
                document.getElementById('perception-response').value = draft.responses.perception || '';
                document.getElementById('future-response').value = draft.responses.future || '';
                document.getElementById('learning-response').value = draft.responses.learning || '';
            }
            
            // 感情ボタンの状態を復元
            draft.emotions.forEach(emotion => {
                const btn = document.querySelector(`[data-emotion="${emotion}"]`);
                if (btn) {
                    btn.classList.add('selected');
                }
            });
            
            this.updateSelectedEmotions();
        }
    }

    /**
     * クリーンアップ
     */
    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
    }
}