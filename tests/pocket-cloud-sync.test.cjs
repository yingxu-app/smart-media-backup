const test = require("node:test");
const assert = require("node:assert/strict");
const { FirebaseCloudClient } = require("../site/pocket/cloud-sync.js");

class MemoryStore {
  constructor({ failWrites = false } = {}) { this.values = new Map(); this.failWrites = failWrites; }
  async get(key) { return this.values.get(key) ?? null; }
  async set(key, value) {
    if (this.failWrites) throw new Error("storage unavailable");
    this.values.set(key, value);
  }
  async remove(key) { this.values.delete(key); }
}

function jsonResponse(payload, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload };
}

const authResponse = uid => ({ localId: uid, email: `${uid}@example.test`, displayName: "Test User", refreshToken: `refresh-${uid}`, idToken: `token-${uid}`, expiresIn: "3600" });

test("login never persists the password and stores only the refresh session", async () => {
  const store = new MemoryStore();
  let authBody;
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async (_url, options) => { authBody = JSON.parse(options.body); return jsonResponse(authResponse("user-a")); },
  });

  const profile = await client.login("user-a@example.test", "do-not-store-this");
  assert.equal(profile.uid, "user-a");
  assert.equal(authBody.password, "do-not-store-this");
  assert.deepEqual(store.values.get("session"), {
    uid: "user-a", email: "user-a@example.test", displayName: "Test User", refreshToken: "refresh-user-a",
  });
  assert.equal(JSON.stringify([...store.values]).includes("do-not-store-this"), false);
});

test("registration requires a username and maps Firebase auth errors", async () => {
  const store = new MemoryStore();
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async () => jsonResponse({ error: { message: "EMAIL_EXISTS : already used" } }, 400),
  });

  await assert.rejects(client.register("user@example.test", "12345678", ""), /注册时请填写用户名/);
  await assert.rejects(client.register("user@example.test", "12345678", "User"), /这个邮箱已注册/);
  assert.equal(store.values.has("session"), false);
});

test("registration writes the username through Firebase profile update", async () => {
  const store = new MemoryStore();
  const calls = [];
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async (url, options) => {
      const body = JSON.parse(options.body);
      calls.push({ url: String(url), body });
      if (String(url).includes("accounts:signUp")) return jsonResponse(authResponse("user-a"));
      return jsonResponse({ displayName: "影序用户", idToken: "updated-token", refreshToken: "updated-refresh", expiresIn: "3600" });
    },
  });

  const profile = await client.register("user-a@example.test", "temporary-password", "影序用户");
  assert.equal(calls.length, 2);
  assert.equal(calls[0].body.displayName, undefined);
  assert.equal(calls[1].url.includes("accounts:update"), true);
  assert.equal(calls[1].body.displayName, "影序用户");
  assert.equal(profile.displayName, "影序用户");
  assert.equal(store.values.get("session").refreshToken, "updated-refresh");
  assert.equal(JSON.stringify([...store.values]).includes("temporary-password"), false);
});

test("history reads and caches only the authenticated UID subtree", async () => {
  const store = new MemoryStore();
  const urls = [];
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async (url, options = {}) => {
      urls.push(String(url));
      if (String(url).includes("identitytoolkit")) return jsonResponse(authResponse("user-a"));
      return jsonResponse({ one: { id: "one", startedAt: "2026-10-19T08:00:00Z" } });
    },
  });

  await client.login("user-a@example.test", "password");
  const records = await client.history();
  assert.equal(records.length, 1);
  assert.match(urls.at(-1), /\/users\/user-a\/history\.json\?auth=token-user-a$/);
  assert.deepEqual(await client.cachedHistory("user-a"), records);
  assert.equal(await client.cachedHistory("user-b"), null);
});

test("offline session restoration keeps cached account data available", async () => {
  const store = new MemoryStore();
  await store.set("session", { uid: "user-a", email: "user-a@example.test", displayName: "A User", refreshToken: "refresh-a" });
  await store.set("history:user-a", [{ id: "cached" }]);
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async () => { throw new Error("offline"); },
  });

  const restored = await client.restoreSession();
  assert.equal(restored.signedIn, true);
  assert.equal(restored.online, false);
  assert.equal(restored.profile.uid, "user-a");
  assert.deepEqual(await client.cachedHistory(), [{ id: "cached" }]);
});

test("a browser storage failure leaves login online but reports no persistence", async () => {
  const store = new MemoryStore({ failWrites: true });
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async () => jsonResponse(authResponse("user-a")),
  });

  const profile = await client.login("user-a@example.test", "password");
  assert.equal(profile.uid, "user-a");
  assert.equal(profile.sessionPersisted, false);
  assert.equal(await client.token(), "token-user-a");
});

test("sign out clears the active account's token and local history cache", async () => {
  const store = new MemoryStore();
  const client = new FirebaseCloudClient({
    apiKey: "public-test-key", databaseUrl: "https://example.test", store,
    fetchImpl: async () => jsonResponse(authResponse("user-a")),
  });
  await client.login("user-a@example.test", "password");
  await store.set("history:user-a", [{ id: "one" }]);
  await store.set("history:user-b", [{ id: "other-account" }]);
  await client.signOut();

  assert.equal(await store.get("session"), null);
  assert.equal(await store.get("history:user-a"), null);
  assert.deepEqual(await store.get("history:user-b"), [{ id: "other-account" }]);
  assert.equal(client.uid, "");
});
