"""Materialize the single-project institutional review; no network or AI calls.

Source JSON is the editorial input. This script updates only Tarsia and keeps
all missing-document and partial-reading qualifications visible to readers.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='ae0c8b5cd54bfea33b10337204535ac003f6014ba99a9afbfabef3102d9311be'

def fingerprint(value):
 return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def run(root=ROOT):
 raw=json.loads((root/'config/tarsia_closeout_update.json').read_text(encoding='utf-8'))
 path=root/'docs/wind/data/projects-2.json';records=json.loads(path.read_text(encoding='utf-8'))
 before=copy.deepcopy(records);matches=[r for r in records if r['id']==raw['project_id']]
 if len(matches)!=1:raise ValueError('Expected exactly one Tarsia record')
 target=matches[0];revision=fingerprint(raw)
 if target.get('documentary',{}).get('institutional_revision')!=revision:
  if fingerprint(target)!=BASE:raise ValueError('Tarsia changed after review: reconcile rather than overwrite')
  doc=copy.deepcopy(target['documentary'])
  doc['fields']=copy.deepcopy(raw['fields'])
  vat_text='; '.join(x['company']+': P.IVA '+x['vat']+((' (C.F. '+x['fiscal_code']+')') if x.get('fiscal_code') and x['fiscal_code']!=x['vat'] else '')+' — '+x['role'] for x in raw['company_identifiers'])
  doc['fields'].append({'label':'P.IVA aziende','value':vat_text+'. Delta e identita Mammana: non attribuite senza conferma.','source_ids':['tars-voltura','tars-plc-soa','tars-idoka-contact','tars-plc-sales','tars-archive']})
  doc['company_identifiers']=copy.deepcopy(raw['company_identifiers'])
  doc['gaps']=copy.deepcopy(raw['gaps'])
  doc['method']='Analisi commerciale mirata di atti regionali, elaborati storici pertinenti e fonti aziendali. Archivio acquisito e indicizzato; non certificazione della lettura integrale di tutti i documenti o dell\'intero fascicolo corrente.'
  doc['reviewed_on']=raw['reviewed_on'];doc['whole_dossier_complete']=False
  doc['institutional_revision']=revision;doc['archive_receipt']=copy.deepcopy(raw['archive_receipt'])
  for source in raw['regional_sources']:
   if source.get('pages'):
    doc['evidence'].append({'source_id':source['id'],'sha256':source['sha256'],'pages':source['reviewed_pages'],'capture':'harvester_original','reading':'targeted_text_and_visual','whole_document_read':False})
  doc['evidence'].append(copy.deepcopy(raw['cronoprogramma_evidence']))
  target['documentary']=doc;target['status_note']=raw['status_note']
  sources={x['id']:x for x in target['sources']}
  sources.update({s['id']:{k:v for k,v in s.items() if k in ('id','title','publisher','date','url','grade')} for s in raw['regional_sources']})
  target['sources']=list(sources.values())
  configs=[copy.deepcopy(c) for c in target['configs'] if c.get('source_id')!='tars-reg-old']
  configs.extend([
   {'date':'2020-06-18','wind_mw':29.995,'wtg_count':7,'note':'Proposta iniziale storica: non configurazione autorizzata dal PAUR.','source_id':'tars-sia'},
   {'date':'2023-03-13','wtg_count':3,'note':'PAUR limitato a T1, T5 e T6; escluse le altre quattro turbine inizialmente proposte.','source_id':'tars-reg-old'},
   {'date':'2026-04-20','wind_mw':12.9,'wtg_count':3,'wtg_mw':4.3,'note':'VPA della variante: Vestas V150; modello progettuale, non prova di ordine OEM.','source_id':'tars-variante'}])
  target['configs']=configs
  assert [r for r in before if r['id']!=target['id']]==[r for r in records if r['id']!=target['id']]
  assert target['mw']==12.9 and target['wtg']==3
  write(path,records)
 # Keep legacy reviewed input aligned so its idempotent regeneration is a no-op.
 p=root/'config/wind_tarsia_review.json';review=json.loads(p.read_text(encoding='utf-8'))
 review['documentary']=copy.deepcopy(target['documentary']);review['status_note']=target['status_note']
 review['sources']=copy.deepcopy(target['sources']);review['expected_base_record_sha256']=BASE
 review['configs']=copy.deepcopy(target['configs']);write(p,review)
 receipt={'project_id':raw['project_id'],'reviewed_on':raw['reviewed_on'],'regional_documents':[{k:s.get(k) for k in ('id','url','sha256','pages','reviewed_pages')} for s in raw['regional_sources'] if s.get('pages')], 'archive':raw['archive_receipt'],'cronoprogramma':raw['cronoprogramma_evidence'],'gaps':raw['gaps'],'human_action':raw['human_action'],'all_documentation_complete':False,'paid_model_calls':0}
 write(root/'docs/wind/research/tarsia-institutional-access.json',receipt)
 for name,heading in [('CURRENT_STATE.md','# Current State'),('CHANGELOG.md','## Unreleased')]:
  p=root/name;text=p.read_text(encoding='utf-8-sig')
  marker='Tarsia institutional review 2026-10-06'
  if marker not in text:
   note='\n\n### '+marker+'\n\nSingle-project enrichment: six original regional PDFs, corporate VAT evidence and the 2.9 GB historic archive recovered. 435 outer members plus 174 nested members; 335 distinct PDF payloads / 3,064 native-text pages. These are extraction counts, not whole-document reading counts. Current SUAP698CS technical attachments, execution schedule, ambiguous RTI identities and damaged historic annexes remain explicit gaps. Historical Gantt24months conflicts with SIA/PAUR14months; no current COD inferred. VAT and fiscal code kept separate for PLC System. No paid model calls, no OneDrive requirement, no other project changes, no PR9 merge.\n'
   if heading not in text:raise ValueError('Missing maintenance heading')
   p.write_text(text.replace(heading,heading+note,1),encoding='utf-8',newline='\n')
 return {'project_id':target['id'],'revision':revision,'other_records_changed':0,'vat_records':len(raw['company_identifiers']),'complete_dossier':False}

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False))
