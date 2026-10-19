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
    let selectedMount = "";
    try {
        const cached = JSON.parse(localStorage.getItem("yingxu-workspace-v1") || "null");
        selectedMount = cached && (cached.selectedSourceMount || cached.detectedMount) || "";
    } catch (_) {}
    if (!selectedMount) {
        dot.classList.remove("active");
        text.classList.remove("active");
        text.textContent = "未就绪";
        return;
    }
    // 导航页只确认原卡是否仍挂载，绝不重新读取 EXIF 或生成预览。
    // 完整扫描只由工作台首次进入、刷新来源或用户切换来源时触发。
    fetch("/api/volumes").then(r => r.json()).then(volumes => {
        const ready = Array.isArray(volumes) && volumes.some(v => v.mount_point === selectedMount);
        dot.classList.toggle("active", ready);
        text.classList.toggle("active", ready);
        text.textContent = ready ? "就绪" : "未就绪";
    }).catch(() => { dot.classList.remove("active"); text.classList.remove("active"); text.textContent = "未就绪"; });
}
refreshSidebarReadiness();
setInterval(refreshSidebarReadiness, 5000);

function accountInitials(name, email) {
    const value = String(name || email || "").trim();
    if (!value) return "影";
    const parts = value.split(/[\s._-]+/).filter(Boolean);
    const latin = parts.filter(part => /^[A-Za-z0-9]/.test(part));
    if (latin.length) return latin.slice(0, 2).map(part => part[0]).join("").toUpperCase();
    return Array.from(value)[0];
}

function refreshFirebaseAccountBadge(account) {
    const badge = document.getElementById("accountBadge");
    if (!badge) return;
    const signedIn = account ? Boolean(account.signed_in) : false;
    if (!signedIn) {
        badge.hidden = true;
        badge.textContent = "";
        return;
    }
    const name = account.display_name || account.email || "影序用户";
    badge.textContent = accountInitials(account.display_name, account.email);
    badge.title = `${name} · 已登录影序同步账号`;
    badge.setAttribute("aria-label", `已登录账号：${name}`);
    badge.hidden = false;
}

function loadFirebaseAccountBadge() {
    fetch("/api/firebase/settings").then(response => response.json()).then(refreshFirebaseAccountBadge)
        .catch(() => refreshFirebaseAccountBadge({signed_in: false}));
}
loadFirebaseAccountBadge();
