/**
 * 3者会話: /api/three-way/join, /message, /leave
 */
(function () {
    let active = false;

    function getRoot() {
        return document.getElementById("three-way-root");
    }

    function renderPanel() {
        const root = getRoot();
        if (!root) return;
        root.innerHTML = `
      <div class="settings-section" style="margin-top:1rem;">
        <h2><i class="fas fa-users"></i> 会話に参加（3者）</h2>
        <div class="action-buttons">
          <button type="button" id="three-way-join" class="primary-button"><i class="fas fa-sign-in-alt"></i> 会話に参加</button>
          <button type="button" id="three-way-leave" class="secondary-button" style="display:none;"><i class="fas fa-sign-out-alt"></i> 退出</button>
        </div>
        <div id="three-way-compose" style="display:none;margin-top:1rem;">
          <textarea id="three-way-message" class="enhanced-select" style="width:100%;min-height:80px;" placeholder="メッセージを入力"></textarea>
          <button type="button" id="three-way-send" class="primary-button" style="margin-top:0.5rem;"><i class="fas fa-paper-plane"></i> 送信</button>
        </div>
        <p id="three-way-status" class="mode-description"></p>
      </div>`;

        document.getElementById("three-way-join")?.addEventListener("click", onJoin);
        document.getElementById("three-way-leave")?.addEventListener("click", onLeave);
        document.getElementById("three-way-send")?.addEventListener("click", onSend);
    }

    async function onJoin() {
        const status = document.getElementById("three-way-status");
        try {
            const res = await fetch("/api/three-way/join", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "join failed");
            active = !!data.joined;
            if (data.joined) {
                document.getElementById("three-way-compose").style.display = "block";
                document.getElementById("three-way-leave").style.display = "inline-flex";
                document.getElementById("three-way-join").style.display = "none";
                if (status) status.textContent = "参加中。メッセージを送信できます。";
            } else {
                if (status) status.textContent = data.error || "参加できませんでした。";
            }
        } catch (e) {
            if (status) status.textContent = e.message;
        }
    }

    async function onSend() {
        const ta = document.getElementById("three-way-message");
        const msg = (ta && ta.value) || "";
        if (!msg.trim()) return;
        const status = document.getElementById("three-way-status");
        try {
            const res = await fetch("/api/three-way/message", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: msg }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "send failed");
            ta.value = "";
            if (status) status.textContent = "送信しました。次の話者: " + (data.next_speaker || "");
            if (typeof displayMessage === "function") {
                displayMessage("あなた: " + msg, "user-message");
            }
        } catch (e) {
            if (status) status.textContent = e.message;
        }
    }

    async function onLeave() {
        const status = document.getElementById("three-way-status");
        try {
            const res = await fetch("/api/three-way/leave", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "leave failed");
            active = false;
            document.getElementById("three-way-compose").style.display = "none";
            document.getElementById("three-way-leave").style.display = "none";
            document.getElementById("three-way-join").style.display = "inline-flex";
            if (status) status.textContent = "観戦モードに戻りました（mode: " + (data.mode || "watch") + "）";
        } catch (e) {
            if (status) status.textContent = e.message;
        }
    }

    document.addEventListener("DOMContentLoaded", renderPanel);
})();
