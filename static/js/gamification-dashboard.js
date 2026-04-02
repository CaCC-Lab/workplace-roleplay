/**
 * ゲーミフィケーション・ダッシュボード
 * /api/gamification/dashboard, /growth, /api/analytics/*, /api/export/*
 */
(function () {
    const AXIS_LABELS = {
        empathy: "共感",
        clarity: "明瞭さ",
        active_listening: "傾聴",
        adaptability: "適応",
        positivity: "前向きさ",
        professionalism: "専門性",
    };

    function esc(s) {
        return String(s ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    async function fetchJson(url) {
        const res = await fetch(url, { credentials: "same-origin" });
        if (!res.ok) throw new Error(`${url} ${res.status}`);
        return res.json();
    }

    function renderXpBars(skillXp) {
        const el = document.getElementById("xp-bars-container");
        if (!el || !skillXp || typeof skillXp !== "object") {
            if (el) el.innerHTML = "<p>データがありません。</p>";
            return;
        }
        const max = Math.max(1, ...Object.values(skillXp).map((v) => Number(v) || 0));
        el.innerHTML = Object.entries(skillXp)
            .map(([k, v]) => {
                const n = Number(v) || 0;
                const pct = Math.min(100, Math.round((n / max) * 100));
                const label = AXIS_LABELS[k] || k;
                return `<div style="margin-bottom:0.75rem;">
          <div style="display:flex;justify-content:space-between;font-size:0.9rem;">
            <span>${esc(label)}</span><span>${esc(n)} XP</span>
          </div>
          <div style="background:#e5e7eb;border-radius:8px;height:10px;overflow:hidden;">
            <div style="width:${pct}%;height:100%;background:var(--primary-color,#3b3b6b);"></div>
          </div>
        </div>`;
            })
            .join("");
    }

    function renderQuests(questsPayload) {
        const dailyEl = document.getElementById("quests-daily");
        const weeklyEl = document.getElementById("quests-weekly");
        if (!questsPayload || typeof questsPayload !== "object") return;
        const daily = questsPayload.daily || [];
        const weekly = questsPayload.weekly || [];
        const fmt = (list, title) => {
            if (!list.length) return `<p><strong>${esc(title)}</strong>: なし</p>`;
            return `<p><strong>${esc(title)}</strong></p><ul>${list
                .map(
                    (q) =>
                        `<li>${esc(q.description || q.title || "")} — ${esc(q.current_value)}/${esc(
                            q.target_value
                        )}</li>`
                )
                .join("")}</ul>`;
        };
        if (dailyEl) dailyEl.innerHTML = fmt(daily, "デイリー");
        if (weeklyEl) weeklyEl.innerHTML = fmt(weekly, "ウィークリー");
    }

    function renderBadges(overview) {
        const grid = document.getElementById("badge-grid");
        if (!grid) return;
        const items = (overview && overview.badges) || [];
        if (!items.length) {
            grid.innerHTML = "<p>バッジ情報がありません。</p>";
            return;
        }
        grid.innerHTML = items
            .map((row) => {
                const b = row.badge || row;
                const earned = b.earned ? "獲得済" : "未獲得";
                const cls = b.earned ? "feature-card" : "feature-card feature-card--locked";
                return `<div class="${cls}" style="opacity:${b.earned ? 1 : 0.75}">
            <h3>${esc(b.name || b.badge_id)}</h3>
            <p>${esc(earned)}</p>
          </div>`;
            })
            .join("");
    }

    function renderAnalytics(practice, skills, weakness) {
        const p = document.getElementById("analytics-practice");
        const s = document.getElementById("analytics-skills");
        const w = document.getElementById("analytics-weakness");
        if (p && practice) {
            p.innerHTML = `<p>累計時間: ${esc(practice.total_time_minutes)} 分 / セッション数: ${esc(
                practice.session_count
            )} / 平均: ${esc(practice.avg_session_minutes)} 分 / 活発な曜日: ${esc(
                practice.most_active_day
            )}</p>`;
        }
        if (s && skills && typeof skills === "object") {
            s.innerHTML =
                "<p><strong>6軸スキル</strong></p><ul>" +
                Object.entries(skills)
                    .map(([axis, row]) => {
                        const r = row || {};
                        return `<li>${esc(AXIS_LABELS[axis] || axis)}: 現在 ${esc(
                            r.current
                        )} / 成長率 ${esc(r.growth_rate)} / ランク ${esc(r.rank)}</li>`;
                    })
                    .join("") +
                "</ul>";
        }
        if (w && Array.isArray(weakness)) {
            w.innerHTML =
                "<p><strong>改善ポイント</strong></p><ul>" +
                weakness
                    .slice(0, 6)
                    .map(
                        (x) =>
                            `<li>${esc(AXIS_LABELS[x.axis] || x.axis)} (score ${esc(x.score)}): ${esc(
                                x.recommendation
                            )}</li>`
                    )
                    .join("") +
                "</ul>";
        }
    }

    let growthChart;

    function renderGrowthChart(growth) {
        const canvas = document.getElementById("growth-chart");
        if (!canvas || !window.Chart || !growth) return;
        const avg = growth.last_10_average || {};
        const labels = Object.keys(avg).map((k) => AXIS_LABELS[k] || k);
        const data = Object.keys(avg).map((k) => Number(avg[k]) || 0);
        if (growthChart) growthChart.destroy();
        growthChart = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "直近の平均XP（参考）",
                        data,
                        backgroundColor: "rgba(59, 59, 107, 0.6)",
                    },
                ],
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
            },
        });
    }

    async function downloadExport(path, filename) {
        const res = await fetch(path, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ history: [] }),
        });
        if (!res.ok) throw new Error("export failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    }

    async function initDashboard() {
        const errBox = document.getElementById("dashboard-error");
        try {
            const [dash, growth, practice, skills, weakness] = await Promise.allSettled([
                fetchJson("/api/gamification/dashboard"),
                fetchJson("/api/gamification/growth"),
                fetchJson("/api/analytics/practice-stats"),
                fetchJson("/api/analytics/skill-progress"),
                fetchJson("/api/analytics/weakness"),
            ]);

            const v = (r) => r.status === "fulfilled" ? r.value : null;
            if (v(dash)) {
                renderXpBars(v(dash).skill_xp);
                renderQuests(v(dash).quests);
                renderBadges(v(dash).badges_overview);
            }
            if (v(growth)) renderGrowthChart(v(growth));
            if (v(practice) || v(skills) || v(weakness)) renderAnalytics(v(practice), v(skills), v(weakness));

            document.getElementById("btn-export-csv")?.addEventListener("click", () =>
                downloadExport("/api/export/csv", "conversations.csv", "text/csv").catch((e) =>
                    alert(e.message)
                )
            );
            document.getElementById("btn-export-json")?.addEventListener("click", () =>
                downloadExport("/api/export/json", "conversations.json", "application/json").catch((e) =>
                    alert(e.message)
                )
            );
        } catch (e) {
            console.error(e);
            if (errBox) {
                errBox.style.display = "block";
                errBox.textContent = "ダッシュボードの読み込みに失敗しました: " + e.message;
            }
        }
    }

    document.addEventListener("DOMContentLoaded", initDashboard);
})();
