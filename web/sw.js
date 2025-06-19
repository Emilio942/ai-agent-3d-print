
// AI Agent 3D Print System - Enhanced Service Worker
// Version: 2.0.0

const CACHE_NAME = 'ai-3d-print-v2';
const OFFLINE_CACHE = 'ai-3d-print-offline-v2';
const DYNAMIC_CACHE = 'ai-3d-print-dynamic-v2';

// Resources to cache immediately
const STATIC_ASSETS = [
    '/',
    '/web/index.html',
    '/web/css/styles.css',
    '/web/css/components.css',
    '/web/css/advanced.css',
    '/web/js/app.js',
    '/web/js/advanced.js',
    '/web/manifest.json',
    '/web/assets/icons/icon-192.png',
    '/web/assets/icons/icon-512.png',
    '/api/health',
    '/api/docs',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

// API routes that can work offline
const OFFLINE_FALLBACKS = {
    '/api/status/': '/web/offline/status.json',
    '/api/print-request': '/web/offline/print-request.json',
    '/api/history': '/web/offline/history.json'
};

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('🚀 Service Worker installing...');
    
    event.waitUntil(
        Promise.all([
            caches.open(CACHE_NAME).then(cache => {
                console.log('📦 Caching static assets...');
                return cache.addAll(STATIC_ASSETS);
            }),
            caches.open(OFFLINE_CACHE).then(cache => {
                console.log('📱 Setting up offline fallbacks...');
                return cache.addAll(Object.values(OFFLINE_FALLBACKS));
            })
        ]).then(() => {
            console.log('✅ Service Worker installed successfully');
            return self.skipWaiting();
        })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('🔄 Service Worker activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME && 
                        cacheName !== OFFLINE_CACHE && 
                        cacheName !== DYNAMIC_CACHE) {
                        console.log('🗑️ Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('✅ Service Worker activated');
            return self.clients.claim();
        })
    );
});

// Fetch event - handle requests with cache-first strategy
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests and chrome-extension requests
    if (request.method !== 'GET' || url.protocol === 'chrome-extension:') {
        return;
    }
    
    // Handle different types of requests
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleApiRequest(request));
    } else if (url.pathname.startsWith('/web/') || url.pathname === '/') {
        event.respondWith(handleStaticRequest(request));
    } else {
        event.respondWith(handleDynamicRequest(request));
    }
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
    const url = new URL(request.url);
    
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses (except POST requests)
        if (networkResponse.ok && request.method === 'GET') {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('🌐 Network failed for API request, trying cache...');
        
        // Try cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Try offline fallback
        for (const [pattern, fallback] of Object.entries(OFFLINE_FALLBACKS)) {
            if (url.pathname.startsWith(pattern)) {
                const fallbackResponse = await caches.match(fallback);
                if (fallbackResponse) {
                    return fallbackResponse;
                }
            }
        }
        
        // Return offline page for critical API endpoints
        return new Response(JSON.stringify({
            success: false,
            error: 'Offline',
            message: 'This feature requires an internet connection',
            offline: true
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Handle static requests with cache-first strategy
async function handleStaticRequest(request) {
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Try network
        const networkResponse = await fetch(request);
        
        // Cache the response
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('🌐 Network failed for static request');
        
        // Return cached version or offline page
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for HTML requests
        if (request.destination === 'document') {
            return caches.match('/web/offline/index.html');
        }
        
        return new Response('Offline', { status: 503 });
    }
}

// Handle dynamic requests
async function handleDynamicRequest(request) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Try cache
        const cachedResponse = await caches.match(request);
        return cachedResponse || new Response('Offline', { status: 503 });
    }
}

// Background sync for print jobs
self.addEventListener('sync', event => {
    console.log('🔄 Background sync triggered:', event.tag);
    
    if (event.tag === 'sync-print-jobs') {
        event.waitUntil(syncPrintJobs());
    }
});

// Sync queued print jobs when online
async function syncPrintJobs() {
    try {
        const db = await openIndexedDB();
        const queuedJobs = await getQueuedJobs(db);
        
        for (const job of queuedJobs) {
            try {
                const response = await fetch('/api/print-request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(job.data)
                });
                
                if (response.ok) {
                    await removeQueuedJob(db, job.id);
                    console.log('✅ Synced print job:', job.id);
                }
            } catch (error) {
                console.log('❌ Failed to sync print job:', job.id, error);
            }
        }
    } catch (error) {
        console.log('❌ Background sync failed:', error);
    }
}

// Push notification handling
self.addEventListener('push', event => {
    console.log('📨 Push notification received');
    
    if (!event.data) return;
    
    const data = event.data.json();
    const options = {
        body: data.body || 'Your 3D print job has an update',
        icon: '/web/assets/icons/icon-192.png',
        badge: '/web/assets/icons/badge.png',
        vibrate: [200, 100, 200],
        data: data.data || {},
        actions: [
            {
                action: 'view',
                title: 'View Details',
                icon: '/web/assets/icons/view.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/web/assets/icons/dismiss.png'
            }
        ],
        requireInteraction: data.requireInteraction || false
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'AI 3D Print System', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('🔔 Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'view') {
        const urlToOpen = event.notification.data.url || '/';
        event.waitUntil(clients.openWindow(urlToOpen));
    }
});

// IndexedDB helpers for offline storage
function openIndexedDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('AI3DPrintDB', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = event => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('queuedJobs')) {
                db.createObjectStore('queuedJobs', { keyPath: 'id' });
            }
        };
    });
}

async function getQueuedJobs(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['queuedJobs'], 'readonly');
        const store = transaction.objectStore('queuedJobs');
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

async function removeQueuedJob(db, jobId) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['queuedJobs'], 'readwrite');
        const store = transaction.objectStore('queuedJobs');
        const request = store.delete(jobId);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

console.log('🚀 AI 3D Print Service Worker loaded');
