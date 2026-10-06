"""Read an acquired Tarsia ZIP without network or paid AI calls.
CMS extraction is not signature validation. Native screening is not semantic review.
"""
from __future__ import annotations
import argparse, gc, hashlib, json, re, shutil, subprocess, tempfile, time, zipfile
from pathlib import Path
import fitz

FIELDS={'identity_power':r'Tarsia|\bMW\b|\bkW\b|aerogenerator','location':r'localizz|coordinate|\bUTM\b|Comune di|superficie','schedule':r'cronoprogram|\bmesi\b|inizio lavori|fine lavori|commissioning','companies':r'proponente|committente|progettaz|GEMSA|Vestas|affidat|appalt|impresa esecutrice','contacts_ids':r'partita\s*iva|P\.?\s*IVA|P\.\s*I\.|codice fiscale|\bC\.F\.|@|telefono|Tel\.','useful_works':r'fondazion|viabilit|terre armate|piazzol|cavidott|sottostazion'}
CORE=re.compile(r'cronop|PET[-_ ]P[-_ ]CL[-_ ]02|PET[-_ ](?:P[-_ ])?G[-_ ]0[01](?:_|\b)|PET[-_ ]E[-_ ]0?1(?:_|\b)',re.I)

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def unwrap(path,scratch):
 chain=[];current=Path(path)
 for n in range(16):
  with current.open('rb') as f:prefix=f.read(32)
  if prefix.lstrip().startswith(b'%PDF-'):return current,chain,'pdf'
  if not (prefix.startswith(b'0') or prefix.startswith(b'-----BEGIN')):return current,chain,'other'
  output=Path(scratch)/f'cms-{n}.payload'
  command=['openssl','cms','-verify','-noverify','-nosigs','-inform','PEM' if prefix.startswith(b'-----') else 'DER','-in',str(current),'-out',str(output)]
  result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
  if result.returncode:raise ValueError('CMS payload extraction failed: '+result.stderr.decode(errors='replace')[-300:])
  if not output.exists() or not output.stat().st_size:raise ValueError('Empty CMS payload')
  chain.append({'wrapper_sha256':sha(current),'payload_sha256':sha(output),'signature_validated':False});current=output
 raise ValueError('Nested CMS limit reached; not marked processed')

def run(source,output):
 source,output=Path(source),Path(output);output.mkdir(parents=True,exist_ok=True)
 for name in ('text','core-originals','covers'):(output/name).mkdir(exist_ok=True)
 fitz.TOOLS.mupdf_display_errors(False);fitz.TOOLS.mupdf_display_warnings(False)
 report={'archive_url':'https://www.regione.calabria.it/website/conferenzeservizi/ambiente_territorio/files/PAURTarsiaovest.zip','archive_sha256':sha(source),'archive_bytes':source.stat().st_size,'source_run':37523274647,'network_calls':0,'paid_model_calls':0,'signature_validity_certified':False,'all_project_dossier_complete':False,'semantic_analysis_complete':False,'members':[],'payloads':{}}
 patterns={k:re.compile(v,re.I) for k,v in FIELDS.items()};start=time.monotonic()
 def save():
  report['counts']={'members_processed':len(report['members']),'unique_member_bytes':len({r.get('sha256') for r in report['members'] if r.get('sha256')}),'unique_pdf_payloads':sum(p.get('kind')=='pdf' for p in report['payloads'].values()),'unique_pdf_pages':sum(p.get('page_count',0) for p in report['payloads'].values()),'member_errors':sum(r.get('status')=='processing_failed' for r in report['members']),'content_reuses':sum(r.get('payload_reused',False) for r in report['members']),'members_with_cms':sum(bool(r.get('cms_chain')) for r in report['members'])}
  temp=output/'manifest.tmp';temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(output/'manifest.json')
 with zipfile.ZipFile(source) as z:
  items=[i for i in z.infolist() if not i.is_dir()]
  if len(items)>10000 or sum(i.file_size for i in items)>12*1024**3:raise ValueError('Archive expansion requires explicit larger budget')
  report['expected_members']=len(items);report['inventory']=[{'name':i.filename,'size':i.file_size} for i in items];save();member_reuse={}
  for index,info in enumerate(items):
   row={'name':info.filename,'bytes':info.file_size,'semantic_status':'pending'}
   try:
    if info.flag_bits&1:raise ValueError('Encrypted ZIP member')
    if info.file_size>1024**3:raise ValueError('Member exceeds 1 GiB read budget')
    with tempfile.TemporaryDirectory() as tmp:
     path=Path(tmp)/'original';digest=hashlib.sha256();count=0
     with z.open(info) as a,path.open('wb') as b:
      for block in iter(lambda:a.read(1048576),b''):count+=len(block);digest.update(block);b.write(block)
     if count!=info.file_size:raise ValueError('Truncated ZIP member')
     h=digest.hexdigest();row.update(sha256=h,crc_verified=True)
     if h in member_reuse:row.update(member_reuse[h]);row['payload_reused']=True
     else:
      payload,chain,kind=unwrap(path,tmp);ph=sha(payload);row.update(payload_sha256=ph,cms_chain=chain,kind=kind,payload_reused=ph in report['payloads'])
      if ph not in report['payloads']:
       pack={'sha256':ph,'kind':kind,'bytes':payload.stat().st_size,'first_member':info.filename,'semantic_status':'pending'}
       if kind=='pdf':
        doc=fitz.open(payload)
        if doc.is_encrypted or not len(doc):raise ValueError('Unreadable/encrypted/empty PDF')
        pages=[];packets=[]
        for n,page in enumerate(doc,1):
         text=page.get_text();hits={k:[] for k in patterns}
         for k,pattern in patterns.items():
          for match in list(pattern.finditer(text))[:12]:hits[k].append(re.sub(r'\s+',' ',text[max(0,match.start()-150):match.end()+230]))
         hits={k:v for k,v in hits.items() if v};pages.append({'page':n,'text':text,'needs_visual':len(text.strip())<80})
         if hits:packets.append({'page':n,'fields':hits})
        pack.update(page_count=len(pages),low_text_pages=[p['page'] for p in pages if p['needs_visual']],text_file='text/'+ph+'.json',screening=packets)
        (output/pack['text_file']).write_text(json.dumps({'name':info.filename,'sha256':ph,'pages':pages},ensure_ascii=False),encoding='utf-8')
        page=doc[0];scale=min(1.4,1600/max(page.rect.width,page.rect.height));page.get_pixmap(matrix=fitz.Matrix(scale,scale)).save(str(output/'covers'/(ph+'.png')))
        doc.close();fitz.TOOLS.store_shrink(100)
       report['payloads'][ph]=pack
      if kind=='pdf' and CORE.search(info.filename):
       target=output/'core-originals'/(ph+'.pdf')
       if not target.exists():shutil.copyfile(payload,target)
       report['payloads'][ph]['original_file']='core-originals/'+ph+'.pdf'
      row['status']='content_processed';member_reuse[h]={k:row[k] for k in ('payload_sha256','cms_chain','kind','status')}
   except Exception as exc:row.update(status='processing_failed',error=str(exc)[:600])
   report['members'].append(row)
   if index%10==0 or index+1==len(items):save();print(json.dumps({'processed':index+1,'expected':len(items),'errors':report['counts']['member_errors']}),flush=True)
   gc.collect()
 report['inventory_complete_for_this_zip']=len(report['members'])==report['expected_members'];report['elapsed_seconds']=round(time.monotonic()-start,2)
 report['guard']='All bytes/versions inventoried; native screening is not semantic confirmation. Historic archive does not certify current SUAP variation completeness.';save();return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.source,a.output)
