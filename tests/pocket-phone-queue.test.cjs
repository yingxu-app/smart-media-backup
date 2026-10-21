const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createPhoneQueue, restorePhoneQueue } = require("../site/pocket/phone-queue.js");

function fakeFile(name, size, lastModified = 123) {
  return { name, size, lastModified, slice() {} };
}

test("phone queue stores the selected File references with resume metadata", () => {
  const file = fakeFile("IMG_1001.JPG", 2048, 456);
  const queue = createPhoneQueue([
    { file, relativePath: "DCIM/IMG_1001.JPG", kind: "photo", status: "selected" },
  ], "http://192.168.1.2:8080", "周末拍摄", 789);

  assert.equal(queue.version, 1);
  assert.equal(queue.createdAt, 789);
  assert.equal(queue.desktopAddress, "http://192.168.1.2:8080");
  assert.equal(queue.eventName, "周末拍摄");
  assert.equal(queue.totalBytes, 2048);
  assert.equal(queue.files[0].file, file);
  assert.equal(queue.files[0].relativePath, "DCIM/IMG_1001.JPG");
  assert.equal(queue.files[0].lastModified, 456);
});

test("restored queue is resumable and drops invalid stored file entries", () => {
  const first = fakeFile("IMG_1.JPG", 10);
  const saved = { version: 99, desktopAddress: "http://desktop", eventName: "旅行", files: [
    { file: first, relativePath: "IMG_1.JPG", kind: "photo", size: 10 },
    { file: { name: "lost reference" }, relativePath: "lost.jpg" },
  ] };

  const restored = restorePhoneQueue(saved);
  assert.equal(restored.queue.version, 1);
  assert.equal(restored.queue.files.length, 1);
  assert.equal(restored.selectedFiles.length, 1);
  assert.equal(restored.selectedFiles[0].file, first);
  assert.equal(restored.selectedFiles[0].status, "待连接电脑");
});

test("empty or unusable persisted queues are rejected for safe cleanup", () => {
  assert.equal(restorePhoneQueue(null), null);
  assert.equal(restorePhoneQueue({ files: [] }), null);
  assert.equal(restorePhoneQueue({ files: [{ relativePath: "gone.jpg" }] }), null);
});
