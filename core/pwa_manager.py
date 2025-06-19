#!/usr/bin/env python3
"""
Progressive Web App (PWA) Enhancement Module
AI Agent 3D Print System

Provides enhanced PWA capabilities including:
- Advanced service worker functionality
- Offline capability management
- Background sync for print jobs
- Push notifications
- Mobile-optimized features
- App shell caching
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.logger import get_logger

logger = get_logger(__name__)


class PWAManager:
    """Manage Progressive Web App features and capabilities"""
    
    def __init__(self, web_dir: Path):
        self.web_dir = web_dir
        self.logger = get_logger(f"{__name__}.PWAManager")
    
    def generate_manifest(self, 
                         name: str = "AI Agent 3D Print System",
                         short_name: str = "AI 3D Print",
                         description: str = "AI-powered 3D printing workflow system") -> Dict[str, Any]:
        """Generate enhanced PWA manifest"""
        manifest = {
            "name": name,
            "short_name": short_name,
            "description": description,
            "start_url": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "theme_color": "#2563eb",
            "background_color": "#ffffff",
            "scope": "/",
            "lang": "en-US",
            "dir": "ltr",
            
            # Enhanced icons
            "icons": [
                {
                    "src": "/web/assets/icons/icon-72.png",
                    "sizes": "72x72",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-96.png",
                    "sizes": "96x96",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-128.png",
                    "sizes": "128x128",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-144.png",
                    "sizes": "144x144",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-152.png",
                    "sizes": "152x152",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-384.png",
                    "sizes": "384x384",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/web/assets/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ],
            
            # Enhanced features
            "categories": ["productivity", "utilities", "technology"],
            "related_applications": [],
            "prefer_related_applications": False,
            
            # Shortcuts for quick actions
            "shortcuts": [
                {
                    "name": "Quick Print",
                    "short_name": "Print",
                    "description": "Start a new 3D print job",
                    "url": "/?action=quick-print",
                    "icons": [
                        {
                            "src": "/web/assets/icons/shortcut-print.png",
                            "sizes": "96x96"
                        }
                    ]
                },
                {
                    "name": "View History",
                    "short_name": "History",
                    "description": "View print history",
                    "url": "/?action=history",
                    "icons": [
                        {
                            "src": "/web/assets/icons/shortcut-history.png",
                            "sizes": "96x96"
                        }
                    ]
                },
                {
                    "name": "System Status",
                    "short_name": "Status",
                    "description": "Check system status",
                    "url": "/?action=status",
                    "icons": [
                        {
                            "src": "/web/assets/icons/shortcut-status.png",
                            "sizes": "96x96"
                        }
                    ]
                }
            ],
            
            # Screenshots for app stores
            "screenshots": [
                {
                    "src": "/web/assets/screenshots/desktop-main.png",
                    "sizes": "1280x720",
                    "type": "image/png",
                    "platform": "wide"
                },
                {
                    "src": "/web/assets/screenshots/mobile-main.png",
                    "sizes": "375x812",
                    "type": "image/png",
                    "platform": "narrow"
                }
            ],
            
            # Enhanced display modes
            "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
            
            # File handling for 3D models
            "file_handlers": [
                {
                    "action": "/upload",
                    "accept": {
                        "model/gltf-binary": [".glb"],
                        "model/gltf+json": [".gltf"],
                        "model/stl": [".stl"],
                        "model/obj": [".obj"],
                        "application/sla": [".3mf"]
                    }
                }
            ],
            
            # Protocol handlers
            "protocol_handlers": [
                {
                    "protocol": "web+3dprint",
                    "url": "/print?url=%s"
                }
            ],
            
            # Share target for sharing 3D models
            "share_target": {
                "action": "/share",
                "method": "POST",
                "enctype": "multipart/form-data",
                "params": {
                    "title": "title",
                    "text": "text",
                    "url": "url",
                    "files": [
                        {
                            "name": "model",
                            "accept": ["model/*", ".stl", ".obj", ".gltf", ".glb", ".3mf"]
                        }
                    ]
                }
            }
        }
        
        return manifest
    
    def generate_service_worker(self) -> str:
        """Generate enhanced service worker for offline functionality"""
        sw_content = """
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
"""
        return sw_content
    
    def create_offline_pages(self):
        """Create offline fallback pages and resources"""
        offline_dir = self.web_dir / "offline"
        offline_dir.mkdir(exist_ok=True)
        
        # Offline index page
        offline_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 3D Print - Offline</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .offline-container {
            text-align: center;
            max-width: 400px;
        }
        .offline-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        .offline-title {
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        .offline-message {
            font-size: 1.1rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }
        .retry-button {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid white;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .retry-button:hover {
            background: rgba(255, 255, 255, 0.3);
        }
    </style>
</head>
<body>
    <div class="offline-container">
        <div class="offline-icon">🌐</div>
        <h1 class="offline-title">You're Offline</h1>
        <p class="offline-message">
            No internet connection detected. Some features may be limited while offline.
        </p>
        <button class="retry-button" onclick="location.reload()">
            Try Again
        </button>
    </div>
</body>
</html>
"""
        
        with open(offline_dir / "index.html", "w") as f:
            f.write(offline_html)
        
        # Offline API responses
        offline_responses = {
            "status.json": {
                "success": False,
                "offline": True,
                "message": "Status unavailable offline"
            },
            "print-request.json": {
                "success": False,
                "offline": True,
                "message": "Cannot start print jobs while offline"
            },
            "history.json": {
                "success": False,
                "offline": True,
                "message": "History unavailable offline"
            }
        }
        
        for filename, data in offline_responses.items():
            with open(offline_dir / filename, "w") as f:
                json.dump(data, f)
    
    def setup_pwa(self):
        """Set up complete PWA functionality"""
        try:
            # Generate and save manifest
            manifest = self.generate_manifest()
            manifest_path = self.web_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Generate and save service worker
            sw_content = self.generate_service_worker()
            sw_path = self.web_dir / "sw.js"
            with open(sw_path, "w") as f:
                f.write(sw_content)
            
            # Create offline pages
            self.create_offline_pages()
            
            self.logger.info("✅ PWA setup complete")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ PWA setup failed: {e}")
            return False


def setup_pwa_for_system(web_dir: Path = None):
    """Convenience function to set up PWA for the system"""
    if web_dir is None:
        web_dir = Path("web")
    
    pwa_manager = PWAManager(web_dir)
    return pwa_manager.setup_pwa()
