"""Materialize one reviewed project and a conditional renderer, with a base guard.
No remote requests, model calls, branch updates or publication. Repeated runs
reuse exactly the same reviewed source. Unrelated project values cannot change.
"""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(record):
 return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

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
  path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 path=root/'docs/wind/assets/app.js';s=path.read_text(encoding='utf-8')
 expression="${window.WindDocumentary?.render(p)||''}"
 if expression not in s:
  if hashlib.sha256(path.read_bytes()).hexdigest()!='e5828d05ccdbf593ccd8f422989487e770427d918901e0e5162681d30050c99a':raise ValueError('Renderer base changed')
  anchor='<section class="detail-section"><h3>Timeline</h3>'
  assert s.count(anchor)==1;s=s.replace(anchor,expression+anchor);path.write_text(s,encoding='utf-8')
 path=root/'docs/wind/index.html';s=path.read_text(encoding='utf-8')
 if 'assets/documentary-summary.js' not in s:
  s=s.replace('<script src="assets/app.js"></script>','<script src="assets/documentary-summary.js"></script><script src="assets/app.js"></script>')
  s=s.replace('</head>','<link rel="stylesheet" href="assets/documentary-summary.css">\n</head>');path.write_text(s,encoding='utf-8')
 return {'project_id':p['id'],'wind_mw':p['mw'],'contacts':len(p['documentary']['contacts']),'other_projects_changed':0,'paid_model_calls':0}

if __name__=='__main__':print(json.dumps(apply()))
