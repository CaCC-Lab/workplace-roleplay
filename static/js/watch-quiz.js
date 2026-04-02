/**
 * 観戦クイズ: /api/watch/next の quiz をモーダル表示、/api/quiz/answer、/api/quiz/summary
 */
(function () {
    let lastQuiz = null;

    function esc(s) {
        return String(s ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function ensureModal() {
        let modal = document.getElementById("watch-quiz-modal");
        if (modal) return modal;
        modal = document.createElement("div");
        modal.id = "watch-quiz-modal";
        modal.className = "modal";
        modal.style.display = "none";
        modal.innerHTML = `
      <div class="modal-content" style="max-width:480px;">
        <span class="close" id="watch-quiz-close" style="cursor:pointer">&times;</span>
        <h3 id="watch-quiz-title">クイズ</h3>
        <p id="watch-quiz-question"></p>
        <div id="watch-quiz-choices"></div>
        <div id="watch-quiz-result" style="margin-top:1rem;"></div>
      </div>`;
        document.body.appendChild(modal);
        document.getElementById("watch-quiz-close").addEventListener("click", () => {
            modal.style.display = "none";
        });
        return modal;
    }

    function showQuizModal(quiz) {
        lastQuiz = quiz;
        const modal = ensureModal();
        const qEl = document.getElementById("watch-quiz-question");
        const cEl = document.getElementById("watch-quiz-choices");
        const rEl = document.getElementById("watch-quiz-result");
        if (rEl) rEl.innerHTML = "";
        if (qEl) qEl.textContent = quiz.question || "";
        if (cEl) {
            cEl.innerHTML = "";
            (quiz.choices || []).forEach((label, idx) => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "secondary-button";
                btn.style.margin = "0.25rem";
                btn.textContent = label;
                btn.addEventListener("click", () => submitAnswer(idx));
                cEl.appendChild(btn);
            });
        }
        modal.style.display = "block";
    }

    async function submitAnswer(idx) {
        const rEl = document.getElementById("watch-quiz-result");
        try {
            const res = await fetch("/api/quiz/answer", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_answer: idx,
                    quiz: lastQuiz,
                    context: [],
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "answer failed");
            if (rEl) {
                rEl.innerHTML = `<p><strong>${data.is_correct ? "正解！" : "不正解"}</strong></p><p>${esc(
                    data.explanation || ""
                )}</p>`;
            }
        } catch (e) {
            if (rEl) rEl.textContent = "送信に失敗しました: " + e.message;
        }
    }

    async function showQuizSummary() {
        try {
            const res = await fetch("/api/quiz/summary", { credentials: "same-origin" });
            if (!res.ok) return;
            const data = await res.json();
            const acc = data.accuracy != null ? Math.round(data.accuracy * 1000) / 10 : 0;
            const msg = `クイズ集計: 正答 ${data.correct || 0} / ${data.total || 0}（正答率 ${acc}%）`;
            if (typeof displayMessage === "function") {
                displayMessage(msg, "system-message");
            } else {
                alert(msg);
            }
        } catch (e) {
            console.warn("quiz summary", e);
        }
    }

    function patchFetch() {
        const prev = window.fetch.bind(window);
        window.fetch = async function (input, init) {
            const res = await prev(input, init);
            try {
                const url = typeof input === "string" ? input : input.url;
                if (url.includes("/api/watch/next") && res.ok) {
                    const clone = res.clone();
                    const data = await clone.json();
                    if (data && data.quiz) {
                        queueMicrotask(() => showQuizModal(data.quiz));
                    }
                }
            } catch (e) {
                console.warn("watch-quiz intercept", e);
            }
            return res;
        };
    }

    function bindSessionEnd() {
        const stopBtn = document.getElementById("stop-watch");
        if (stopBtn) {
            stopBtn.addEventListener("click", () => {
                setTimeout(showQuizSummary, 300);
            });
        }
        window.addEventListener("beforeunload", () => {
            if (document.visibilityState !== "hidden") return;
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        patchFetch();
        bindSessionEnd();
    });
})();
