(() => {
  "use strict";

  const config = window.YINGXU_FIREBASE_CONFIG || {};
  const store = new YingxuCloudSync.IndexedDbStore();
  const client = new YingxuCloudSync.FirebaseCloudClient({ ...config, store });
  const byId = id => document.getElementById(id);
  let stopLiveWatch = () => {};
  let currentUid = "";
  let handoffTimer = 0;
  let selectedPhoneFiles = [];
  let handoffWindow = null;
  let handoffOrigin = "";
  const MAX_PHONE_FILES = 1000;

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
  function supportedMedia(file) {
    const extension = (String(file.name).match(/\.[^.]+$/) || [""])[0].toLowerCase();
    const video = file.type.startsWith("video/") || [".mp4", ".mov", ".m4v", ".avi", ".mxf", ".braw", ".mpg", ".mts", ".m2ts", ".insv", ".webm", ".mkv", ".wmv", ".flv", ".3gp"].includes(extension);
    const photo = file.type.startsWith("image/") || [".arw", ".cr2", ".cr3", ".nef", ".nrw", ".dng", ".orf", ".rw2", ".raf", ".srw", ".x3f", ".3fr", ".fff", ".mef", ".mos", ".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp", ".bmp", ".gif"].includes(extension);
    return video ? "video" : photo ? "photo" : "";
  }

  function readSelectedFiles() {
    const inputs = [byId("phoneMediaFiles"), byId("phoneFolderFiles")];
    const unique = new Set();
    return inputs.flatMap(input => Array.from(input.files || []).map(file => ({
      file,
      relativePath: file.webkitRelativePath || file.name,
      kind: supportedMedia(file),
    }))).filter(item => {
      const key = `${item.relativePath}|${item.file.size}|${item.file.lastModified}`;
      if (!item.kind || unique.has(key)) return false;
      unique.add(key);
      return true;
    });
  }

  function renderSelectedFiles() {
    const root = byId("phoneSelectedFiles");
    root.replaceChildren();
    if (!selectedPhoneFiles.length) {
      root.className = "file-list empty";
      root.textContent = "尚未选择照片或视频";
      return;
    }
    root.className = "file-list";
    const total = selectedPhoneFiles.reduce((sum, item) => sum + item.file.size, 0);
    for (const item of selectedPhoneFiles.slice(0, 24)) {
      const row = element("div", "file-row");
      row.append(element("span", "file-name", item.relativePath));
      row.append(element("span", "file-size", item.file.size < 1024 * 1024
        ? `${Math.max(1, Math.round(item.file.size / 1024))} KB`
        : `${(item.file.size / 1024 / 1024).toFixed(1)} MB`));
      root.append(row);
    }
    if (selectedPhoneFiles.length > 24) root.append(element("p", "muted", `另有 ${selectedPhoneFiles.length - 24} 个文件`));
    root.append(element("p", "muted", `${selectedPhoneFiles.length} 个文件 · ${(total / 1024 / 1024).toFixed(1)} MB`));
  }

  function clearPhoneSelection() {
    byId("phoneMediaFiles").value = "";
    byId("phoneFolderFiles").value = "";
    selectedPhoneFiles = [];
    renderSelectedFiles();
    byId("phoneBackupProgressTrack").classList.add("hidden");
    setMessage("desktopMessage", "已清除手机文件选择。");
  }

  function handleDesktopMessage(event) {
    if (!handoffOrigin || event.origin !== handoffOrigin || event.source !== handoffWindow) return;
    const data = event.data || {};
    if (data.type === "YINGXU_POCKET_READY" && handoffWindow && !handoffWindow.closed) {
      clearInterval(handoffTimer);
      handoffTimer = 0;
      try {
        handoffWindow.postMessage({
          type: "YINGXU_POCKET_FILES",
          eventName: byId("phoneEventName").value.trim() || "手机备份",
          files: selectedPhoneFiles.map(item => ({ file: item.file, relativePath: item.relativePath, kind: item.kind })),
        }, event.origin);
        setMessage("desktopMessage", "已连接电脑协作页，正在扫描并校验所选素材…");
      } catch (_) {
        byId("phoneBackupButton").disabled = false;
        setMessage("desktopMessage", "浏览器没有允许交接文件。请在电脑协作页直接重新选择素材。", true);
      }
    } else if (data.type === "YINGXU_POCKET_ACCEPTED") {
      byId("phoneBackupControls").classList.remove("hidden");
      byId("clearPhoneFilesButton").disabled = true;
      setMessage("desktopMessage", "电脑已接收文件清单，正在执行重复检查和备份。");
    } else if (data.type === "YINGXU_POCKET_PROGRESS") {
      byId("phoneBackupProgressTrack").classList.remove("hidden");
      const percent = Math.max(0, Math.min(100, Number(data.percent) || 0));
      byId("phoneBackupProgressBar").style.width = `${percent}%`;
      byId("pausePhoneBackupButton").textContent = String(data.message || "").includes("已暂停") ? "继续" : "暂停";
      setMessage("desktopMessage", String(data.message || "电脑正在处理手机备份…"), Boolean(data.error));
    } else if (data.type === "YINGXU_POCKET_FINISHED") {
      byId("phoneBackupControls").classList.add("hidden");
      byId("phoneBackupButton").disabled = false;
      byId("clearPhoneFilesButton").disabled = false;
      byId("phoneBackupProgressTrack").classList.remove("hidden");
      byId("phoneBackupProgressBar").style.width = data.status === "completed" ? "100%" : `${Math.max(0, Math.min(100, Number(data.percent) || 0))}%`;
      setMessage("desktopMessage", String(data.message || "电脑备份任务结束。"), data.status !== "completed");
    }
  }

  function sendDesktopCommand(command) {
    if (!handoffWindow || handoffWindow.closed || !handoffOrigin) {
      setMessage("desktopMessage", "电脑协作页未连接。请重新开始备份。", true);
      return;
    }
    handoffWindow.postMessage({ type: "YINGXU_POCKET_COMMAND", command }, handoffOrigin);
  }

  function startPhoneBackup() {
    try {
      const base = new URL(byId("desktopAddress").value.trim());
      if (base.protocol !== "http:" || base.username || base.password || base.hostname === "localhost" || base.hostname === "127.0.0.1") {
        throw new Error("请输入电脑在同一 Wi‑Fi 下显示的局域网 HTTP 地址。");
      }
      base.pathname = "/pocket/";
      base.search = "?handoff=1";
      base.hash = "";
      const hostParts = base.hostname.split(".").map(Number);
      const privateIpv4 = hostParts.length === 4 && hostParts.every(part => Number.isInteger(part) && part >= 0 && part <= 255)
        && (hostParts[0] === 10 || hostParts[0] === 192 && hostParts[1] === 168
          || hostParts[0] === 172 && hostParts[1] >= 16 && hostParts[1] <= 31);
      if (!privateIpv4 && !base.hostname.endsWith(".local")) {
        throw new Error("电脑地址必须是同一局域网的私有 IPv4 地址或 .local 名称。");
      }
      selectedPhoneFiles = readSelectedFiles();
      if (!selectedPhoneFiles.length) throw new Error("请先选择至少一个支持的照片或视频文件。");
      if (selectedPhoneFiles.length > MAX_PHONE_FILES) throw new Error("单次最多选择 1000 个文件，请分批备份。");
      const totalBytes = selectedPhoneFiles.reduce((sum, item) => sum + item.file.size, 0);
      if (totalBytes > 100 * 1024 * 1024 * 1024) throw new Error("单次手机备份最多 100 GB，请分批备份。");
      renderSelectedFiles();
      window.removeEventListener("message", handleDesktopMessage);
      window.addEventListener("message", handleDesktopMessage);
      handoffOrigin = base.origin;
      handoffWindow = window.open(base.href, "yingxuPocketDesktop");
      if (!handoffWindow) throw new Error("浏览器拦截了电脑协作页。请允许此 PWA 打开局域网页面后重试。");
      byId("phoneBackupButton").disabled = true;
      let attempts = 0;
      clearInterval(handoffTimer);
      handoffTimer = window.setInterval(() => {
        if (!handoffWindow || handoffWindow.closed) {
          clearInterval(handoffTimer);
          handoffTimer = 0;
          byId("phoneBackupButton").disabled = false;
          setMessage("desktopMessage", "电脑协作页已关闭。电脑需保持运行并与手机位于同一 Wi‑Fi。", true);
          return;
        }
        if (++attempts > 600) {
          clearInterval(handoffTimer);
          handoffTimer = 0;
          byId("phoneBackupButton").disabled = false;
          setMessage("desktopMessage", "尚未收到电脑页面就绪信号。请在电脑页面完成配对后重试。", true);
          return;
        }
        try { handoffWindow.postMessage({ type: "YINGXU_POCKET_PING" }, base.origin); } catch (_) {}
      }, 500);
      setMessage("desktopMessage", "请在电脑页面完成一次配对；页面就绪后，所选素材会自动交接并开始扫描。电脑需保持运行。");
    } catch (error) { setMessage("desktopMessage", error.message || "地址格式无效。", true); }
  }

  byId("phoneMediaFiles").addEventListener("change", () => { selectedPhoneFiles = readSelectedFiles(); renderSelectedFiles(); });
  byId("phoneFolderFiles").addEventListener("change", () => { selectedPhoneFiles = readSelectedFiles(); renderSelectedFiles(); });
  byId("phoneBackupButton").addEventListener("click", startPhoneBackup);
  byId("clearPhoneFilesButton").addEventListener("click", clearPhoneSelection);
  byId("pausePhoneBackupButton").addEventListener("click", () => sendDesktopCommand("toggle-pause"));
  byId("cancelPhoneBackupButton").addEventListener("click", () => {
    if (window.confirm("取消手机备份？已完成并校验的文件会保留在电脑，未完成文件不会保留。")) sendDesktopCommand("cancel");
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
