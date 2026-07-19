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
