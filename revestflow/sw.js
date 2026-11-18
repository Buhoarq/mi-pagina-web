/* FlujoPlan · fuera de servicio (18-11-2026). Reemplaza al service worker de la aplicación: borra todo lo guardado en caché
   (páginas, modelos y avances cifrados descargados), se da de baja y recarga las pestañas abiertas, que pasan a mostrar «fuera de servicio». */
self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil((async()=>{
  try{const ks=await caches.keys();await Promise.all(ks.filter(k=>!k.startsWith('puertaflow-')).map(k=>caches.delete(k)));}catch(_){}
  try{await self.registration.unregister();}catch(_){}
  try{const cs=await self.clients.matchAll({type:'window'});cs.forEach(c=>{try{c.navigate(c.url);}catch(_){}});}catch(_){}
})()));
self.addEventListener('fetch',e=>{});
