#!/usr/bin/env python3
"""Materialize verified Serra Giannina documentary enrichment, with no network or publication."""
import copy, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def apply(root=ROOT):
    root=Path(root)
    review=json.loads((root/'config/wind_serra_review.json').read_text(encoding='utf-8'))
    path=root/'docs/wind/data/projects-1.json'
    records=json.loads(path.read_text(encoding='utf-8'))
    before=copy.deepcopy(records)
    matches=[p for p in records if p['id']==review['project_id']]
    if len(matches)!=1:raise ValueError('Unexpected Serra Giannina identity')
    p=matches[0]
    expected=review['base_expected']
    for k in ('mw','wtg','stage','name'):
        if p[k]!=expected[k]:raise ValueError('Serra baseline changed; manual reconciliation needed')
    if p.get('documentary')==review['documentary']:
        return {'project_id':p['id'],'reused_without_writes':True}
    if p.get('documentary'):
        sha=hashlib.sha256(json.dumps(p['documentary'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if sha != review.get('previous_documentary_sha256'):
            raise ValueError('Newer documentary review exists; do not overwrite')
        # An incremental review may add evidence, never silently replace a source.
        existing={s['id']:s for s in p['sources']}
        if len(existing)!=len(p['sources']):raise ValueError('Duplicate existing source ID')
        for s in review['sources_added']:
            if s['id'] in existing:
                if existing[s['id']]!=s:raise ValueError('Existing source changed')
            else:p['sources'].append(s)
        # Retain the Company Network key; legal name stays in company_registry.
        for rel in p['relations']:
            if rel['company']=='EGM Project S.r.l.':rel['company']='EGM Project'
        p['documentary']=review['documentary']
        path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return {'project_id':p['id'],'incremental_review':True,'other_projects_changed':0,'paid_model_calls':0}
    gantt=next((s for s in p['sources'] if s['id']=='sg-plan'),None)
    if not gantt or gantt['url']:raise ValueError('Existing BoP schedule has changed')
    gantt['url']=review['changed_source']['sg-plan']
    gantt['publisher']='MASE / cronoprogramma BoP Serra Giannina (6 WTG)'
    seen={s['id'] for s in p['sources']}
    for s in review['sources_added']:
        if s['id'] in seen:raise ValueError('Duplicate evidence source')
        seen.add(s['id']);p['sources'].append(s)
    rel=next((r for r in p['relations'] if r['company']=='EGM Project'),None)
    if rel is None or rel['status']!='signal':raise ValueError('Expected engineering lead missing')
    rel.update(review['relation_update'])
    p['relations'].append(review['relation_added'])
    p['status_note']=review['status_note']
    for i,k in enumerate(('site','civil','cod')):
        if p['timing'][i]['phase']!=k:raise ValueError('Unexpected timing order')
        p['timing'][i]['label']=review['phase_labels'][k]
    p['timing'][0]['confidence']='A2'
    p['next']['label']=review['next_label']
    p['documentary']=review['documentary']
    if [r for r in before if r['id']!=p['id']] != [r for r in records if r['id']!=p['id']]:
        raise ValueError('Non-target project changed')
    path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'project_id':p['id'],'added_sources':len(review['sources_added']),
            'company_registry':len(p['documentary']['company_registry']),
            'other_projects_changed':0,'paid_model_calls':0}

if __name__=='__main__':
    print(json.dumps(apply()))
