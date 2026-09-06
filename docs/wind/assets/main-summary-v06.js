(()=>{'use strict';
const $=s=>document.querySelector(s);
function trimDiscoveryPromotedChip(){const box=$('#discoverySummary');if(!box)return;[...box.children].forEach(el=>{if((el.textContent||'').includes('già promossi nel Radar'))el.remove()})}
function installDiscoveryGuard(){const box=$('#discoverySummary');if(!box)return;trimDiscoveryPromotedChip();new MutationObserver(trimDiscoveryPromotedChip).observe(box,{childList:true,subtree:true})}
function addMethodCoverage(){const body=$('#methodBody');if(!body||body.querySelector('.method-coverage'))return;const div=document.createElement('div');div.className='method-coverage';div.innerHTML='<h3>Copertura del motore di intelligence</h3><p>Questi registri alimentano ricerca e monitoraggio, ma non sono una vista operativa principale.</p><div class="method-coverage-grid"><span><b>61</b> player commerciali monitorati</span><span><b>31</b> nodi fonte istituzionali/pubblici</span><span><b>21</b> adapter istituzionali eseguibili</span></div><small>Player &amp; Network Watch e Institutional &amp; Source Watch restano nella metodologia: capability, membership o presenza in una fonte non equivalgono a un award di progetto.</small>';body.appendChild(div)}
function init(){installDiscoveryGuard();$('#openMethod')?.addEventListener('click',()=>setTimeout(addMethodCoverage,0))}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
