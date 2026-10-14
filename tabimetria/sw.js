/* TabiMetría — service worker: deja la app disponible sin conexión.
   Estrategia: responde desde caché al instante y actualiza en segundo plano. */
const CACHE='tabimetria-v1.0';
const BASE=['./','./index.html','./manifest.webmanifest','./icono.svg'];
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.all(BASE.map(u=>c.add(u).catch(()=>{})))));
  self.skipWaiting();
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  e.respondWith(caches.match(req,{ignoreSearch:true}).then(hit=>{
    const red=fetch(req).then(r=>{
      if(r&&(r.ok||r.type==='opaque')){const cp=r.clone();caches.open(CACHE).then(c=>c.put(req,cp));}
      return r;
    }).catch(()=>hit||(req.mode==='navigate'?caches.match('./index.html'):undefined));
    return hit||red;
  }));
});
