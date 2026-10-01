self.addEventListener("install", e => {
  e.waitUntil(
    caches.open("uol-chat-pwa").then(cache => {
      return cache.addAll([
        "./",
        "./index.html",
        "./css/style.css",
        "./js/script.js",
        "./assets/uni_logo.png",
        "./assets/uni_bg.png",
        "./assets/robo.png"
      ]);
    })
  );
});

self.addEventListener("fetch", e => {
  e.respondWith(
    caches.match(e.request).then(response => {
      return response || fetch(e.request);
    })
  );
});
