const MAX_LINE_CHARS = 256 * 1024;
const REQUEST_TIMEOUT_MS = 15000;

function asciiArrayBuffer(text) {
  const bytes = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i += 1) bytes[i] = text.charCodeAt(i);
  return bytes.buffer;
}

function arrayBufferToAscii(buffer) {
  const bytes = new Uint8Array(buffer);
  let text = "";
  const chunkSize = 8192;
  for (let start = 0; start < bytes.length; start += chunkSize) {
    const end = Math.min(start + chunkSize, bytes.length);
    for (let i = start; i < end; i += 1) text += String.fromCharCode(bytes[i]);
  }
  return text;
}

class PocketTcpClient {
  constructor() {
    this.socket = null;
    this.buffer = "";
    this.nextId = 1;
    this.pending = new Map();
    this.closed = false;
  }

  connect(address, port) {
    if (this.socket) return Promise.reject(new Error("连接已创建"));
    if (typeof wx.createTCPSocket !== "function") {
      return Promise.reject(new Error("当前微信基础库不支持 TCP，请升级微信"));
    }
    return new Promise((resolve, reject) => {
      const socket = wx.createTCPSocket();
      this.socket = socket;
      let settled = false;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        reject(new Error("连接超时；请确认手机与电脑在同一 Wi‑Fi"));
        this.close();
      }, 10000);

      socket.onConnect(() => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve();
      });
      socket.onMessage((event) => this._receive(event && event.message));
      socket.onError((event) => {
        const message = (event && (event.errMsg || event.message)) || "TCP 连接失败";
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(new Error(message));
        }
        this._failPending(new Error(message));
      });
      socket.onClose(() => {
        this.closed = true;
        this._failPending(new Error("桌面端连接已断开"));
      });
      socket.connect({ address, port });
    });
  }

  request(command, fields = {}) {
    if (!this.socket || this.closed) return Promise.reject(new Error("尚未连接桌面端"));
    const id = String(this.nextId++);
    const payload = encodeURIComponent(JSON.stringify({ id, command, ...fields })) + "\n";
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error("桌面端响应超时"));
      }, REQUEST_TIMEOUT_MS);
      this.pending.set(id, { resolve, reject, timer });
      try {
        this.socket.send({ data: asciiArrayBuffer(payload) });
      } catch (error) {
        clearTimeout(timer);
        this.pending.delete(id);
        reject(error);
      }
    });
  }

  _receive(message) {
    if (!(message instanceof ArrayBuffer)) return;
    this.buffer += arrayBufferToAscii(message);
    let newline = this.buffer.indexOf("\n");
    while (newline >= 0) {
      if (newline > MAX_LINE_CHARS) {
        this._protocolError("桌面端返回内容超出限制");
        return;
      }
      const line = this.buffer.slice(0, newline);
      this.buffer = this.buffer.slice(newline + 1);
      if (line.length > 0) this._handleLine(line);
      if (this.closed) return;
      newline = this.buffer.indexOf("\n");
    }
    if (this.buffer.length > MAX_LINE_CHARS) {
      this._protocolError("桌面端返回内容超出限制");
    }
  }

  _handleLine(line) {
    let response;
    try {
      response = JSON.parse(decodeURIComponent(line));
    } catch (_) {
      this._protocolError("桌面端响应格式错误");
      return;
    }
    if (!response || typeof response !== "object" || Array.isArray(response)) {
      this._protocolError("桌面端响应格式错误");
      return;
    }
    const id = String(response.id);
    const pending = this.pending.get(id);
    if (!pending) return;
    clearTimeout(pending.timer);
    this.pending.delete(id);
    if (response.ok) pending.resolve(response);
    else pending.reject(new Error(response.error || "请求失败"));
  }

  _failPending(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  _protocolError(message) {
    this._failPending(new Error(message));
    this.close();
  }

  close() {
    const socket = this.socket;
    this.socket = null;
    this.closed = true;
    if (socket) {
      try { socket.close(); } catch (_) { /* already closed */ }
    }
  }
}

module.exports = { PocketTcpClient };
