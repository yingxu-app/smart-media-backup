/* Smart Media Backup — 全局 JS */
console.log("🖼 Smart Media Backup v1.0 loaded");

// === 主题切换 ===
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    html.setAttribute("data-theme", next);
    localStorage.setItem("smb-theme", next);
    document.querySelector(".theme-toggle").textContent = next === "dark" ? "🌙" : "☀️";
}
(function() {
    const saved = localStorage.getItem("smb-theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    document.querySelector(".theme-toggle").textContent = saved === "dark" ? "🌙" : "☀️";
})();

function refreshSidebarReadiness() {
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    if (!dot || !text) return;
    fetch("/api/scan").then(r => r.json()).then(data => {
        const ready = Boolean(data && !data.error && data.mount_point);
        dot.classList.toggle("active", ready);
        text.classList.toggle("active", ready);
        text.textContent = ready ? "就绪" : "未就绪";
    }).catch(() => { dot.classList.remove("active"); text.classList.remove("active"); text.textContent = "未就绪"; });
}
refreshSidebarReadiness();
setInterval(refreshSidebarReadiness, 5000);
