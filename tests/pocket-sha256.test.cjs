const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const { Sha256 } = require("../smb/static/pocket/sha256.js");

test("incremental SHA-256 matches Node across padding and chunk boundaries", () => {
  for (const length of [0, 1, 55, 56, 63, 64, 65, 4096, 1024 * 1024 + 3]) {
    const bytes = crypto.randomBytes(length);
    const digest = new Sha256();
    for (let offset = 0; offset < bytes.length; offset += 37) {
      digest.update(bytes.subarray(offset, offset + 37));
    }
    assert.equal(digest.digest(), crypto.createHash("sha256").update(bytes).digest("hex"), `${length} bytes`);
  }
});

test("incremental SHA-256 rejects updates after finalization", () => {
  const digest = new Sha256();
  digest.update(new Uint8Array([1, 2, 3]));
  digest.digest();
  assert.throws(() => digest.update(new Uint8Array([4])), /已完成/);
});
