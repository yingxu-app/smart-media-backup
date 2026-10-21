(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.YingxuPhoneQueue = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function createPhoneQueue(selectedFiles, desktopAddress, eventName, createdAt = Date.now()) {
    const files = (Array.isArray(selectedFiles) ? selectedFiles : []).filter(item => item?.file)
      .map(item => ({
        file: item.file,
        relativePath: String(item.relativePath || item.file.name || "未命名文件"),
        kind: String(item.kind || "file"),
        name: String(item.file.name || ""),
        size: Math.max(0, Number(item.file.size) || 0),
        lastModified: Math.max(0, Number(item.file.lastModified) || 0),
      }));
    return {
      version: 1,
      createdAt: Number(createdAt) || Date.now(),
      desktopAddress: String(desktopAddress || ""),
      eventName: String(eventName || ""),
      totalBytes: files.reduce((sum, item) => sum + item.size, 0),
      files,
    };
  }

  function restorePhoneQueue(saved) {
    if (!saved || !Array.isArray(saved.files)) return null;
    const files = saved.files.filter(item => item?.file && typeof item.file.slice === "function"
      && typeof item.relativePath === "string");
    if (!files.length) return null;
    const queue = { ...saved, version: 1, files,
      totalBytes: files.reduce((sum, item) => sum + Math.max(0, Number(item.size) || 0), 0) };
    return {
      queue,
      selectedFiles: files.map(item => ({
        file: item.file,
        relativePath: item.relativePath,
        kind: item.kind,
        status: "待连接电脑",
      })),
    };
  }

  return { createPhoneQueue, restorePhoneQueue };
});
