// ── RAKSHAK Service Worker v2.0.0 ───────────────────────────────────────────
// Multi-cache strategy, SOS background sync, enhanced push notifications

const SW_VERSION = '2.1.0';
const CACHE_STATIC  = 'rakshak-static-v3';
const CACHE_DYNAMIC = 'rakshak-dynamic-v3';
const CACHE_API     = 'rakshak-api-v3';
const OFFLINE_URL   = '/offline';

// Static app shell to pre-cache
const PRECACHE_ASSETS = [
  '/',
  '/dashboard/',
  '/login/',
  '/static/css/main.css',
  '/static/js/dashboard.js',
  '/static/js/admin.js',
  '/static/js/heatmap.js',
  '/static/manifest.json',
  '/offline',
];

// ── INSTALL: pre-cache static shell ─────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_STATIC).then((cache) => {
      console.log(`[SW ${SW_VERSION}] Pre-caching app shell`);
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  self.skipWaiting();
});

// ── ACTIVATE: purge old caches ──────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  const currentCaches = [CACHE_STATIC, CACHE_DYNAMIC, CACHE_API];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !currentCaches.includes(name))
          .map((name) => {
            console.log(`[SW ${SW_VERSION}] Purging old cache:`, name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// ── FETCH: routing strategy ─────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle failed SOS POST requests with background sync queue
  if (request.method === 'POST' && url.pathname.includes('/sos/')) {
    event.respondWith(handleSosPost(request));
    return;
  }

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip WebSocket upgrades
  if (request.headers.get('Upgrade') === 'websocket') return;

  // API / dynamic routes -> network-first (cached in CACHE_API)
  if (isApiOrDynamic(url)) {
    event.respondWith(networkFirst(request, CACHE_API));
    return;
  }

  // Static assets -> cache-first (cached in CACHE_STATIC)
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, CACHE_STATIC));
    return;
  }

  // HTML pages -> network-first with offline fallback (cached in CACHE_DYNAMIC)
  event.respondWith(networkFirstWithOfflineFallback(request));
});

// ── SOS Background Sync ────────────────────────────────────────────────────
async function handleSosPost(request) {
  try {
    const response = await fetch(request.clone());
    // Notify clients of successful SOS
    notifyClients({ type: 'SOS_SENT', status: 'delivered' });
    return response;
  } catch (err) {
    // Queue the SOS for later delivery
    const body = await request.clone().text();
    const sosQueue = await caches.open('rakshak-sos-queue');
    const queueKey = new Request(`/_sos_queue/${Date.now()}`);
    await sosQueue.put(queueKey, new Response(body, {
      headers: {
        'Content-Type': request.headers.get('Content-Type') || 'application/json',
        'X-Original-URL': request.url,
        'X-Queued-At': new Date().toISOString()
      }
    }));

    // Register for background sync
    if (self.registration.sync) {
      await self.registration.sync.register('flush-sos-queue');
    }

    // Notify clients SOS is queued
    notifyClients({ type: 'SOS_QUEUED', message: 'SOS saved offline — will send when connected' });

    return new Response(JSON.stringify({
      status: 'queued',
      message: 'SOS queued for delivery when connection restores'
    }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// ── Background Sync: flush SOS queue ────────────────────────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'flush-sos-queue') {
    event.waitUntil(flushSosQueue());
  }
});

async function flushSosQueue() {
  const sosQueue = await caches.open('rakshak-sos-queue');
  const keys = await sosQueue.keys();

  for (const key of keys) {
    const cached = await sosQueue.match(key);
    if (!cached) continue;

    const body = await cached.text();
    const originalUrl = cached.headers.get('X-Original-URL');
    const contentType = cached.headers.get('Content-Type');

    try {
      const response = await fetch(originalUrl, {
        method: 'POST',
        headers: { 'Content-Type': contentType },
        body: body
      });

      if (response.ok) {
        await sosQueue.delete(key);
        notifyClients({ type: 'SOS_SENT', status: 'delivered', url: originalUrl });
      }
    } catch (err) {
      console.log(`[SW] SOS retry failed for ${originalUrl}, keeping in queue`);
    }
  }
}

// ── Strategy: network-first ─────────────────────────────────────────────────
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: 'offline', message: 'No network connection' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ── Strategy: cache-first ───────────────────────────────────────────────────
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    return new Response('', { status: 408, statusText: 'Offline' });
  }
}

// ── Strategy: network-first with offline fallback ───────────────────────────
async function networkFirstWithOfflineFallback(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_DYNAMIC);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;

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

// ── Client messaging ────────────────────────────────────────────────────────
async function notifyClients(data) {
  const clients = await self.clients.matchAll({ type: 'window' });
  clients.forEach(client => client.postMessage(data));
}

// ── PUSH NOTIFICATIONS: type-based routing ──────────────────────────────────
self.addEventListener('push', (event) => {
  let data = {
    title: 'RAKSHAK ALERT',
    body: 'New safety notification.',
    icon: '/static/manifest.json',
    tag: 'rakshak-alert',
    requireInteraction: false,
    vibrate: [200, 100, 200],
    actions: [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      data = { ...data, ...payload };

      // Type-based notification styling
      if (payload.type === 'sos') {
        data.title = 'SOS EMERGENCY ALERT';
        data.requireInteraction = true;
        data.vibrate = [500, 200, 500, 200, 500, 200, 1000];
        data.tag = 'sos-emergency';
        data.actions = [
          { action: 'view', title: 'View Alert' },
          { action: 'call', title: 'Call 112' },
        ];
      } else if (payload.type === 'safewalk') {
        data.title = 'SAFE WALK UPDATE';
        data.vibrate = [100, 50, 100];
        data.tag = 'safewalk-update';
      }
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

  // Emergency call action
  if (action === 'call') {
    event.waitUntil(self.clients.openWindow('tel:112'));
    return;
  }

  if (action === 'dismiss') return;

  let targetUrl = '/dashboard/';
  if (event.notification.data && event.notification.data.url) {
    targetUrl = event.notification.data.url;
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes('/dashboard') && 'focus' in client) {
          return client.focus();
        }
      }
      return self.clients.openWindow(targetUrl);
    })
  );
});

// ── MESSAGE HANDLER: commands from main app ─────────────────────────────────
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (event.data === 'GET_VERSION') {
    event.source.postMessage({ type: 'SW_VERSION', version: SW_VERSION });
  } else if (event.data === 'FLUSH_SOS_QUEUE') {
    flushSosQueue();
  }
});
