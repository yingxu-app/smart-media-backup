const CACHE_NAME = "yingxu-pocket-shell-v2";
const SHELL_INDEX = new URL("./index.html", self.registration.scope).href;
const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./firebase-config.js",
  "./cloud-sync.js",
  "./app.js",
  "../assets/yingxu-icon.svg",
  "../assets/yingxu-icon-180.png",
  "../assets/yingxu-icon-512.png",
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith("yingxu-pocket-shell-") && key !== CACHE_NAME)
    .map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  // Never cache Firebase Auth, Realtime Database, or other API responses.
  if (url.hostname.includes("firebaseio.com") || url.hostname.includes("firebasedatabase.app")
      || url.hostname === "identitytoolkit.googleapis.com" || url.hostname === "securetoken.googleapis.com") return;

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then(response => {
      if (response.ok) caches.open(CACHE_NAME).then(cache => cache.put(SHELL_INDEX, response.clone()));
      return response;
    }).catch(async () => (await caches.match(SHELL_INDEX)) || (await caches.match(new URL("./", self.registration.scope).href))));
    return;
  }

  event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
    if (response.ok && APP_SHELL.some(path => new URL(path, self.registration.scope).href === request.url)) {
      caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
    }
    return response;
  })));
});
