// beta retirada: el service worker se desinstala solo y borra su caché
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil((async()=>{for(const k of await caches.keys())if(k.startsWith('tabiflow-beta'))await caches.delete(k);await self.registration.unregister();for(const c of await self.clients.matchAll())c.navigate(c.url);})()));
