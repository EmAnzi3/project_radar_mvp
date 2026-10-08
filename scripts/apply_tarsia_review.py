"""Materialize the reviewed Tarsia data; no remote access or branch updates.
Repeated runs reuse the same interpretation. Base guards reject newer input.
"""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(record):
 return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def write(path,text):
 path.write_text(text,encoding='utf-8',newline='\n')

def apply(root=ROOT):
 review=json.loads((root/'config/wind_tarsia_review.json').read_text(encoding='utf-8'))
 path=root/'docs/wind/data/projects-2.json';rows=json.loads(path.read_text(encoding='utf-8'))
 before=copy.deepcopy(rows);matches=[p for p in rows if p['id']==review['project_id']]
 if len(matches)!=1:raise ValueError('Expected one target project')
 p=matches[0]
 if p.get('documentary')!=review['documentary']:
  if sha(p)!=review['expected_base_record_sha256']:raise ValueError('Project changed since review: reconcile, do not overwrite')
  p['site_type']='onshore';p['status_note']=review['status_note']
  p['next']['label']='SSE MT/AT: obiettivo 2026 dichiarato da PLC; consuntivo da verificare'
  p['timing'][0]['label']='Avvio costruzione annunciato da Plenitude';p['timing'][0]['confidence']='A2'
  p['timing'][1]['label']='SSE MT/AT: previsione PLC per il 2026, non data certa di entrata in esercizio'
  for r in p['relations']:
   if r['company']=='Delta Costruzioni':
    r['company']='Delta S.r.l.'
    r['scope']='Denominazione letterale del comunicato PLC; identità societaria e recapiti da verificare. Nessuna equivalenza automatica con Delta Costruzioni.'
  p['sources'].extend(review['sources']);p['documentary']=review['documentary']
  assert [x for x in before if x['id']!=p['id']]==[x for x in rows if x['id']!=p['id']]
  write(path,json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 if review.get('institutional_update_version'):
  oldsource=next((s for s in p['sources'] if s['id']=='tars-reg-old'),None)
  if oldsource is None:raise ValueError('Missing Tarsia historic PAUR')
  oldsource['url']='https://www.regione.calabria.it/wp-content/uploads/2023/03/360_parco-eolico-tarsia-ovest-ddg-3509-del-13_03_2023.pdf'
  oldsource['title']='DDG 3509/2023 – PAUR limitato a T1, T5 e T6 (non a tutti e sette i WTG originari)'
  historic=next((x for x in p['configs'] if x['source_id']=='tars-reg-old'),None)
  if historic is None:raise ValueError('Missing historic configuration')
  historic['note']="Istanza iniziale 7 aerogeneratori / 29,995 MW: il PAUR DDG 3509/2023 autorizza soltanto T1, T5 e T6. Non usare 29,995 MW come potenza dell'impianto autorizzato."
  if not any(x.get('source_id')=='tars-reg-variante-2026' for x in p['configs']):
   p['configs'].insert(0,{'date':'2026-04-20','wind_mw':12.9,'bess_mw':0,'wtg_count':3,'wtg_mw':4.3,'note':'Variante VPA regionale: 3 Vestas V150-4.3 (T1,T5,T6), modifica di opere di connessione e viabilità; nessun COD attestato.','source_id':'tars-reg-variante-2026'})
  if [x for x in before if x['id']!=p['id']] != [x for x in rows if x['id']!=p['id']]:raise ValueError('Non-target mutation')
  write(path,json.dumps(rows,ensure_ascii=False,indent=2)+'\\n')
 path=root/'docs/wind/assets/app.js';s=path.read_text(encoding='utf-8')
 expression="${window.WindDocumentary?.render(p)||''}"
 if expression not in s:
  # Text-mode LF normalization handles Windows checkout without weakening the content guard.
  if hashlib.sha256(s.encode('utf-8')).hexdigest()!='e5828d05ccdbf593ccd8f422989487e770427d918901e0e5162681d30050c99a':raise ValueError('Renderer base changed')
  anchor='<section class="detail-section"><h3>Timeline</h3>'
  assert s.count(anchor)==1;s=s.replace(anchor,expression+anchor);write(path,s)
 path=root/'docs/wind/index.html';s=path.read_text(encoding='utf-8')
 if 'assets/documentary-summary.js' not in s:
  s=s.replace('<script src="assets/app.js"></script>','<script src="assets/documentary-summary.js"></script><script src="assets/app.js"></script>')
  s=s.replace('</head>','<link rel="stylesheet" href="assets/documentary-summary.css">\n</head>');write(path,s)
 path=root/'scripts/harvest_wind_project.py';s=path.read_text(encoding='utf-8')
 if 'unrelated_footer' not in s:
  anchor="        relevant = bool(re.search(r'tarsia', url + ' ' + title, re.I))"
  assert s.count(anchor)==1
  s=s.replace(anchor,anchor+"\n        unrelated_footer = bool(re.search(r'bilancio|sostenibil|slavery|modello.?231|policy|codice.etico|privacy|cookie', url + ' ' + title, re.I))\n        if unrelated_footer: continue")
  s=s.replace("'previous_good_copy_retained': valid_old}","'previous_good_copy_retained': valid_old, 'last_access_error': str(exc)[:400]}")
  s=s.replace("    return {'kind': kind, 'text': text, 'links': parser.links,", "    return {'kind': kind, 'text': text, 'links': parser.links,\n            'dynamic_content_review_needed': len(re.sub(r'\\s+', ' ', text).strip()) < 100,")
  write(path,s)
 path=root/'config/wind_tarsia_pilot.json';c=json.loads(path.read_text(encoding='utf-8'))
 for entry in c['sources']:
  if entry['scope']=='project_index':
   entry['url']='https://www.regione.calabria.it/provvedimenti-della-regione/?filter_item=Tarsia&sort_order=0'
   entry['title']='Registro Calabria: filtro oggetto Tarsia dal modulo pubblico; non indice completo certificato'
 write(path,json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 for name,heading in [('CURRENT_STATE.md','# Current State'),('CHANGELOG.md','## Unreleased')]:
  path=root/name;s=path.read_text(encoding='utf-8-sig')
  if 'Tarsia pilot 2026-10-06' not in s:
   note='\n\n### Tarsia pilot 2026-10-06\n\nTest isolato dal master, senza integrare la Draft PR #9. Raccolta iniziale eseguita, ma includeva cinque PDF aziendali estranei: filtro corretto senza dichiararli letti. Scheda commerciale Tarsia materializzata con contatti pubblici, cronologia qualificata e Delta S.r.l. come nella fonte PLC. Un comunicato PDF acquisito e letto; tre fonti HTML usate mediante lettore web di riserva, con provenienza distinta e senza falso hash originale. OneDrive non collegato: copia/sincronizzazione cloud NON eseguita. Nessun altro progetto modificato; numero e MW invariati. Nessuna API a pagamento. Pubblicazione da verificare dopo merge mirato.\n'
   if heading not in s:raise ValueError('Missing maintenance heading')
   write(path,s.replace(heading,heading+note,1))
 return {'project_id':p['id'],'wind_mw':p['mw'],'contacts':len(p['documentary']['contacts']),'other_projects_changed':0,'paid_model_calls':0}

if __name__=='__main__':print(json.dumps(apply()))
