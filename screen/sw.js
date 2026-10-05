/* HowCom office screen: offline cache for the Web Redirect version (Bauer spec: cache static resources).
   Static files: cache first, downloaded once. today.json: network first (4 s), falls back to the cached copy.
   Plain service worker, no Workbox. Bump CACHE when the design changes. */
var CACHE = "howcom-screen-v1";
var ASSETS = [
  "./", "./index.html", "./config.js", "./data.js", "./howcom-logo.png",
  "./fonts/hanken-grotesk-latin-400-normal.woff2",
  "./fonts/hanken-grotesk-latin-500-normal.woff2",
  "./fonts/hanken-grotesk-latin-600-normal.woff2"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(ASSETS); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function networkFirst(req) {
  return caches.open(CACHE).then(function (c) {
    var timeout = new Promise(function (resolve) { setTimeout(function () { resolve(null); }, 4000); });
    var net = fetch(req).then(function (res) {
      if (res && res.ok) c.put(req, res.clone());
      return res;
    }).catch(function () { return null; });
    return Promise.race([net, timeout]).then(function (res) {
      return res || c.match(req).then(function (hit) { return hit || net; });
    });
  });
}

function cacheFirst(req) {
  return caches.match(req).then(function (hit) {
    return hit || fetch(req).then(function (res) {
      if (res && res.ok) caches.open(CACHE).then(function (c) { c.put(req, res.clone()); });
      return res;
    });
  });
}

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var url = new URL(e.request.url);
  if (/today\.json$/.test(url.pathname)) { e.respondWith(networkFirst(e.request)); return; }
  if (url.origin === self.location.origin) e.respondWith(cacheFirst(e.request));
});
