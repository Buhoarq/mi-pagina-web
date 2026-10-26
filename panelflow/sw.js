/* Panel FlujoPlan HCQ — service worker: la página queda disponible sin conexión; los datos (.enc / .json) se piden siempre
   primero a la red y, sin señal, se muestra la última copia guardada. */
const CACHE='panelflow-hcq-v2.1';
const BASE=['./','./index.html','./manifest.webmanifest','./icono.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>Promise.all(BASE.map(u=>c.add(u).catch(()=>{})))));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('panelflow-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);if(url.origin!==location.origin)return;
  const llave=new Request(url.origin+url.pathname);
  e.respondWith(fetch(req).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(llave,cp));}return r;})
    .catch(()=>caches.match(llave).then(h=>h||caches.match('./index.html'))));
});
