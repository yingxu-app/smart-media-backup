const test = require("node:test");
const assert = require("node:assert/strict");
const { FirebaseSyncClient } = require("../src/services/firebase-sync.cjs");

test("Firebase accounts only read under their own UID and keep refresh tokens in secure storage", async () => {
  const storageA = new Map();
  const storageB = new Map();
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (String(url).includes("accounts:signInWithPassword")) {
      const payload = JSON.parse(options.body);
      const id = payload.email.startsWith("a-") ? "uid-a" : "uid-b";
      return { ok: true, async json() { return { localId: id, idToken: `id-${id}`, refreshToken: `refresh-${id}`, expiresIn: "3600" }; } };
    }
    return { ok: true, async json() { return { history: {} }; } };
  };
  const clientA = new FirebaseSyncClient({ apiKey: "public-key", databaseUrl: "https://yingxu.firebaseio.com",
    secureStore: { async set(key, value) { storageA.set(key, value); }, async get(key) { return storageA.get(key) || null; }, async remove(key) { storageA.delete(key); } },
    deviceId: "device-a", fetchImpl });
  const clientB = new FirebaseSyncClient({ apiKey: "public-key", databaseUrl: "https://yingxu.firebaseio.com",
    secureStore: { async set(key, value) { storageB.set(key, value); }, async get(key) { return storageB.get(key) || null; }, async remove(key) { storageB.delete(key); } },
    deviceId: "device-b", fetchImpl });
  await clientA.signIn("a-photo@example.com", "user-password");
  await clientB.signIn("b-photo@example.com", "another-password");
  await clientA.get("history");
  await clientB.get("history");
  const readUrls = calls.filter((call) => call.options.method !== "POST").map((call) => call.url);
  assert.ok(readUrls.some((url) => url.includes("/users/uid-a/history.json")));
  assert.ok(readUrls.some((url) => url.includes("/users/uid-b/history.json")));
  assert.ok(!JSON.stringify([...storageA.values(), ...storageB.values()]).includes("user-password"));
  assert.ok(JSON.stringify([...storageA.values(), ...storageB.values()]).includes("refresh-uid-a"));
});

test("Firebase database paths reject traversal and invalid key characters", async () => {
  const client = new FirebaseSyncClient({ apiKey: "key", databaseUrl: "https://yingxu.firebaseio.com",
    secureStore: { async get() { return null; } }, deviceId: "device" });
  client.uid = "uid-a";
  await assert.rejects(client.get("../../uid-b/history"), /无效字段/);
  await assert.rejects(client.get("history/record.with.dots"), /无效字段/);
});
