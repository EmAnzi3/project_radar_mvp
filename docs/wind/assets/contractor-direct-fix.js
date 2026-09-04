(()=>{'use strict';
const $=s=>document.querySelector(s), all=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const fmt=v=>new Intl.NumberFormat('it-IT',{maximumFractionDigits:1}).format(+v||0);
let projects=[],meta={},chosen='',writing=false;
function conf(c){return `<span class="confidence ${esc(c)}">${esc(c)}</span>`}
function strictRel(r){return (meta.execution_roles||[]).includes(r.role)&&r.status==='confirmed'&&['A1','A2'].includes(r.confidence)}
async function load(){
  const m=await fetch('data/projects.json',{cache:'no-store'}).then(r=>r.json());
  const [mm,...chunks]=await Promise.all([fetch('data/'+m.meta,{cache:'no-store'}).then(r=>r.json()),...m.chunks.map(x=>fetch('data/'+x,{cache:'no-store'}).then(r=>r.json()))]);
  meta=mm;projects=chunks.flat();
}
function currentProjects(){
  const ids=new Set(all('#opportunityRows [data-project-id]').map(x=>x.dataset.projectId));
  return ids.size?projects.filter(p=>ids.has(p.id)):projects;
}
function companyNames(ps){return [...new Set(ps.flatMap(p=>(p.relations||[]).map(r=>r.company)).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'it',{sensitivity:'base'}))}
function ensureSelect(names){
  const old=$('#contractorQ'); if(old){old.value='';old.setAttribute('autocomplete','off')}
  let sel=$('#contractorFocus');
  if(!sel&&old){const label=old.closest('label'); const cap=label?.querySelector('span'); if(cap)cap.textContent='Approfondisci azienda'; sel=document.createElement('select');sel.id='contractorFocus';label?.appendChild(sel)}
  if(!sel)return null;
  if(!chosen||!names.includes(chosen))chosen=names[0]||'';
  const existing=[...sel.options].map(o=>o.value);
  if(existing.length!==names.length||existing.some((v,i)=>v!==names[i])){sel.replaceChildren(...names.map(n=>new Option(n,n)))}
  sel.value=chosen;
  if(!sel.dataset.directBound){sel.dataset.directBound='1';sel.addEventListener('change',()=>{chosen=sel.value;renderDirect()})}
  return sel;
}
function renderDirect(){
  const view=$('#contractorView'),sum=$('#contractorSummary'); if(!view||!sum||!projects.length)return;
  const ps=currentProjects(),names=companyNames(ps);ensureSelect(names);
  if(!chosen){view.innerHTML='<div class="contractor-empty">Nessuna azienda disponibile nel filtro.</div>';return}
  const rows=[]; const roles=new Set(); const linked=new Map();
  ps.forEach(p=>{const rels=(p.relations||[]).filter(r=>r.company===chosen);if(!rels.length)return;rels.forEach(r=>roles.add(r.role));linked.set(p.id,{p,rels})});
  const linkedProjects=[...linked.values()].sort((a,b)=>(b.p.score||0)-(a.p.score||0));
  const total=linkedProjects.reduce((s,x)=>s+(+x.p.mw||0),0);
  const strictCompanies=new Set();ps.forEach(p=>(p.relations||[]).forEach(r=>{if(strictRel(r))strictCompanies.add(r.company)}));
  const linkedProjectCount=new Set(ps.flatMap(p=>(p.relations||[]).length?[p.id]:[])).size;
  sum.innerHTML=`<span class="summary-chip"><b>${names.length}</b> aziende/nodi nel filtro</span><span class="summary-chip"><b>${strictCompanies.size}</b> con scope esecutivo A1/A2</span><span class="summary-chip"><b>${linkedProjectCount}</b> progetti collegati</span>`;
  linkedProjects.forEach(({p,rels})=>{const rr=rels.map(r=>`${esc(r.role)} · ${esc(r.status||'n.d.')} · ${conf(r.confidence||'D')}`).join('<br>');rows.push(`<div class="contractor-project" data-direct-project="${esc(p.id)}"><div><b>${esc(p.name)}</b><small>${rr}<br>${esc(p.stage)} · next ${esc(p.next?.label||'n.d.')}</small></div><span class="project-mw">${fmt(p.mw)} MW</span></div>`)});
  writing=true;
  view.innerHTML=`<article class="contractor-card review-selected direct-contractor-card"><div class="contractor-card-head"><h3>${esc(chosen)}</h3><div class="contractor-metric"><b>${fmt(total)}</b><span>MW collegati · ${linkedProjects.length} progetti</span></div></div><div class="contractor-roles">${[...roles].sort((a,b)=>a.localeCompare(b,'it')).map(r=>`<span class="role-pill">${esc(r)}</span>`).join('')}</div>${rows.join('')||'<div class="contractor-empty">Nessun progetto collegato nel filtro corrente.</div>'}</article>`;
  view.querySelectorAll('[data-direct-project]').forEach(x=>x.onclick=()=>{const id=x.dataset.directProject;const target=document.querySelector(`#opportunityRows [data-project-id="${CSS.escape(id)}"]`)||document.querySelector(`#mapMarkers [data-id="${CSS.escape(id)}"]`);target?.click()});
  writing=false;
}
function schedule(){clearTimeout(schedule.t);schedule.t=setTimeout(renderDirect,30)}
function initObservers(){
 const view=$('#contractorView'),opp=$('#opportunityRows');
 if(view)new MutationObserver(()=>{if(writing)return;if(!view.querySelector('.direct-contractor-card'))schedule()}).observe(view,{childList:true,subtree:true});
 if(opp)new MutationObserver(schedule).observe(opp,{childList:true,subtree:true});
 ['region','stage','type','developer','contractor','mwMin','mwMax','window','q','resetFilters'].forEach(id=>document.getElementById(id)?.addEventListener(id==='resetFilters'?'click':'change',schedule));
}
async function init(){try{await load();initObservers();setTimeout(renderDirect,120)}catch(err){console.error('contractor direct view init failed',err)}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
