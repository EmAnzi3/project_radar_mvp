#!/usr/bin/env python3
"""Serra Giannina MASE: bounded batches; PDF keyword hits are not verified facts."""
import argparse, json, re, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
sys.path.insert(0,str(Path(__file__).resolve().parent))
from wind_mase_inventory import inventory
from harvest_wind_project import run as harvest, save

ROOT=Path(__file__).resolve().parents[1]
PATS={k:re.compile(v,re.I) for k,v in {
 "timeline":r"cronoprogramma|inizio lavori|fine lavori|202[5-9]",
 "roles":r"appalt|affidament|contratto|subappalt|esecutor|fornitor|EPC|BoP",
 "contacts":r"partita iva|p\.iva|codice fiscale|(?:PEC|email)\b|@[a-z0-9.-]+\.",
 "works":r"fondazion|pali\b|scavi|cavidott|sottostazion|piazzol|montaggio",
 "companies":r"RWE|EGM|proponent|committent|s\.r\.l\.|s\.p\.a\."}.items()}
def time():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def load(p):
 p=Path(p)
 return json.loads(p.read_text(encoding="utf8")) if p.exists() else {}
def seed(state):
 review=load(ROOT/"config/wind_serra_review.json")
 sources={x["id"]:x["url"] for x in review.get("sources_added",[])}
 sources["sg-plan"]=review.get("changed_source",{}).get("sg-plan")
 for key,h in review.get("documentary",{}).get("acquired_document_shas",{}).items():
  u=sources.get(key)
  if u:state["documents"].setdefault(u,{"status":"prior_reviewed","sha256":h,"source_id":key})
def scan(state,config):
 if state.get("last_index","")>(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat():return
 status=[]
 with requests.Session() as s:
  for spec in config["procedures"]:
   d=inventory(s,spec)
   status.append({"id":spec["id"],"complete":d["complete"],"rows":len(d["rows"]),"expected":d["expected"],"error":d["error"]})
   if d["complete"]:
    state["inventory"].update({x["url"]:dict(x,procedure=spec["id"]) for x in d["rows"]})
 state["index_status"]=status
 state["last_index"]=time()
def score(row):
 t=(row.get("title","")+" "+row.get("filename","")).lower()
 ranks=["cronoprogramma","contratto","affidamento","computo metrico","cantierizzazione","esecutivo","sottostazione","fondazion","cavidott"]
 m=re.search("20[0-9][0-9]",row.get("published",""))
 return (-int(m.group()) if m else 0,next((i for i,x in enumerate(ranks) if x in t),15),t)
def excerpt(data):
 hits={};scans=[]
 for page in data.get("pages",[]):
  n=page["page"];txt=re.sub(r"\s+"," ",page.get("text",""))
  if page.get("visual_review_needed"):scans.append(n)
  for k,pattern in PATS.items():
   if len(hits.get(k,[]))>=8:continue
   for x in list(pattern.finditer(txt))[:2]:
    hits.setdefault(k,[]).append({"page":n,"excerpt":txt[max(0,x.start()-80):x.end()+100][:220]})
 return hits,scans[:80]
def run(statefile,reportfile,count=6,offline=False):
 state=load(statefile)
 if state and state.get("project_id")!="serra-giannina":raise ValueError("Wrong project state")
 state.setdefault("project_id","serra-giannina")
 state.setdefault("documents",{});state.setdefault("inventory",{})
 seed(state);batch=[];network={}
 if not offline:
  scan(state,load(ROOT/"config/wind_serra_mase.json"))
  save(statefile,state)
  rows=[]
  for row in sorted(state["inventory"].values(),key=score):
   old=state["documents"].get(row["url"],{})
   if old.get("status") in ("prior_reviewed","extracted","visual_only","oversize"):continue
   if old.get("retry_after","")>time():continue
   size=re.search(r"[0-9]+",row.get("size",""))
   if size and int(size.group())>64000:
    state["documents"][row["url"]]={"status":"oversize","source_title":row["title"]}
    continue
   rows.append(row)
   if len(rows)>=count:break
  save(statefile,state)
  if rows:
   config={"project_id":"serra-giannina","scope_note":"MASE indexed originals",
    "allowed_hosts":["va.mite.gov.it","va.mase.gov.it"],"link_depth":0,
    "sources":[{"url":r["url"],"title":r["title"],"scope":"project_document","expected":"pdf"} for r in rows]}
   with tempfile.TemporaryDirectory() as tmp:
    meta=harvest(config,Path(tmp))
    network={k:meta[k] for k in ("network_requests","bytes_transferred","text_extractions")}
    found=load(Path(tmp)/"manifest.json").get("resources",{})
    for row in rows:
     u=row["url"];result=found.get(u,{})
     if result.get("kind")=="pdf" and result.get("text"):
      pagefile=load(Path(tmp)/result["text"])
      hits,scans=excerpt(pagefile)
      state["documents"][u]={"status":"extracted" if pagefile.get("pages") else "visual_only",
       "sha256":result["sha256"],"pages":pagefile.get("page_count",0),
       "keyword_candidates":hits,"visual_review_pages":scans,
       "source_title":row["title"],"fact_status":"unverified"}
     else:
      previous=state["documents"].get(u,{})
      attempt=previous.get("attempt",0)+1
      state["documents"][u]={"status":"error","attempt":attempt,
       "reason":result.get("error","No PDF acquired")[:220],
       "retry_after":(datetime.now(timezone.utc)+timedelta(hours=min(168,6*2**min(attempt-1,4)))).isoformat(timespec="seconds")}
     save(statefile,state)
     batch.append({"url":u,"status":state["documents"][u]["status"],
       "sha256":state["documents"][u].get("sha256")})
 docs=state["documents"];keys=set(state["inventory"])
 report={"project_id":"serra-giannina","checked_at":time(),"indexes":state.get("index_status",[]),
  "indexed_references":len(keys),"prior_reviewed":sum(v.get("status")=="prior_reviewed" for v in docs.values()),
  "extracted":sum(docs.get(k,{}).get("status")=="extracted" for k in keys),
  "unattempted":sum(k not in docs for k in keys),
  "needs_visual_or_size_review":sum(docs.get(k,{}).get("status") in ("oversize","visual_only") for k in keys),
  "errors":sum(docs.get(k,{}).get("status")=="error" for k in keys),
  "batch":batch,"network":network,"new_verified_facts":0,
  "dossier_complete":False,"paid_ai_calls":0,
  "caveat":"Keyword candidates are not verified EPC, timeline or procurement facts."}
 save(reportfile,report)
 return report
if __name__=="__main__":
 a=argparse.ArgumentParser()
 a.add_argument("--state",required=True);a.add_argument("--report",required=True)
 a.add_argument("--limit",type=int,default=6);a.add_argument("--offline",action="store_true")
 args=a.parse_args()
 if not 0<=args.limit<=20:a.error("limit must be 0..20")
 print(json.dumps(run(args.state,args.report,args.limit,args.offline),ensure_ascii=False,indent=2))
