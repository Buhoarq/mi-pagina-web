/* TabiFlow desactivado: este service worker reemplaza al anterior, borra la caché y se elimina. */
self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil((async()=>{
  for(const k of await caches.keys())await caches.delete(k);
  await self.registration.unregister();
  for(const c of await self.clients.matchAll({type:'window'}))c.navigate(c.url);
})()));
self.addEventListener('fetch',()=>{});
