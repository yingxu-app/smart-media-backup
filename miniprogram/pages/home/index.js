const { PocketTcpClient } = require("../../services/pocket-client");

const PORT = 18080;
const STATUS_LABELS = {
  idle: "空闲",
  scanning: "正在扫描",
  metadata: "读取素材信息",
  copying: "正在备份",
  reviewing: "正在审片",
  previewing: "正在预览",
  verifying: "正在校验",
  done: "备份完成",
  error: "任务遇到问题"
};

Page({
  data: {
    address: "",
    port: PORT,
    code: "",
    connecting: false,
    connected: false,
    error: "",
    statusText: "空闲",
    source: "",
    progress: {},
    progressPercent: 0,
    history: [],
    notes: { event: "", location: "", device: "", notes: "" },
    savingNotes: false,
    savedMessage: ""
  },

  onLoad() {
    this.client = null;
    this.token = "";
    this.pollTimer = null;
    const savedAddress = wx.getStorageSync("yingxuPocketAddress");
    if (savedAddress) this.setData({ address: savedAddress });
  },

  onAddressInput(event) { this.setData({ address: event.detail.value.trim() }); },
  onCodeInput(event) { this.setData({ code: event.detail.value.replace(/\D/g, "").slice(0, 6) }); },

  isPrivateIPv4(address) {
    const parts = address.split(".");
    if (parts.length !== 4 || parts.some((part) => !/^\d{1,3}$/.test(part))) return false;
    const octets = parts.map(Number);
    if (octets.some((part) => part < 0 || part > 255)) return false;
    const [first, second] = octets;
    return first === 10 || (first === 192 && second === 168) ||
      (first === 172 && second >= 16 && second <= 31);
  },

  async connect() {
    const address = this.data.address.trim();
    const port = PORT;
    const code = this.data.code.trim();
    if (!this.isPrivateIPv4(address) || !/^\d{6}$/.test(code)) {
      this.setData({ error: "请输入电脑的私有局域网 IPv4 地址和 6 位配对码" });
      return;
    }
    this.setData({ connecting: true, error: "" });
    const client = new PocketTcpClient();
    this.client = client;
    try {
      await client.connect(address, port);
      const paired = await client.request("pair", { code });
      this.token = paired.token;
      wx.setStorageSync("yingxuPocketAddress", address);
      this.setData({ connected: true, connecting: false, code: "", error: "" });
      await this.refreshAll();
      if (!this.client || !this.token || !this.data.connected) return;
      this.pollTimer = setInterval(() => this.refreshAll(), 15000);
    } catch (error) {
      client.close();
      if (this.client === client) this.client = null;
      this.setData({ connecting: false, connected: false, error: error.message || "连接失败" });
    }
  },

  async refreshAll() {
    if (!this.client || !this.token) return;
    try {
      const fields = { token: this.token };
      const [status, history, notes] = await Promise.all([
        this.client.request("status", fields),
        this.client.request("history", { ...fields, limit: 20 }),
        this.client.request("notes.get", fields)
      ]);
      const data = status.data || {};
      const progress = data.progress || {};
      const percent = Number(progress.phase_progress || 0);
      this.setData({
        statusText: STATUS_LABELS[data.status] || data.status || "未知状态",
        source: data.source || "",
        progress,
        progressPercent: Math.max(0, Math.min(100, percent)),
        history: history.items || [],
        notes: notes.notes || this.data.notes,
        error: ""
      });
    } catch (error) {
      this.resetConnection(`${error.message || "读取桌面状态失败"}；请重新连接`);
    }
  },

  resetConnection(error = "") {
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = null;
    if (this.client) this.client.close();
    this.client = null;
    this.token = "";
    this.setData({
      connected: false,
      connecting: false,
      error,
      history: [],
      source: "",
      progress: {},
      progressPercent: 0
    });
  },

  onNoteInput(event) {
    const key = event.currentTarget.dataset.key;
    this.setData({ [`notes.${key}`]: event.detail.value, savedMessage: "" });
  },

  async saveNotes() {
    if (!this.client || !this.token) return;
    this.setData({ savingNotes: true, savedMessage: "" });
    try {
      const result = await this.client.request("notes.save", {
        token: this.token,
        data: this.data.notes
      });
      this.setData({ notes: result.notes, savedMessage: "已保存到电脑" });
    } catch (error) {
      this.setData({ error: error.message || "保存失败" });
    } finally {
      this.setData({ savingNotes: false });
    }
  },

  async disconnect() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = null;
    if (this.client && this.token) {
      try { await this.client.request("disconnect", { token: this.token }); } catch (_) { /* socket may already be gone */ }
    }
    if (this.client) this.client.close();
    this.client = null;
    this.token = "";
    this.setData({ connected: false, connecting: false, error: "", history: [] });
  },

  onUnload() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    if (this.client) this.client.close();
    this.client = null;
    this.token = "";
  }
});
