// ── RAKSHAK Service Worker v1.0 ─────────────────────────────────────────────
// Network-first for API, cache-first for static assets, offline fallback, push

const CACHE_NAME = 'rakshak-v1';
const OFFLINE_URL = '/offline';

// Static assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/static/css/main.css',
  '/static/js/dashboard.js',
  '/static/js/admin.js',
  '/static/js/heatmap.js',
  '/static/js/three_shield.js',
  '/static/manifest.json',
  '/offline',
];

// ── INSTALL: pre-cache static shell ─────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Pre-caching app shell');
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  // Activate immediately, don't wait for old SW to die
  self.skipWaiting();
});

// ── ACTIVATE: purge old caches ──────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  // Claim all open tabs immediately
  self.clients.claim();
});

// ── FETCH: routing strategy ─────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests (POST for SOS, etc.)
  if (request.method !== 'GET') return;

  // Skip WebSocket upgrades (SocketIO)
  if (request.headers.get('Upgrade') === 'websocket') return;

  // API / dynamic routes  ->  network-first
  if (isApiOrDynamic(url)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets  ->  cache-first
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // HTML pages  ->  network-first with offline fallback
  event.respondWith(networkFirstWithOfflineFallback(request));
});

// ── Strategy: network-first (API calls) ─────────────────────────────────────
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    // Cache successful API responses for offline reads
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    // For API calls with no cache, return a JSON error
    return new Response(
      JSON.stringify({ error: 'offline', message: 'No network connection' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ── Strategy: cache-first (static assets) ───────────────────────────────────
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Return empty response for non-critical assets
    return new Response('', { status: 408, statusText: 'Offline' });
  }
}

// ── Strategy: network-first with offline fallback (HTML pages) ──────────────
async function networkFirstWithOfflineFallback(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;

    // Serve the offline fallback page
    const offlinePage = await caches.match(OFFLINE_URL);
    if (offlinePage) return offlinePage;

    return new Response('<h1>Offline</h1>', {
      status: 503,
      headers: { 'Content-Type': 'text/html' },
    });
  }
}

// ── Route classifiers ───────────────────────────────────────────────────────
function isApiOrDynamic(url) {
  const apiPaths = ['/api/', '/sos/', '/socket.io/', '/auth/', '/admin/'];
  return apiPaths.some((p) => url.pathname.startsWith(p));
}

function isStaticAsset(url) {
  return (
    url.pathname.startsWith('/static/') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.jpg') ||
    url.pathname.endsWith('.svg') ||
    url.pathname.endsWith('.ico') ||
    url.pathname.endsWith('.woff2') ||
    url.pathname.endsWith('.woff')
  );
}

// ── PUSH NOTIFICATIONS: SOS alerts ──────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = {
    title: 'RAKSHAK SOS ALERT',
    body: 'Emergency alert triggered nearby.',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    tag: 'sos-alert',
    requireInteraction: true,
    vibrate: [200, 100, 200, 100, 400],
    actions: [
      { action: 'view', title: 'View Alert' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      data = { ...data, ...payload };
    } catch (e) {
      data.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
      tag: data.tag,
      requireInteraction: data.requireInteraction,
      vibrate: data.vibrate,
      actions: data.actions,
      data: data,
    })
  );
});

// ── NOTIFICATION CLICK: route user to alert ─────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const action = event.action;
  let targetUrl = '/dashboard/';

  if (action === 'view' && event.notification.data && event.notification.data.url) {
    targetUrl = event.notification.data.url;
  } else if (action === 'dismiss') {
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Focus existing tab if open
      for (const client of windowClients) {
        if (client.url.includes('/dashboard') && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise open a new tab
      return clients.openWindow(targetUrl);
    })
  );
});
