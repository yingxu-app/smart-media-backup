(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.YingxuCloudSync = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const AUTH_ERRORS = {
    EMAIL_EXISTS: "这个邮箱已注册，请直接登录。",
    EMAIL_NOT_FOUND: "这个邮箱尚未注册，请先注册。",
    INVALID_EMAIL: "邮箱格式无效。",
    INVALID_PASSWORD: "邮箱或密码不正确。",
    INVALID_LOGIN_CREDENTIALS: "邮箱或密码不正确。",
    USER_DISABLED: "此账号已停用，请联系项目维护者。",
    TOO_MANY_ATTEMPTS_TRY_LATER: "尝试次数过多，请稍后再试。",
    WEAK_PASSWORD: "密码未达到 Firebase 要求，请更换更强的密码。",
    OPERATION_NOT_ALLOWED: "Firebase 项目尚未启用邮箱/密码登录。",
    API_KEY_INVALID: "Firebase 项目配置无效。",
    CONFIGURATION_NOT_FOUND: "Firebase Authentication 尚未完成项目配置。",
  };

  function userError(message, status = 0) {
    const code = String(message || "").split(":", 1)[0].trim();
    if (AUTH_ERRORS[code]) return AUTH_ERRORS[code];
    const diagnosticCode = /^[A-Z0-9_]{1,60}$/.test(code) ? code : `HTTP_${Number(status) || 0}`;
    return `Firebase 返回错误代码 ${diagnosticCode}（HTTP ${Number(status) || 0}）。请将错误代码提供给支持人员；不要发送密码。`;
  }

  class IndexedDbStore {
    constructor({ indexedDBImpl = globalThis.indexedDB, databaseName = "yingxu-pocket-cloud-v1" } = {}) {
      this.indexedDB = indexedDBImpl;
      this.databaseName = databaseName;
      this.databasePromise = null;
    }

    _database() {
      if (!this.indexedDB) return Promise.reject(new Error("当前浏览器不支持本地安全存储。"));
      if (!this.databasePromise) {
        this.databasePromise = new Promise((resolve, reject) => {
          const request = this.indexedDB.open(this.databaseName, 1);
          request.onupgradeneeded = () => {
            if (!request.result.objectStoreNames.contains("records")) request.result.createObjectStore("records");
          };
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => reject(new Error("无法打开浏览器本地存储。"));
        });
      }
      return this.databasePromise;
    }

    async get(key) {
      const database = await this._database();
      return new Promise((resolve, reject) => {
        const request = database.transaction("records", "readonly").objectStore("records").get(key);
        request.onsuccess = () => resolve(request.result ?? null);
        request.onerror = () => reject(new Error("无法读取浏览器本地存储。"));
      });
    }

    async set(key, value) {
      const database = await this._database();
      return new Promise((resolve, reject) => {
        const transaction = database.transaction("records", "readwrite");
        transaction.objectStore("records").put(value, key);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(new Error("无法保存浏览器本地数据。"));
      });
    }

    async remove(key) {
      const database = await this._database();
      return new Promise((resolve, reject) => {
        const transaction = database.transaction("records", "readwrite");
        transaction.objectStore("records").delete(key);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(new Error("无法清除浏览器本地数据。"));
      });
    }
  }

  class FirebaseCloudClient {
    constructor({ apiKey, databaseUrl, store, fetchImpl = fetch, eventSourceFactory = url => new EventSource(url) }) {
      this.apiKey = String(apiKey || "").trim();
      this.databaseUrl = String(databaseUrl || "").replace(/\/+$/, "");
      this.store = store;
      this.fetch = fetchImpl;
      this.eventSourceFactory = eventSourceFactory;
      this.session = null;
      this.uid = "";
      this.sessionPersisted = true;
    }

    get configured() { return Boolean(this.apiKey && this.databaseUrl && this.store); }

    async _json(url, options = {}) {
      let response;
      const { authRequest = false, ...requestOptions } = options;
      try { response = await this.fetch(url, requestOptions); }
      catch (_) { throw new Error("网络连接不可用；可继续查看本机缓存的云端历史。"); }
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = payload?.error?.message || "";
        const error = new Error(authRequest ? userError(message, response.status) : "云端数据读取失败，请检查账号权限或网络。");
        error.code = String(message).split(":", 1)[0].trim();
        throw error;
      }
      return payload;
    }

    async _authenticate(endpoint, email, password, displayName = "") {
      if (!this.configured) throw new Error("Firebase 项目配置不完整。");
      const body = { email: String(email || "").trim(), password: String(password || ""), returnSecureToken: true };
      const username = String(displayName || "").trim().slice(0, 40);
      const data = await this._json(`https://identitytoolkit.googleapis.com/v1/${endpoint}?key=${encodeURIComponent(this.apiKey)}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), authRequest: true,
      });
      let session = {
        uid: String(data.localId || ""),
        email: String(data.email || body.email),
        displayName: String(data.displayName || username || body.email.split("@", 1)[0] || "").trim().slice(0, 40),
        refreshToken: String(data.refreshToken || ""),
        idToken: String(data.idToken || ""),
        expiresAt: Date.now() + Math.max(60, Number(data.expiresIn) || 3600) * 1000,
      };
      if (!session.uid || !session.refreshToken || !session.idToken) throw new Error("Firebase 登录响应不完整，请重试。");
      if ((endpoint === "accounts:signUp" || username) && username) {
        try {
          const updated = await this._json(`https://identitytoolkit.googleapis.com/v1/accounts:update?key=${encodeURIComponent(this.apiKey)}`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idToken: session.idToken, displayName: username, returnSecureToken: true }), authRequest: true,
          });
          session = {
            ...session,
            displayName: String(updated.displayName || username).trim().slice(0, 40),
            idToken: String(updated.idToken || session.idToken),
            refreshToken: String(updated.refreshToken || session.refreshToken),
            expiresAt: Date.now() + Math.max(60, Number(updated.expiresIn) || 3600) * 1000,
          };
        } catch (error) {
          const message = endpoint === "accounts:signUp"
            ? "账号已创建，但用户名暂未同步。请用登录按钮重试，并保留用户名字段。"
            : "账号已登录，但用户名暂未同步；请检查网络后重试。";
          const profileError = new Error(message);
          profileError.cause = error;
          throw profileError;
        }
      }
      this.session = session;
      this.uid = session.uid;
      try {
        await this.store.set("session", { uid: session.uid, email: session.email, displayName: session.displayName, refreshToken: session.refreshToken });
        this.sessionPersisted = true;
      } catch (_) {
        // Keep this online session usable, but let the UI explain it will not survive a browser restart.
        this.sessionPersisted = false;
      }
      return this.profile();
    }

    login(email, password, displayName = "") { return this._authenticate("accounts:signInWithPassword", email, password, displayName); }
    register(email, password, displayName) {
      if (!String(displayName || "").trim()) return Promise.reject(new Error("注册时请填写用户名。"));
      return this._authenticate("accounts:signUp", email, password, displayName);
    }

    profile() {
      if (!this.session) return null;
      return { uid: this.session.uid, email: this.session.email, displayName: this.session.displayName, sessionPersisted: this.sessionPersisted };
    }

    async restoreSession() {
      const saved = await this.store.get("session");
      if (!saved?.uid || !saved?.refreshToken) return { signedIn: false, online: false };
      this.uid = String(saved.uid);
      this.session = { ...saved, idToken: "", expiresAt: 0 };
      this.sessionPersisted = true;
      try {
        await this._refreshToken();
        return { signedIn: true, online: true, profile: this.profile() };
      } catch (error) {
        if (["INVALID_GRANT", "TOKEN_EXPIRED", "USER_DISABLED"].includes(error.code)) {
          await this.signOut();
          return { signedIn: false, online: true, revoked: true };
        }
        return { signedIn: true, online: false, profile: this.profile() };
      }
    }

    async _refreshToken() {
      if (!this.session?.refreshToken) throw new Error("请先登录影序账号。");
      const body = new URLSearchParams({ grant_type: "refresh_token", refresh_token: this.session.refreshToken });
      const data = await this._json(`https://securetoken.googleapis.com/v1/token?key=${encodeURIComponent(this.apiKey)}`, {
        method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body,
      });
      if (!data.id_token) throw new Error("登录已过期，请重新登录影序账号。");
      this.session = {
        ...this.session,
        uid: String(data.user_id || this.session.uid),
        idToken: String(data.id_token),
        refreshToken: String(data.refresh_token || this.session.refreshToken),
        expiresAt: Date.now() + Math.max(60, Number(data.expires_in) || 3600) * 1000,
      };
      this.uid = this.session.uid;
      await this.store.set("session", {
        uid: this.uid, email: this.session.email, displayName: this.session.displayName, refreshToken: this.session.refreshToken,
      });
      return this.session.idToken;
    }

    async token() {
      if (this.session?.idToken && this.session.expiresAt > Date.now() + 60_000) return this.session.idToken;
      return this._refreshToken();
    }

    async _read(path) {
      if (!this.uid || !["history", "live"].includes(path)) throw new Error("云端读取路径无效。");
      const token = await this.token();
      return this._json(`${this.databaseUrl}/users/${encodeURIComponent(this.uid)}/${path}.json?auth=${encodeURIComponent(token)}`);
    }

    async history() {
      const value = await this._read("history");
      const items = Object.values(value || {}).filter(item => item && typeof item === "object");
      items.sort((a, b) => String(b.startedAt || "").localeCompare(String(a.startedAt || "")));
      await this.store.set(`history:${this.uid}`, items.slice(0, 100));
      return items.slice(0, 100);
    }

    cachedHistory(uid = this.uid) { return this.store.get(`history:${uid}`); }
    async live() {
      const value = await this._read("live");
      await this.store.set(`live:${this.uid}`, value || {});
      return value || {};
    }

    cachedLive(uid = this.uid) { return this.store.get(`live:${uid}`); }

    watchLive(onValue, onError = () => {}) {
      if (!this.uid || !this.eventSourceFactory) return () => {};
      let source = null;
      let closed = false;
      const connect = async () => {
        try {
          const token = await this.token();
          if (closed) return;
          const url = `${this.databaseUrl}/users/${encodeURIComponent(this.uid)}/live.json?auth=${encodeURIComponent(token)}`;
          source = this.eventSourceFactory(url);
          ["put", "patch"].forEach(eventName => source.addEventListener(eventName, event => {
            try {
              const message = JSON.parse(event.data || "{}");
              if (eventName === "put" && message.path === "/") {
                const value = message.data || {};
                this.store.set(`live:${this.uid}`, value).catch(() => {});
                onValue(value);
              } else if (eventName === "patch" && message.data && typeof message.data === "object") {
                // Patches are partial; read the scoped snapshot so removals and changed children render correctly.
                this.live().then(onValue).catch(onError);
              }
            } catch (_) { onError(new Error("云端实时数据格式无效。")); }
          }));
          source.onerror = () => onError(new Error("云端实时连接中断，正在尝试恢复。"));
          window.setTimeout(() => {
            if (closed) return;
            source?.close();
            connect();
          }, 45 * 60 * 1000);
        } catch (error) { onError(error); }
      };
      connect();
      return () => { closed = true; source?.close(); };
    }

    async signOut() {
      const uid = this.uid;
      this.session = null;
      this.uid = "";
      this.sessionPersisted = true;
      await this.store.remove("session");
      if (uid) await this.store.remove(`history:${uid}`);
      if (uid) await this.store.remove(`live:${uid}`);
    }
  }

  return { FirebaseCloudClient, IndexedDbStore, userError };
});
