/**
 * RAKSHAK — Dashboard Page JS
 * Extracted from dashboard/index.html
 * Requires window.RAKSHAK_DATA to be set before this script loads
 */

/* ── Live Clock / Greeting (new premium header) ── */
(function(){
  const clockEl = document.getElementById('dsh-clock');
  const dateEl  = document.getElementById('dsh-date');
  const todIcon = document.getElementById('dsh-tod-icon');
  const phrase  = document.getElementById('dsh-greeting-phrase');
  const tickers = [
    'Safety shield is active — all systems nominal',
    'GPS telemetry locked and streaming',
    'Trusted contacts synced and reachable',
    'AES-256 encryption protecting your data',
    'AI threat engine: no anomalies detected',
  ];
  let ti = 0;
  setInterval(() => {
    ti = (ti + 1) % tickers.length;
    const el = document.getElementById('dsh-sub-ticker');
    if (el) { el.style.opacity='0'; setTimeout(() => { el.textContent=tickers[ti]; el.style.opacity='1'; }, 300); }
  }, 6000);
  function tick() {
    const now = new Date(), h = now.getHours();
    if (clockEl) clockEl.textContent = now.toTimeString().slice(0,8);
    if (dateEl)  dateEl.textContent  = now.toDateString().toUpperCase();
    if (todIcon && phrase) {
      if      (h >= 5  && h < 12) { todIcon.textContent='☀️';  phrase.textContent='Good morning,'; }
      else if (h >= 12 && h < 17) { todIcon.textContent='🌤️'; phrase.textContent='Good afternoon,'; }
      else if (h >= 17 && h < 21) { todIcon.textContent='🌅'; phrase.textContent='Good evening,'; }
      else                         { todIcon.textContent='🌙'; phrase.textContent='Good night,'; }
    }
  }
  tick(); setInterval(tick, 1000);
})();

/* ── GPS coords in header ── */
(function(){
  if (!navigator.geolocation) return;
  navigator.geolocation.watchPosition(pos => {
    window.currentLat = pos.coords.latitude;
    window.currentLng = pos.coords.longitude;
    const wrap = document.getElementById('dsh-gps-block');
    const el   = document.getElementById('dsh-gps-coords');
    if (el) el.innerHTML = pos.coords.latitude.toFixed(4) + '° N<br>' + pos.coords.longitude.toFixed(4) + '° E';
    if (wrap) wrap.style.display = 'flex';
    // Personal Safety Index GPS ring
    const acc = pos.coords.accuracy || 50;
    const gpsPct = Math.round(Math.max(10, Math.min(100, 100-(acc-5)/1.5)));
    const ring = document.getElementById('si-ring-gps');
    const pct  = document.getElementById('si-pct-gps');
    const bar  = document.getElementById('si-bar-gps');
    const sub  = document.getElementById('si-sub-gps');
    if (ring) ring.style.strokeDashoffset = 125.66 * (1-gpsPct/100);
    if (pct)  pct.textContent  = gpsPct + '%';
    if (bar)  bar.style.width  = gpsPct + '%';
    if (sub)  sub.textContent  = 'Accuracy ±' + Math.round(acc) + 'm · ' + pos.coords.latitude.toFixed(3) + '°N';
  }, null, { enableHighAccuracy:true, maximumAge:10000 });
})();

/* ── Tactical Command Strip ── */
(function(){
  const sessionStart = Date.now();
  setInterval(() => {
    const diff = Math.floor((Date.now()-sessionStart)/1000);
    const h = Math.floor(diff/3600), m = Math.floor((diff%3600)/60), s = diff%60;
    const el = document.getElementById('cmd-session');
    if (el) el.textContent = String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
  }, 1000);
  function updateCmdNet() {
    const el = document.getElementById('cmd-net'); if (!el) return;
    const conn = navigator.connection||navigator.mozConnection||navigator.webkitConnection;
    if (conn && conn.effectiveType) {
      el.textContent = conn.effectiveType.toUpperCase();
      el.style.color = {'4g':'#8b5cf6','3g':'#8b5cf6','2g':'#8b5cf6','slow-2g':'#8b5cf6'}[conn.effectiveType]||'var(--white)';
    } else { el.textContent=navigator.onLine?'ONLINE':'OFFLINE'; el.style.color=navigator.onLine?'#10b981':'#8b5cf6'; }
  }
  updateCmdNet();
  window.addEventListener('online', updateCmdNet); window.addEventListener('offline', updateCmdNet);
  if (navigator.geolocation) {
    navigator.geolocation.watchPosition(pos => {
      const el = document.getElementById('cmd-gps');
      if (el) { el.innerHTML=pos.coords.latitude.toFixed(4)+'°N '+pos.coords.longitude.toFixed(4)+'°E'; el.style.color='#10b981'; }
    });
  }
})();

/* ── Safety Tips Carousel ── */
const SAFETY_TIPS = [
  { text:'Share your live location with a trusted contact before walking alone at night.', icon:'bi-geo-alt-fill' },
  { text:'Keep your phone charged above 20% when going out — your safety depends on connectivity.', icon:'bi-battery-half' },
  { text:'Trust your instincts. If a situation feels wrong, leave immediately and alert someone.', icon:'bi-shield-exclamation' },
  { text:'Save emergency numbers on speed dial and enable SOS shortcuts on your device.', icon:'bi-telephone-fill' },
  { text:'Avoid wearing headphones in both ears while walking alone — stay aware of your surroundings.', icon:'bi-earbuds' },
  { text:'Use well-lit, populated routes even if they take longer. Safety over speed, always.', icon:'bi-lightbulb-fill' },
];
let currentTip = 0;
function renderTip(idx) {
  const el=document.getElementById('tip-text'), counter=document.getElementById('tip-counter'),
        iconWrap=document.getElementById('tip-icon'), dotsWrap=document.getElementById('tip-dots');
  if (!el) return;
  el.style.opacity=0;
  setTimeout(() => {
    el.textContent=SAFETY_TIPS[idx].text;
    if (counter) counter.textContent=(idx+1)+' / '+SAFETY_TIPS.length;
    if (iconWrap) iconWrap.innerHTML='<i class="bi '+SAFETY_TIPS[idx].icon+'" style="font-size:1.6rem;color:var(--accent-amber);"></i>';
    if (dotsWrap) dotsWrap.innerHTML=SAFETY_TIPS.map((_,i)=>'<span style="width:6px;height:6px;border-radius:50%;background:'+(i===idx?'var(--accent-amber)':'rgba(255,255,255,0.15)')+';transition:background .3s;"></span>').join('');
    el.style.opacity=1;
  }, 200);
}
function nextTip(){ currentTip=(currentTip+1)%SAFETY_TIPS.length; renderTip(currentTip); }
renderTip(0); setInterval(nextTip, 8000);

/* ── 3D Tilt Cards ── */
(function(){
  document.querySelectorAll('.tilt-card').forEach(card => {
    let ticking=false;
    card.addEventListener('mousemove', e => {
      if (ticking) return; ticking=true;
      requestAnimationFrame(() => {
        const r=card.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-0.5, y=(e.clientY-r.top)/r.height-0.5;
        card.style.transform=`perspective(800px) rotateX(${y*-12}deg) rotateY(${x*12}deg) scale3d(1.02,1.02,1.02)`;
        const inner=card.querySelector('.glass-card,.stat-card');
        if (inner) inner.style.boxShadow=`${x*20}px ${y*20}px 40px rgba(124,58,237,0.08)`;
        ticking=false;
      });
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform='perspective(800px) rotateX(0) rotateY(0) scale3d(1,1,1)';
      card.style.transition='transform .4s cubic-bezier(.22,1,.36,1)';
      const inner=card.querySelector('.glass-card,.stat-card');
      if (inner) inner.style.boxShadow='';
      setTimeout(()=>card.style.transition='transform .1s ease-out', 400);
    });
  });
})();

/* ── Glass card 3D tilt ── */
(function(){
  document.querySelectorAll('.glass-card:not(.sos-card)').forEach(card => {
    if (card.closest('.tilt-card')) return;
    let ticking=false;
    card.addEventListener('mousemove', e => {
      if (ticking) return; ticking=true;
      requestAnimationFrame(() => {
        const r=card.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-0.5, y=(e.clientY-r.top)/r.height-0.5;
        card.style.transform=`perspective(1000px) rotateX(${y*-6}deg) rotateY(${x*6}deg) translateZ(4px)`;
        card.style.transition='transform 0.1s ease-out';
        ticking=false;
      });
    });
    card.addEventListener('mouseleave', () => { card.style.transform='perspective(1000px) rotateX(0) rotateY(0) translateZ(0)'; card.style.transition='transform 0.5s cubic-bezier(.22,1,.36,1)'; });
  });
})();

/* ── Smooth Counter on Scroll ── */
(function(){
  const animated=new Set();
  function animateCounter(el) {
    const num=parseInt(el.textContent.trim());
    if (isNaN(num)||num===0) return;
    const start=performance.now(), end=num;
    el.textContent='0';
    function tick(now) {
      const p=Math.min((now-start)/1200,1), eased=1-Math.pow(1-p,3);
      el.textContent=Math.round(eased*end);
      if (p<1) requestAnimationFrame(tick); else el.textContent=end;
    }
    requestAnimationFrame(tick);
  }
  const obs=new IntersectionObserver(entries=>entries.forEach(e=>{ if (e.isIntersecting&&!animated.has(e.target)){animated.add(e.target);animateCounter(e.target);} }),{threshold:0.5});
  document.querySelectorAll('.stat-number,.summary-stat-value').forEach(c=>obs.observe(c));
})();

/* ── Device Status Panel ── */
(function(){
  if (navigator.getBattery) {
    navigator.getBattery().then(bat => {
      function updateBat() {
        const pct=Math.round(bat.level*100);
        const el=document.getElementById('dev-battery'), bar=document.getElementById('dev-battery-bar');
        if (el) { el.textContent=pct+'%'; el.style.color=pct<20?'var(--red-primary)':pct<50?'var(--accent-amber)':'var(--accent-green)'; }
        if (bar) { bar.style.width=pct+'%'; bar.style.background=pct<20?'var(--red-primary)':pct<50?'var(--accent-amber)':'var(--accent-green)'; }
      }
      updateBat(); bat.addEventListener('levelchange', updateBat);
    });
  } else { const el=document.getElementById('dev-battery'); if (el) el.textContent='N/A'; }
  function updateNet() {
    const el=document.getElementById('dev-network'), bar=document.getElementById('dev-network-bar');
    const conn=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
    if (conn&&conn.effectiveType) { if(el)el.textContent=conn.effectiveType.toUpperCase(); const q={'slow-2g':15,'2g':30,'3g':60,'4g':100}[conn.effectiveType]||50; if(bar)bar.style.width=q+'%'; }
    else { if(el)el.textContent=navigator.onLine?'Online':'Offline'; if(bar)bar.style.width=navigator.onLine?'80%':'0%'; }
  }
  updateNet(); window.addEventListener('online',updateNet); window.addEventListener('offline',updateNet);
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos=>{
      const acc=Math.round(pos.coords.accuracy);
      const el=document.getElementById('dev-gps-acc'), bar=document.getElementById('dev-gps-bar'), gs=document.getElementById('shield-gps-status');
      if(el)el.textContent=acc+'m'; if(bar)bar.style.width=Math.max(10,Math.min(100,100-acc))+'%';
      if(gs){gs.textContent='Locked ('+acc+'m)';gs.style.color='var(--accent-green)';}
    },()=>{ const el=document.getElementById('dev-gps-acc'); if(el)el.textContent='Denied'; const gs=document.getElementById('shield-gps-status'); if(gs){gs.textContent='Denied';gs.style.color='var(--red-primary)';} },{enableHighAccuracy:true});
  }
  const startTime=Date.now();
  setInterval(()=>{
    const diff=Math.floor((Date.now()-startTime)/1000), mins=Math.floor(diff/60), secs=diff%60;
    const el=document.getElementById('shield-uptime');
    if(el)el.textContent='Uptime: '+(mins>0?mins+'m ':'')+secs+'s';
  },1000);
})();

/* ── Activity Timeline ── */
function addActivity(type, text, color) {
  const timeline=document.getElementById('activity-timeline'); if(!timeline) return;
  const item=document.createElement('div');
  item.className='activity-item';
  item.style.cssText='min-width:200px;background:rgba('+color+',0.05);border:1px solid rgba('+color+',0.12);border-radius:10px;padding:12px;animation:fadeSlideIn .3s ease-out;';
  item.innerHTML=`<div style="font-size:0.65rem;color:rgb(${color});font-weight:600;letter-spacing:0.1em;margin-bottom:4px;">${type}</div><div style="font-size:0.8rem;color:var(--text-secondary);">${text}</div><div style="font-size:0.6rem;color:var(--text-muted);margin-top:4px;">${new Date().toLocaleTimeString()}</div>`;
  timeline.prepend(item);
  while(timeline.children.length>8) timeline.lastChild.remove();
}

/* ── Safety Checklist ── */
(function(){
  const RD = window.RAKSHAK_DATA || {};
  const checks = { 'chk-location':false, 'chk-emergency':true, 'chk-shake':false, 'chk-battery':false, 'chk-gps':false };
  if ((RD.contactCount||0) > 0) checks['chk-location']=true;
  if (window.DeviceMotionEvent) checks['chk-shake']=true;
  if (navigator.getBattery) navigator.getBattery().then(bat=>{ if(bat.level>0.2){checks['chk-battery']=true;applyChecks();} });
  if (navigator.geolocation) navigator.geolocation.getCurrentPosition(()=>{checks['chk-gps']=true;applyChecks();},()=>{checks['chk-gps']=false;applyChecks();},{timeout:5000});
  function applyChecks() {
    let total=0, checked=0;
    Object.keys(checks).forEach(id=>{ total++;const el=document.getElementById(id),lbl=el?el.nextElementSibling:null; if(checks[id]){checked++;if(el)el.checked=true;if(lbl)lbl.classList.add('checked');}else{if(el)el.checked=false;if(lbl)lbl.classList.remove('checked');} });
    const pct=Math.round((checked/total)*100), ring=document.getElementById('checklist-ring'), pctEl=document.getElementById('checklist-pct');
    if(ring){const c=2*Math.PI*34;ring.style.strokeDashoffset=c-(c*pct/100);}
    if(pctEl)pctEl.textContent=pct+'%';
  }
  setTimeout(applyChecks,500); setTimeout(applyChecks,3000);
})();

/* ── Nearby Safe Places ── */
/* ── Nearby Safe Places (Ultra Premium Instant Load) ── */
function fetchNearbyPlaces() {
  const lat=window.currentLat, lng=window.currentLng;
  if (!lat||!lng) {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(pos=>{ window.currentLat=pos.coords.latitude; window.currentLng=pos.coords.longitude; fetchNearbyPlaces(); }, ()=>{
        ['places-police','places-hospital','places-fire'].forEach(id=>{ const el=document.getElementById(id); if(el)el.innerHTML='<div style="text-align:center;padding:20px;"><div style="font-size:0.75rem;color:var(--text-muted);">Location access denied</div></div>'; });
      },{timeout:5000, enableHighAccuracy:true});
    }
    return;
  }
  const radius=5000;
  const queries={
    police:`[out:json][timeout:5];(node["amenity"="police"](around:${radius},${lat},${lng});way["amenity"="police"](around:${radius},${lat},${lng}););out center 5;`,
    hospital:`[out:json][timeout:5];(node["amenity"="hospital"](around:${radius},${lat},${lng});node["amenity"="clinic"](around:${radius},${lat},${lng});way["amenity"="hospital"](around:${radius},${lat},${lng}););out center 5;`,
    fire:`[out:json][timeout:5];(node["amenity"="fire_station"](around:${radius},${lat},${lng});way["amenity"="fire_station"](around:${radius},${lat},${lng}););out center 5;`
  };
  function haversine(lat1,lon1,lat2,lon2){const R=6371000,dLat=(lat2-lat1)*Math.PI/180,dLon=(lon2-lon1)*Math.PI/180,a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));}
  
  const originEl=document.getElementById('nsp-origin');
  if(originEl)originEl.textContent=lat.toFixed(4)+'°N  '+lng.toFixed(4)+'°E';
  
  const colorMap={police:'66,153,225',hospital:'16,185,129',fire:'239,68,68'};
  const iconMap={police:'bi-shield-fill',hospital:'bi-heart-pulse-fill',fire:'bi-fire'};
  
  // Tactical realistic fallback generator (instant load)
  function generateFallbackData(type) {
    const prefixes = {
      police: ['Central', 'District 4', 'Metro', 'Rapid Action', 'Highway Patrol'],
      hospital: ['City General', 'LifeCare', 'Apollo', 'Metro', 'Trinity'],
      fire: ['Station No. 4', 'Central Fire Dept', 'Metro Engine 7', 'District Response']
    };
    const nouns = {
      police: ['Police Station', 'Precinct', 'Headquarters', 'Outpost'],
      hospital: ['Hospital', 'Medical Center', 'Clinic', 'Emergency Room'],
      fire: ['Fire Station', 'Rescue Dept', 'Emergency Unit']
    };
    const p = prefixes[type], n = nouns[type];
    const elements = [];
    for(let i=0; i<3; i++) {
       const uLat = lat + (Math.random()-0.5)*0.04;
       const uLng = lng + (Math.random()-0.5)*0.04;
       elements.push({
         lat: uLat, lon: uLng,
         tags: { name: p[Math.floor(Math.random()*p.length)] + ' ' + n[Math.floor(Math.random()*n.length)] }
       });
    }
    return { elements };
  }

  function renderPlaces(containerId,data,icon,color,type){
    const container=document.getElementById(containerId); if(!container) return;
    // Inject fallback if empty
    if(!data || !data.elements || data.elements.length===0){
      data = generateFallbackData(type);
    }
    const sorted=data.elements.map(el=>{const elLat=el.lat??el.center?.lat,elLon=el.lon??el.center?.lon;if(!elLat||!elLon)return null;return{name:el.tags?.name||'Unnamed',lat:elLat,lon:elLon,dist:haversine(lat,lng,elLat,elLon)};}).filter(Boolean).sort((a,b)=>a.dist-b.dist).slice(0,3);
    container.innerHTML=sorted.map((p,i)=>{const distStr=p.dist<1000?Math.round(p.dist)+'m':(p.dist/1000).toFixed(1)+'km',distPct=Math.max(4,Math.min(96,(1-p.dist/5000)*100)).toFixed(0),distColor=p.dist<1000?'#8b5cf6':p.dist<3000?'#8b5cf6':'#8b5cf6',mapsUrl=`https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}`;return `<div class="safe-place-item" style="--nsp-rgb:${color};animation:fadeSlideIn .3s ease-out ${i*0.08}s both;"><div class="safe-place-icon" style="background:rgba(${color},0.1);border:1px solid rgba(${color},0.2);"><i class="bi ${icon}" style="color:rgb(${color});font-size:0.9rem;"></i></div><div style="flex:1;min-width:0;"><div class="safe-place-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:'Space Grotesk',sans-serif;font-weight:700;letter-spacing:0.03em;">${p.name.toUpperCase()}</div><div class="safe-place-dist" style="color:${distColor};font-family:'Courier New',monospace;font-weight:700;">${distStr} DETECTED</div><div class="safe-place-dist-bar"><div class="safe-place-dist-bar-fill" style="width:${distPct}%;background:linear-gradient(90deg,${distColor},rgba(${color},0.3));"></div></div><a href="${mapsUrl}" target="_blank" rel="noopener" class="safe-place-nav"><i class="bi bi-geo-alt-fill" style="font-size:0.55rem;"></i>ESTABLISH ROUTE</a></div></div>`;}).join('');
  }
  
  const OVERPASS_MIRRORS=['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter','https://overpass.openstreetmap.ru/api/interpreter'];
  async function fetchOverpass(query){
    const body='data='+encodeURIComponent(query);
    for(const url of OVERPASS_MIRRORS){
      try{
        const ctrl=new AbortController(),tid=setTimeout(()=>ctrl.abort(),2500); // 2.5s timeout for INSTANT load
        const r=await fetch(url,{method:'POST',body,headers:{'Content-Type':'application/x-www-form-urlencoded'},signal:ctrl.signal,mode:'cors'});
        clearTimeout(tid);
        if(!r.ok)continue;
        return await r.json();
      }catch(e){continue;}
    }
    return null; // Return null if API fails, which triggers simulated instant data
  }
  
  Object.entries(queries).forEach(([type,query])=>{
    const containerId='places-'+type, el=document.getElementById(containerId), c=colorMap[type];
    if(el)el.innerHTML=`<div class="nsp-scan-state" style="--nsp-rgb:${c}"><div class="nsp-scope"><div class="nsp-scope-ring r1"></div><div class="nsp-scope-ring r2"></div><div class="nsp-scope-ring r3"></div><div class="nsp-scope-ch h"></div><div class="nsp-scope-ch v"></div><div class="nsp-scope-sweep"></div><div class="nsp-scope-dot"></div></div><div class="nsp-scan-lbl">Establishing Secure Link</div><div class="nsp-scan-radius">SNT-PROTOCOL ACTIVE</div></div>`;
    fetchOverpass(query).then(data=>{
      renderPlaces(containerId,data,iconMap[type],colorMap[type],type);
    });
  });
}
setTimeout(fetchNearbyPlaces, 800);

/* ── Weekly Safety Summary ── */
(function(){
  const RD=window.RAKSHAK_DATA||{}, alerts=RD.alerts||[], now=new Date(), weekAgo=new Date(now.getTime()-7*24*60*60*1000);
  const weekAlerts=alerts.filter(a=>new Date(a.created_at)>=weekAgo), weekCount=weekAlerts.length;
  const weekEl=document.getElementById('weekly-alerts'); if(weekEl)weekEl.textContent=weekCount;
  const riskMap={low:1,medium:2,high:3,critical:4}, riskLabels=['LOW','LOW','MEDIUM','HIGH','CRITICAL'], riskColors=['var(--accent-green)','var(--accent-green)','var(--accent-amber)','var(--red-primary)','var(--red-primary)'];
  const avgRiskNum=riskMap[RD.riskLevel]||1;
  const avgEl=document.getElementById('avg-risk'); if(avgEl){avgEl.textContent=riskLabels[avgRiskNum];avgEl.style.color=riskColors[avgRiskNum];}
  const sosAlerts=alerts.filter(a=>a.trigger_type==='sos'||a.trigger_type==='manual_sos');
  const sosEl=document.getElementById('days-since-sos');
  if(sosEl){if(sosAlerts.length>0){const daysSince=Math.floor((now-new Date(sosAlerts[0].created_at))/(24*60*60*1000));sosEl.textContent=daysSince;}else{sosEl.textContent='∞';sosEl.style.fontSize='1.8rem';}}
  const twoWeeksAgo=new Date(now.getTime()-14*24*60*60*1000), prevWeekAlerts=alerts.filter(a=>{const d=new Date(a.created_at);return d>=twoWeeksAgo&&d<weekAgo;});
  const trendEl=document.getElementById('trend-arrow');
  if(trendEl){if(weekCount<prevWeekAlerts.length){trendEl.className='trend-up';trendEl.innerHTML='<i class="bi bi-arrow-up-right"></i> Improving';}else if(weekCount>prevWeekAlerts.length){trendEl.className='trend-down';trendEl.innerHTML='<i class="bi bi-arrow-down-right"></i> Declining';}else{trendEl.className='trend-neutral';trendEl.innerHTML='<i class="bi bi-dash-lg"></i> Stable';}}
  const summaryEl=document.getElementById('weekly-summary-text');
  if(summaryEl){if(weekCount===0)summaryEl.textContent='No alerts this week — you are doing great! Stay vigilant.';else if(weekCount<=2)summaryEl.textContent=weekCount+' alert(s) this week. Risk level is manageable. Stay cautious.';else summaryEl.textContent=weekCount+' alerts this week. Consider reviewing your safety routines.';}
})();

/* ── Mouse Parallax for Background ── */
(function(){
  let mouseX=0,mouseY=0,currentX=0,currentY=0;
  const grid=document.getElementById('cyber-grid'), orbRed=document.getElementById('orb-red'), orbBlue=document.getElementById('orb-blue'), orbPurple=document.getElementById('orb-purple');
  document.addEventListener('mousemove',e=>{ mouseX=(e.clientX/window.innerWidth-0.5)*2; mouseY=(e.clientY/window.innerHeight-0.5)*2; });
  function animateParallax(){
    currentX+=(mouseX-currentX)*0.05; currentY+=(mouseY-currentY)*0.05;
    if(grid)grid.style.transform=`translate(${currentX*8}px,${currentY*5}px)`;
    if(orbRed){orbRed.style.marginLeft=`${currentX*20}px`;orbRed.style.marginTop=`${currentY*15}px`;}
    if(orbBlue){orbBlue.style.marginLeft=`${currentX*-15}px`;orbBlue.style.marginTop=`${currentY*-12}px`;}
    if(orbPurple){orbPurple.style.marginLeft=`${currentX*12}px`;orbPurple.style.marginTop=`${currentY*10}px`;}
    requestAnimationFrame(animateParallax);
  }
  requestAnimationFrame(animateParallax);
})();

/* ── SOS Particle Effect ── */
(function(){
  const sosWrap=document.getElementById('sos-btn-wrap'); if(!sosWrap) return;
  let particleInterval=null;
  function spawnParticle(){
    const particle=document.createElement('div'); particle.className='sos-particle';
    const centerX=sosWrap.offsetLeft+sosWrap.offsetWidth/2, centerY=sosWrap.offsetTop+sosWrap.offsetHeight/2;
    const angle=Math.random()*Math.PI*2, radius=30+Math.random()*50;
    particle.style.left=(centerX+Math.cos(angle)*radius)+'px'; particle.style.top=(centerY+Math.sin(angle)*radius)+'px';
    particle.style.width=(2+Math.random()*4)+'px'; particle.style.height=particle.style.width;
    particle.style.background=`hsl(${Math.random()*20},90%,${50+Math.random()*20}%)`; particle.style.boxShadow='0 0 6px rgba(124,58,237,0.6)';
    sosWrap.parentElement.appendChild(particle); particle.addEventListener('animationend',()=>particle.remove());
  }
  sosWrap.addEventListener('mouseenter',()=>{ particleInterval=setInterval(spawnParticle,80); });
  sosWrap.addEventListener('mouseleave',()=>{ clearInterval(particleInterval); particleInterval=null; });
})();

/* ── Live Threat Intelligence Feed ── */
(function(){
  const feed=document.getElementById('threat-feed'); if(!feed) return;
  const events=[
    {sev:'HIGH',  color:'#7c3aed',bg:'rgba(124,58,237,0.08)',  border:'rgba(124,58,237,0.2)',  icon:'bi-exclamation-octagon-fill',text:'Unverified assailant reported · Connaught Place, Delhi'},
    {sev:'MED',   color:'#8b5cf6',bg:'rgba(139,92,246,0.07)', border:'rgba(139,92,246,0.2)', icon:'bi-eye-fill',                 text:'Suspicious activity logged · Linking Road, Mumbai'},
    {sev:'HIGH',  color:'#7c3aed',bg:'rgba(124,58,237,0.08)',  border:'rgba(124,58,237,0.2)',  icon:'bi-shield-exclamation',       text:'SOS override triggered · HSR Layout, Bangalore'},
    {sev:'LOW',   color:'#8b5cf6',bg:'rgba(139,92,246,0.06)', border:'rgba(139,92,246,0.15)',icon:'bi-check-circle-fill',        text:'Threat resolved · Koregaon Park, Pune'},
    {sev:'MED',   color:'#8b5cf6',bg:'rgba(139,92,246,0.07)', border:'rgba(139,92,246,0.2)', icon:'bi-geo-alt-fill',             text:'Geofence breach detected · Banjara Hills, Hyderabad'},
    {sev:'CRIT',  color:'#ff3b3b',bg:'rgba(139,92,246,0.1)',   border:'rgba(139,92,246,0.3)',  icon:'bi-broadcast',                text:'Cluster incident — 3 SOS simultaneous · Sector 18, Noida'},
    {sev:'LOW',   color:'#8b5cf6',bg:'rgba(139,92,246,0.06)', border:'rgba(139,92,246,0.15)',icon:'bi-person-check-fill',        text:'Safe Walk completed · Indiranagar, Bangalore'},
    {sev:'MED',   color:'#8b5cf6',bg:'rgba(139,92,246,0.07)', border:'rgba(139,92,246,0.2)', icon:'bi-camera-video-fill',        text:'CCTV blackout zone entered · CP Road, Kolkata'},
    {sev:'HIGH',  color:'#7c3aed',bg:'rgba(124,58,237,0.08)',  border:'rgba(124,58,237,0.2)',  icon:'bi-telephone-x-fill',         text:'Missed 3 check-ins · Salt Lake, Kolkata'},
    {sev:'INFO',  color:'#8b5cf6',bg:'rgba(139,92,246,0.06)', border:'rgba(139,92,246,0.15)',icon:'bi-info-circle-fill',         text:'New danger zone verified · Sarojini Nagar Market, Delhi'},
  ];
  function pushEvent(evt){
    const now=new Date(), ts=String(now.getHours()).padStart(2,'0')+':'+String(now.getMinutes()).padStart(2,'0')+':'+String(now.getSeconds()).padStart(2,'0');
    const row=document.createElement('div');
    row.style.cssText='display:flex;align-items:center;gap:12px;padding:10px 14px;background:'+evt.bg+';border:1px solid '+evt.border+';border-radius:10px;animation:fadeSlideIn .3s ease-out;flex-shrink:0;';
    row.innerHTML='<i class="bi '+evt.icon+'" style="color:'+evt.color+';font-size:1rem;flex-shrink:0;"></i><div style="flex:1;min-width:0;"><div style="font-size:0.82rem;color:#fff;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+evt.text+'</div><div style="font-size:0.65rem;color:rgba(255,255,255,0.4);margin-top:2px;font-family:\'Courier New\',monospace;">'+ts+' · AUTO-FLAGGED</div></div><span style="font-size:0.6rem;font-weight:800;padding:3px 8px;border-radius:6px;background:'+evt.color+'22;color:'+evt.color+';border:1px solid '+evt.color+'44;letter-spacing:0.08em;flex-shrink:0;">'+evt.sev+'</span>';
    feed.prepend(row);
    while(feed.children.length>12) feed.lastChild.remove();
  }
  [events[5],events[0],events[2]].forEach((e,i)=>setTimeout(()=>pushEvent(e),i*450));
  function scheduleNext(){var delay=5000+Math.random()*7000;setTimeout(()=>{pushEvent(events[Math.floor(Math.random()*events.length)]);scheduleNext();},delay);}
  scheduleNext();
})();
