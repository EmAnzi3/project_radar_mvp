import argparse,json,re
from pathlib import Path
def rank(row):
    title=(row.get('title','')+' '+row.get('filename','')).lower()
    priorities=['cronoprogramma','cantierizzazione','computo metrico','relazione generale','opere elettriche','cavidotto','fondazion','prescrizion','parere']
    return min([i for i,s in enumerate(priorities) if s in title] or [20])
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--inventory',required=True);p.add_argument('--old',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    index=json.loads(Path(a.inventory).read_text())
    previous=json.loads(Path(a.old).read_text())
    seen={r['url'] for r in previous['sources']}
    candidate={}
    for section in index['procedures']:
        if not section['complete']:continue
        for r in section['rows']:
            if r['url'] not in seen:candidate.setdefault(r['url'],dict(r,procedure=section['id']))
    recent=[r for r in candidate.values() if r['procedure']!='10237']
    old=[r for r in candidate.values() if r['procedure']=='10237']
    chosen=(sorted(recent,key=rank)+sorted(old,key=rank))[:24]
    result={'project_id':'serra-giannina','scope_note':'Second batch of inventory-backed new sources; not full dossier',
            'allowed_hosts':['va.mite.gov.it','va.mase.gov.it'],'link_depth':0,
            'sources':[{'url':r['url'],'title':r['title'],'scope':'project_document','expected':'pdf'} for r in chosen]}
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('Selected',len(chosen),'from',len(candidate),'new indexed URLs')
    if len(chosen)!=24:raise SystemExit('Expected exactly 24 new candidates')
if __name__=='__main__':main()
