/* LastPlan (antes Last Planner) — service worker propio: solo borra sus cachés (prefijo lastplanner).
   Modelo y avance se leen de ../tabiflow/; plan.enc y subclaves.json son de esta carpeta. */
const CACHE='lastplanner-v7.3';
const BASE=['./','./index.html','./manifest.webmanifest','./icono.svg','../tabiflow/clave.json','../tabiflow/modelo.enc'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>Promise.all(BASE.map(u=>c.add(u).catch(()=>{})))));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('lastplanner')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);if(url.origin!==location.origin)return;
  const clave=url.pathname.replace(/^.*\//,'');
  const redPrimero=(/\.enc$/.test(clave)||/^(avance\.enc|adjuntos\.enc|plan\.enc|clave\.json|index\.html|)$/.test(clave))||req.mode==='navigate';
  if(redPrimero){
    e.respondWith(fetch(req).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(new Request(url.origin+url.pathname),cp));}return r;})
      .catch(()=>caches.match(new Request(url.origin+url.pathname)).then(h=>h||caches.match('./index.html'))));
    return;}
  e.respondWith(caches.match(new Request(url.origin+url.pathname)).then(hit=>{
    const red=fetch(req).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(new Request(url.origin+url.pathname),cp));}return r;}).catch(()=>hit);
    return hit||red;}));
});
