/**
 * チュートリアルオーバーレイ: first-visit, steps, complete
 */
(function () {
    const MODE = "scenario";

    function esc(s) {
        return String(s ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function ensureOverlay() {
        let el = document.getElementById("tutorial-overlay");
        if (el) return el;
        el = document.createElement("div");
        el.id = "tutorial-overlay";
        el.style.cssText =
            "display:none;position:fixed;inset:0;background:rgba(0,0,0,0.45);z-index:10000;align-items:center;justify-content:center;padding:1rem;";
        el.innerHTML = `
      <div class="modal-content" style="max-width:520px;position:relative;background:#fff;border-radius:12px;padding:1.5rem;">
        <h3 id="tutorial-step-title"></h3>
        <p id="tutorial-step-desc"></p>
        <div class="action-buttons" style="margin-top:1rem;">
          <button type="button" id="tutorial-next" class="primary-button">次へ</button>
          <button type="button" id="tutorial-skip" class="secondary-button">スキップ</button>
        </div>
      </div>`;
        document.body.appendChild(el);
        return el;
    }

    let steps = [];
    let idx = 0;

    function showStep() {
        const overlay = ensureOverlay();
        const st = steps[idx];
        if (!st) {
            overlay.style.display = "none";
            return;
        }
        document.getElementById("tutorial-step-title").textContent = st.title || "";
        document.getElementById("tutorial-step-desc").textContent = st.description || "";
        overlay.style.display = "flex";
    }

    async function completeCurrent() {
        const st = steps[idx];
        if (!st) return;
        await fetch("/api/tutorial/complete", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: MODE, step: st.step }),
        });
    }

    async function init() {
        try {
            const fv = await fetch("/api/tutorial/first-visit", { credentials: "same-origin" });
            const data = await fv.json();
            if (!data.first_visit) return;

            const res = await fetch(`/api/tutorial/steps?mode=${encodeURIComponent(MODE)}`, {
                credentials: "same-origin",
            });
            steps = await res.json();
            if (!Array.isArray(steps) || !steps.length) return;

            idx = 0;
            const overlay = ensureOverlay();
            showStep();

            document.getElementById("tutorial-next").onclick = async () => {
                await completeCurrent();
                idx += 1;
                if (idx >= steps.length) {
                    overlay.style.display = "none";
                    return;
                }
                showStep();
            };
            document.getElementById("tutorial-skip").onclick = () => {
                overlay.style.display = "none";
            };
        } catch (e) {
            console.warn("tutorial-overlay", e);
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
