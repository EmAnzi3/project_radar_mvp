(()=>{'use strict';
const $=s=>document.querySelector(s),all=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
let overlay={},byName=new Map(),body=null,timer=null;
async function load(){
  const manifest=await fetch('data/projects.json',{cache:'no-store'}).then(r=>r.json());
  const chunks=await Promise.all(manifest.chunks.map(x=>fetch('data/'+x,{cache:'no-store'}).then(r=>r.json())));
  byName=new Map(chunks.flat().map(p=>[p.name,p.id]));
  overlay=await fetch('data/enrichment-docpass2-2026-09-04.json',{cache:'no-store'}).then(r=>r.json());
}
function docCard(d){return `<div class="doc2-card"><div><b>${esc(d.title)}</b><span>${esc(d.note||'')}</span></div><span class="doc-status ${esc(d.status||'')}">${esc(d.status||'')}</span></div>`}
function relationCard(r){return `<div class="doc2-rel"><div><b>${esc(r.company)}</b><span>${esc(r.role)} · ${esc(r.scope||'')}</span></div><span class="confidence ${esc(r.confidence||'D')}">${esc(r.confidence||'D')}</span></div>`}
function schedule(intel){
 const s=intel.schedule_intelligence;if(!s)return'';
 const items=(s.items||[]).map(x=>`<div class="doc2-schedule-row"><span>${esc(x.label)}</span><b>${esc(x.when)}</b></div>`).join('');
 return `<h4>Schedule intelligence</h4><div class="doc2-note">${esc(s.note||'')}</div><div class="doc2-schedule">${items}</div>`;
}
function publicSources(intel){
 const a=intel.public_sources||[];if(!a.length)return'';
 return `<h4>Fonti pubbliche territoriali</h4><div class="doc2-public">${a.map(x=>`<div class="doc2-public-row"><span class="doc2-level">${esc(x.level)}</span><div><b>${esc(x.entity)}</b><span>${esc(x.use||'')}</span>${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">Apri fonte</a>`:''}</div></div>`).join('')}</div>`;
}
function inject(){
 if(!body)return;
 const old=body.querySelector('.docpass2-section'); if(old)old.remove();
 const name=$('#detailTitle')?.textContent.trim(),id=byName.get(name),intel=id?overlay.projects?.[id]:null;
 if(!intel)return;
 const docs=(intel.documents||[]).map(docCard).join('');
 const rels=(intel.relations||[]).map(relationCard).join('');
 const html=`<section class="detail-section docpass2-section"><h3>Deep document & public-source pass</h3>${docs?`<h4>Documenti acquisiti</h4><div class="doc2-list">${docs}</div>`:''}${rels?`<h4>Soggetti tecnici emersi</h4><div class="doc2-list">${rels}</div>`:''}${schedule(intel)}${publicSources(intel)}</section>`;
 const scope=body.querySelector('.scope-intel-section');
 if(scope)scope.insertAdjacentHTML('afterend',html); else body.insertAdjacentHTML('afterbegin',html);
}
function scheduleInject(){clearTimeout(timer);timer=setTimeout(inject,60)}
async function init(){
 try{
   await load();body=$('#detailBody');if(!body)return;
   new MutationObserver(scheduleInject).observe(body,{childList:true,subtree:true});
   $('#drawer')&&new MutationObserver(scheduleInject).observe($('#drawer'),{attributes:true,attributeFilter:['class','aria-hidden']});
   scheduleInject();
 }catch(err){console.error('docpass2 intelligence init failed',err)}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();