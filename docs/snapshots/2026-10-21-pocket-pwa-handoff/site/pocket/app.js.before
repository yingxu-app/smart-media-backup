(() => {
  "use strict";

  const config = window.YINGXU_FIREBASE_CONFIG || {};
  const store = new YingxuCloudSync.IndexedDbStore();
  const client = new YingxuCloudSync.FirebaseCloudClient({ ...config, store });
  const byId = id => document.getElementById(id);
  let stopLiveWatch = () => {};
  let currentUid = "";

  function setMessage(id, message, isError = false) {
    const element = byId(id);
    element.textContent = message || "";
    element.classList.toggle("error", Boolean(isError));
  }

  function firstInitial(profile) {
    const name = String(profile?.displayName || profile?.email || "?").trim();
    return Array.from(name)[0]?.toLocaleUpperCase("zh-CN") || "?";
  }

  function showAccount(profile, { online = true } = {}) {
    if (!profile?.uid) return;
    currentUid = profile.uid;
    byId("authCard").classList.add("hidden");
    byId("accountView").classList.remove("hidden");
    byId("avatar").textContent = firstInitial(profile);
    byId("displayNameLabel").textContent = profile.displayName || "影序账号";
    byId("emailLabel").textContent = profile.email || "";
    byId("syncState").textContent = online ? "已连接" : "离线缓存";
    byId("syncMessage").textContent = profile.sessionPersisted === false
      ? "当前浏览器未能保存登录状态；关闭页面后需要重新登录。"
      : online ? "进度和历史按账号隔离同步；原始媒体与电脑路径留在本地。"
        : "当前离线，显示最近一次缓存；联网后可刷新云端记录。";
  }

  function formatTime(value) {
    if (value === null || value === undefined || value === "") return "时间未知";
    let date;
    if (typeof value === "number") date = new Date(value < 1e12 ? value * 1000 : value);
    else date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    }).format(date);
  }

  function formatBytes(value) {
    const bytes = Math.max(0, Number(value) || 0);
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let size = bytes / 1024;
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
    return `${size.toFixed(size >= 100 ? 0 : 1)} ${units[unit]}`;
  }

  function statusLabel(value) {
    return ({ running: "进行中", scanning: "扫描中", completed: "已完成", partial: "部分完成", cancelled: "已取消", failed: "失败", idle: "空闲" })[value] || value || "状态未知";
  }

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = String(value);
    return node;
  }

  function renderLive(items) {
    const root = byId("liveList");
    root.replaceChildren();
    const entries = Object.values(items || {}).filter(item => item && typeof item === "object");
    if (!entries.length) {
      root.className = "empty";
      root.textContent = "目前没有其他设备正在备份。电脑离线或任务结束时，这里不会显示进行中状态。";
      return;
    }
    root.className = "";
    entries.sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0));
    for (const item of entries) {
      const row = element("article", "live-item");
      const title = element("div", "live-title");
      title.append(element("span", "", item.eventName || item.targetName || "备份任务"));
      title.append(element("span", "", statusLabel(item.status)));
      row.append(title);
      const total = Math.max(0, Number(item.totalFiles) || 0);
      const done = Math.max(0, Number(item.processedFiles) || 0);
      const progress = element("div", "progress-track");
      const bar = element("div", "progress-bar");
      bar.style.width = `${total ? Math.min(100, done / total * 100) : 0}%`;
      progress.append(bar);
      row.append(progress);
      const meta = element("div", "meta");
      for (const label of [item.deviceName || "设备", `${done}/${total} 个文件`, formatBytes(item.totalBytes), formatTime(item.updatedAt)]) {
        meta.append(element("span", "pill", label));
      }
      row.append(meta);
      if (item.currentFile) row.append(element("div", "muted", `当前文件：${item.currentFile}`));
      root.append(row);
    }
  }

  function renderHistory(items) {
    const root = byId("historyList");
    root.replaceChildren();
    const entries = Array.isArray(items) ? items : [];
    byId("historyCount").textContent = entries.length ? `${entries.length} 条` : "";
    if (!entries.length) {
      root.className = "empty";
      root.textContent = "还没有云端归档记录。电脑完成备份并成功同步后，记录会显示在这里。";
      return;
    }
    root.className = "";
    for (const item of entries) {
      const row = element("article", "history-item");
      const title = element("div", "history-title");
      title.append(element("span", "", item.eventName || item.targetName || "备份记录"));
      title.append(element("span", "", statusLabel(item.status)));
      row.append(title);
      const meta = element("div", "meta");
      for (const label of [formatTime(item.startedAt || item.updatedAt), item.deviceName || "设备未知", `${Number(item.totalFiles) || 0} 个文件`, formatBytes(item.totalBytes), item.targetName || "目标未记录"]) {
        meta.append(element("span", "pill", label));
      }
      row.append(meta);
      if (item.notes) row.append(element("p", "muted", item.notes));
      root.append(row);
    }
  }

  async function loadHistory() {
    const cached = await client.cachedHistory(currentUid).catch(() => null);
    if (cached) renderHistory(cached);
    if (!navigator.onLine) {
      byId("syncState").textContent = "离线缓存";
      return;
    }
    try {
      renderHistory(await client.history());
      byId("syncState").textContent = "已连接";
      if (client.sessionPersisted) setMessage("syncMessage", "云端归档已刷新；原始媒体与电脑路径不会上传。");
    } catch (error) {
      byId("syncState").textContent = "同步中断";
      const latest = await client.cachedHistory(currentUid).catch(() => null);
      if (latest) renderHistory(latest);
      setMessage("syncMessage", `${error.message} ${latest ? "正在显示本机缓存。" : ""}`, true);
    }
  }

  async function loadLive() {
    try {
      renderLive(await client.live());
    } catch (error) {
      renderLive(await client.cachedLive(currentUid).catch(() => null));
      if (navigator.onLine) setMessage("syncMessage", error.message, true);
    }
  }

  async function enterAccount(profile, online = true) {
    showAccount(profile, { online });
    renderHistory(await client.cachedHistory(profile.uid).catch(() => null));
    renderLive(await client.cachedLive(profile.uid).catch(() => null));
    await Promise.all([loadHistory(), loadLive()]);
    stopLiveWatch();
    stopLiveWatch = client.watchLive(items => {
      renderLive(items);
      byId("syncState").textContent = "实时同步";
    }, error => {
      byId("syncState").textContent = navigator.onLine ? "同步中断" : "离线缓存";
      if (navigator.onLine) setMessage("syncMessage", error.message, true);
    });
  }

  async function authenticate(action) {
    const button = action === "login" ? byId("loginButton") : byId("registerButton");
    button.disabled = true;
    setMessage("authMessage", "正在连接 Firebase…");
    try {
      const profile = action === "login"
        ? await client.login(byId("email").value, byId("password").value, byId("displayName").value)
        : await client.register(byId("email").value, byId("password").value, byId("displayName").value);
      byId("password").value = "";
      setMessage("authMessage", "");
      await enterAccount(profile, true);
    } catch (error) {
      // Keep the user's password field intact on failure so they can inspect or retry locally.
      setMessage("authMessage", error.message || "登录失败，请稍后重试。", true);
    } finally { button.disabled = false; }
  }

  byId("loginButton").addEventListener("click", () => authenticate("login"));
  byId("registerButton").addEventListener("click", () => authenticate("register"));
  byId("password").addEventListener("keydown", event => { if (event.key === "Enter") authenticate("login"); });
  byId("refreshButton").addEventListener("click", loadHistory);
  byId("refreshLiveButton").addEventListener("click", loadLive);
  byId("logoutButton").addEventListener("click", async () => {
    stopLiveWatch();
    await client.signOut().catch(() => {});
    currentUid = "";
    byId("accountView").classList.add("hidden");
    byId("authCard").classList.remove("hidden");
    setMessage("authMessage", "已退出账号，并清除本机云端缓存。");
  });
  byId("openDesktopButton").addEventListener("click", () => {
    try {
      const base = new URL(byId("desktopAddress").value.trim());
      if (base.protocol !== "http:" || base.username || base.password || base.hostname === "localhost" || base.hostname === "127.0.0.1") {
        throw new Error("请输入电脑在同一 Wi‑Fi 下显示的局域网 HTTP 地址。");
      }
      base.pathname = "/pocket/";
      base.search = "";
      base.hash = "";
      window.open(base.href, "_blank", "noopener,noreferrer");
      setMessage("desktopMessage", "已打开电脑的局域网协作页。此页需要电脑运行，云端历史仍可独立查看。");
    } catch (error) { setMessage("desktopMessage", error.message || "地址格式无效。", true); }
  });

  function updateOfflineStatus() {
    byId("offlineStatus").textContent = navigator.onLine
      ? "网络可用。若 Firebase 暂时不可达，可查看本机缓存的归档记录。"
      : "当前离线。已登录的本机账号和缓存记录仍可打开；实时进度会在恢复联网后刷新。";
    if (!navigator.onLine && currentUid) byId("syncState").textContent = "离线缓存";
  }
  window.addEventListener("online", () => { updateOfflineStatus(); if (currentUid) { loadHistory(); loadLive(); } });
  window.addEventListener("offline", updateOfflineStatus);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && currentUid && navigator.onLine) { loadHistory(); loadLive(); }
  });

  updateOfflineStatus();
  if (!client.configured) setMessage("authMessage", "Firebase 配置不完整，请联系影序维护者。", true);
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("./sw.js", { scope: "./" })
      .then(() => navigator.serviceWorker.ready)
      .then(() => { byId("offlineStatus").textContent = "离线页面缓存已启用；首次打开需联网加载完整页面。"; })
      .catch(() => { byId("offlineStatus").textContent = "离线页面缓存未能启用；请保持网络后重试。"; });
  } else {
    byId("offlineStatus").textContent = "请通过 HTTPS 官网打开以启用安装和离线页面缓存；局域网 HTTP 页面不支持 Service Worker。";
  }

  client.restoreSession().then(async result => {
    if (result.signedIn && result.profile) await enterAccount(result.profile, result.online);
    else if (result.revoked) setMessage("authMessage", "登录状态已失效，请重新登录。");
  }).catch(error => setMessage("authMessage", error.message || "无法恢复本机登录状态。", true));
})();
