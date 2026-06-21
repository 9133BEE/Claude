const CACHE = 'guxue-v25';
const PAGES = [
  './index.html',
  './candlestick-patterns.html',
  './stock-course.html',
  './futures-course.html',
  './us-futures-course.html',
  './us-stock-course.html',
  './advanced-tips.html',
  './futures-advanced-tips.html',
  './stock-quiz.html',
  './futures-quiz.html',
  './stock-glossary.html',
  './futures-glossary.html',
  './strategy-glossary.html',
  './tradingview-guide.html',
  './advanced-indicators.html',
  './tv-indicators.html',
  './trade-journal.html',
  './manifest.json',
  './manifest-journal.json',
  './icon.svg',
  './icon-journal.svg'
];

// 安裝時預先快取所有頁面
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PAGES)).then(() => self.skipWaiting())
  );
});

// 啟動時清除舊快取
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// 請求攔截：快取優先，失敗再從網路取
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => caches.match('./index.html'));
    })
  );
});
