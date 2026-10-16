const test = require("node:test");
const assert = require("node:assert/strict");

class FakeSocket {
  constructor() {
    this.sent = [];
    this.handlers = {};
    this.closed = false;
  }
  onConnect(callback) { this.handlers.connect = callback; }
  onMessage(callback) { this.handlers.message = callback; }
  onError(callback) { this.handlers.error = callback; }
  onClose(callback) { this.handlers.close = callback; }
  connect(options) {
    this.options = options;
    setImmediate(() => this.handlers.connect());
  }
  send(options) { this.sent.push(options.data); }
  close() {
    this.closed = true;
    if (this.handlers.close) this.handlers.close();
  }
  respond(payload) {
    const line = `${encodeURIComponent(JSON.stringify(payload))}\n`;
    const bytes = Uint8Array.from(Array.from(line, (char) => char.charCodeAt(0)));
    this.handlers.message({ message: bytes.buffer });
  }
}

let activeSocket;
global.wx = {
  createTCPSocket() {
    activeSocket = new FakeSocket();
    return activeSocket;
  }
};
const { PocketTcpClient } = require("../services/pocket-client.js");

test("client connects once and round-trips UTF-8 Pocket notes over one socket", async () => {
  const client = new PocketTcpClient();
  await client.connect("192.168.1.10", 18080);
  assert.deepEqual(activeSocket.options, { address: "192.168.1.10", port: 18080 });

  const resultPromise = client.request("notes.save", {
    token: "session-token",
    data: { event: "星空拍摄", notes: "湖边" }
  });
  const requestLine = new TextDecoder().decode(activeSocket.sent[0]);
  const request = JSON.parse(decodeURIComponent(requestLine.trim()));
  assert.equal(request.command, "notes.save");
  assert.equal(request.data.event, "星空拍摄");
  activeSocket.respond({
    id: request.id,
    ok: true,
    notes: { event: "星空拍摄", notes: "湖边" }
  });
  const result = await resultPromise;
  assert.equal(result.notes.location, undefined);
  assert.equal(result.notes.event, "星空拍摄");
  client.close();
  assert.equal(activeSocket.closed, true);
});

test("client rejects server error responses", async () => {
  const client = new PocketTcpClient();
  await client.connect("192.168.1.10", 18080);
  const resultPromise = client.request("pair", { code: "000000" });
  const requestLine = new TextDecoder().decode(activeSocket.sent[0]);
  const request = JSON.parse(decodeURIComponent(requestLine.trim()));
  activeSocket.respond({ id: request.id, ok: false, error: "配对码无效或已过期" });
  await assert.rejects(resultPromise, /配对码无效或已过期/);
  client.close();
});

test("client closes on oversized response lines, including newline-terminated frames", async () => {
  for (const frame of ["x".repeat(256 * 1024 + 1), `${"x".repeat(256 * 1024 + 1)}\n`]) {
    const client = new PocketTcpClient();
    await client.connect("192.168.1.10", 18080);
    const resultPromise = client.request("status", { token: "session-token" });
    const requestLine = new TextDecoder().decode(activeSocket.sent[0]);
    const request = JSON.parse(decodeURIComponent(requestLine.trim()));
    const pendingResult = assert.rejects(resultPromise, /桌面端返回内容超出限制/);
    const bytes = Uint8Array.from(Array.from(frame, (char) => char.charCodeAt(0)));
    activeSocket.handlers.message({ message: bytes.buffer });
    await pendingResult;
    assert.equal(client.closed, true);
    assert.equal(activeSocket.closed, true);
    assert.equal(request.command, "status");
  }
});

test("client closes when a frame is not valid encoded JSON", async () => {
  const client = new PocketTcpClient();
  await client.connect("192.168.1.10", 18080);
  const resultPromise = client.request("status", { token: "session-token" });
  const pendingResult = assert.rejects(resultPromise, /桌面端响应格式错误/);
  const bytes = Uint8Array.from(Array.from("not-json\n", (char) => char.charCodeAt(0)));
  activeSocket.handlers.message({ message: bytes.buffer });
  await pendingResult;
  assert.equal(client.closed, true);
  assert.equal(activeSocket.closed, true);
});
