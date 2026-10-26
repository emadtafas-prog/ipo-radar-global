const CACHE = 'ipo-radar-global-v3.0';
const SHELL = ['./','./index.html','./manifest.webmanifest','./assets/icon-192.png','./assets/icon-512.png'];
const DATA_KEY = new URL('./data/signals.json', self.registration.scope).href;
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET'||new URL(event.request.url).origin!==self.location.origin)return;
 if(new URL(event.request.url).pathname.endsWith('/data/signals.json')){
   event.respondWith(fetch(event.request).then(res=>{
     if(res.ok){const copy=res.clone();caches.open(CACHE).then(cache=>cache.put(DATA_KEY,copy))}
     return res;
   }).catch(async()=>await caches.match(DATA_KEY)||new Response(JSON.stringify({generated_at:null,items:[],source_status:[],source_errors:['المصدر غير متصل، ولا توجد نسخة محفوظة.']}),{headers:{'Content-Type':'application/json'}})));
   return;
 }
 event.respondWith(fetch(event.request).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(event.request,copy))}return r}).catch(()=>caches.match(event.request)));
});
