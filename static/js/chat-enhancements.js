/**
 * 雑談チャット拡張: realtime_feedback、モデレーション、要約カード
 */
(function () {
    function esc(s) {
        return String(s ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function ensureHosts() {
        const cc = document.getElementById("chat-container");
        if (!cc) return;
        const anchor = document.querySelector("#chat-container .chat-area") || cc;
        let fb = document.getElementById("realtime-feedback-host");
        if (!fb) {
            fb = document.createElement("div");
            fb.id = "realtime-feedback-host";
            fb.className = "content-section";
            fb.style.marginTop = "1rem";
            if (anchor.nextSibling) {
                cc.insertBefore(fb, anchor.nextSibling);
            } else {
                cc.appendChild(fb);
            }
        }
        let sum = document.getElementById("summary-card-host");
        if (!sum) {
            sum = document.createElement("div");
            sum.id = "summary-card-host";
            sum.className = "content-section";
            sum.style.marginTop = "1rem";
            cc.appendChild(sum);
        }
    }

    function showRealtimeFeedback(fb) {
        if (!fb || !fb.has_feedback) return;
        ensureHosts();
        const host = document.getElementById("realtime-feedback-host");
        if (!host) return;
        host.style.display = "block";
        host.innerHTML = `
      <div class="card-shadow">
        <h3><i class="fas fa-lightbulb"></i> リアルタイムフィードバック</h3>
        <p>${esc(fb.suggestion || "")}</p>
        <p id="summary-trigger-wrap"><button type="button" class="secondary-button" id="btn-open-summary"><i class="fas fa-align-left"></i> 要約を見る</button></p>
      </div>`;
        document.getElementById("btn-open-summary")?.addEventListener("click", () => {
            loadSummary();
        });
    }

    function scrapeHistory() {
        const msgs = [];
        document.querySelectorAll("#chat-messages .message").forEach((el) => {
            const t = (el.textContent || "").trim();
            if (el.classList.contains("user-message")) {
                msgs.push({ role: "user", content: t.replace(/^あなた:\s*/, "") });
            } else if (el.classList.contains("bot-message")) {
                msgs.push({ role: "assistant", content: t.replace(/^相手:\s*/, "") });
            }
        });
        return msgs;
    }

    async function loadSummary() {
        ensureHosts();
        const host = document.getElementById("summary-card-host");
        if (!host) return;
        host.style.display = "block";
        host.innerHTML = "<p>要約を取得しています…</p>";
        try {
            const res = await fetch("/api/summary/generate", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ history: scrapeHistory(), mode: "chat" }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "summary failed");
            const kp = (data.key_points || []).map((x) => `<li>${esc(x)}</li>`).join("");
            const lp = (data.learning_points || []).map((x) => `<li>${esc(x)}</li>`).join("");
            host.innerHTML = `
        <div class="card-shadow">
          <h3><i class="fas fa-file-alt"></i> 要約</h3>
          <p>${esc(data.summary || "")}</p>
          <h4>キーポイント</h4><ul>${kp}</ul>
          <h4>学習ポイント</h4><ul>${lp}</ul>
        </div>`;
        } catch (e) {
            host.innerHTML = `<p class="error-message" style="display:block;">${esc(e.message)}</p>`;
        }
    }

    function showModerationWarning(data) {
        ensureHosts();
        const host = document.getElementById("realtime-feedback-host");
        if (!host) return;
        host.style.display = "block";
        const m = data.moderation || {};
        host.innerHTML = `<div class="error-message" style="display:block;">${esc(
            m.reason || "不適切な表現が含まれています。"
        )}</div>`;
    }

    function patchFetch() {
        const prev = window.fetch.bind(window);
        window.fetch = async function (input, init) {
            const res = await prev(input, init);
            try {
                const url = typeof input === "string" ? input : input.url;
                if (url.includes("/api/chat") && (init || {}).method === "POST") {
                    const clone = res.clone();
                    const data = await clone.json();
                    if (res.status === 400 && data.moderation) {
                        showModerationWarning(data);
                    } else if (res.ok && data.realtime_feedback) {
                        showRealtimeFeedback(data.realtime_feedback);
                    }
                }
            } catch (e) {
                console.warn("chat-enhancements", e);
            }
            return res;
        };
    }

    document.addEventListener("DOMContentLoaded", () => {
        ensureHosts();
        patchFetch();
    });
})();
