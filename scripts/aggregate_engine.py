#!/usr/bin/env python3
"""Complete dependency-free aggregation pipeline.

Pipeline: discover -> fetch -> normalize -> deduplicate -> entity-match ->
score -> persist evidence -> build retrieval index. It is intentionally
conservative: discoveries are candidates and are never silently promoted to
facts.
"""
from __future__ import annotations
import hashlib, json, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'/'aggregate'
CONFIG=ROOT/'data'/'sources.json'; RECORDS=DATA/'records.jsonl'; ENTITIES=DATA/'entities.json'; INDEX=DATA/'retrieval.json'; RUNS=DATA/'runs.jsonl'
UA='family-323979-aggregator/2.0'

def now(): return datetime.now(timezone.utc).isoformat()
def clean(v): return re.sub(r'\\s+',' ',str(v or '')).strip()
def norm(v): return re.sub(r'[^a-z0-9]','',clean(v).lower())
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/atom+xml, application/json, text/xml;q=0.9, */*;q=0.8'})
    with urllib.request.urlopen(req,timeout=30) as r: return r.read()
def xml_items(payload):
    root=ET.fromstring(payload); ns={'a':'http://www.w3.org/2005/Atom'}; entries=root.findall('.//item') or root.findall('.//a:entry',ns); out=[]
    for e in entries:
        def t(*paths):
            for p in paths:
                n=e.find(p,ns) if ':' in p else e.find(p)
                if n is not None and clean(n.text): return clean(n.text)
            return ''
        n=e.find('a:link',ns); link=clean(n.attrib.get('href','')) if n is not None else t('link')
        out.append({'title':t('title','a:title'),'url':link,'summary':t('description','summary','a:summary','content','a:content'),'published':t('pubDate','published','updated','a:published','a:updated')})
    return [x for x in out if x['title'] or x['url']]
def json_items(payload,s):
    o=json.loads(payload.decode()); items=o if isinstance(o,list) else o.get(s.get('items_path','items'),[]); out=[]
    for x in items if isinstance(items,list) else []:
        if not isinstance(x,dict): continue
        g=lambda k: clean(x.get(s.get(k,k),k))
        row={'title':g('title_field'),'url':g('url_field'),'summary':g('summary_field'),'published':g('date_field')}
        if row['title'] or row['url']: out.append(row)
    return out
def fid(source,item): return hashlib.sha256('|'.join([source,item.get('url',''),item.get('title',''),item.get('published','')]).encode()).hexdigest()
def sim(a,b): return SequenceMatcher(None,norm(a),norm(b)).ratio() if a and b else 0.0
def load(p,default):
    if not p.exists(): return default
    return json.loads(p.read_text(encoding='utf8'))
def main():
    DATA.mkdir(parents=True,exist_ok=True); cfg=load(CONFIG,{'sources':[]}); existing={}
    if RECORDS.exists():
        for line in RECORDS.read_text(encoding='utf8').splitlines():
            if line.strip():
                r=json.loads(line); existing[r['id']]=r
    discovered=0; errors=[]; stamp=now()
    for s in cfg.get('sources',[]):
        if s.get('enabled',True) is False: continue
        try:
            raw=fetch(s['url']); items=json_items(raw,s) if s.get('type','rss').lower()=='json' else xml_items(raw)
            for item in items:
                ident=fid(s['id'],item)
                if ident not in existing:
                    existing[ident]={'id':ident,'source_id':s['id'],'source_name':s.get('name',s['id']),'source_url':s['url'],'collected_at':stamp,'status':'candidate','confidence':0.0,**item}; discovered+=1
        except Exception as e: errors.append({'source_id':s.get('id'),'error':str(e)})
    rows=list(existing.values())
    # Entity extraction is deliberately generic; explicit entities can be supplied in data/entities.json.
    entities=load(ROOT/'data'/'entities.json',[])
    if isinstance(entities,dict): entities=entities.get('entities',[])
    for r in rows:
        candidates=[]
        for e in entities:
            names=[e.get('name','')]+e.get('aliases',[])
            score=max([sim(r.get('title',''),n) for n in names]+[sim(r.get('summary',''),n) for n in names])
            if score>=0.72: candidates.append({'entity_id':e.get('id'), 'score':round(score,3)})
        candidates.sort(key=lambda x:x['score'],reverse=True); r['entity_matches']=candidates[:5]
        r['confidence']=candidates[0]['score'] if candidates else 0.0
    rows.sort(key=lambda x:x.get('collected_at',''),reverse=True); RECORDS.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
    # Lightweight inverted retrieval index: terms -> record IDs.
    inv={}
    stop={'the','and','for','with','from','that','this','are','was','were','has','have','into','about'}
    for r in rows:
        text=' '.join([r.get('title',''),r.get('summary','')]); terms=set(re.findall(r'[a-z0-9]{3,}',text.lower()))-stop
        for term in terms: inv.setdefault(term,[]).append(r['id'])
    INDEX.write_text(json.dumps({'generated_at':stamp,'record_count':len(rows),'terms':inv},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    ENTITIES.write_text(json.dumps({'generated_at':stamp,'entities':entities},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with RUNS.open('a',encoding='utf8') as f: f.write(json.dumps({'run_at':stamp,'new_records':discovered,'total_records':len(rows),'errors':errors},ensure_ascii=False)+'\n')
    print(json.dumps({'new_records':discovered,'total_records':len(rows),'errors':len(errors)})); return 0
if __name__=='__main__': sys.exit(main())
