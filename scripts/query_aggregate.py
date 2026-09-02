#!/usr/bin/env python3
"""Query the aggregate retrieval index without external dependencies."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'/'aggregate'
def main():
    q=' '.join(sys.argv[1:]).strip().lower()
    if not q: print('usage: query_aggregate.py <search terms>'); return 2
    rows={}
    p=DATA/'records.jsonl'
    if p.exists():
        for line in p.read_text(encoding='utf8').splitlines():
            if line.strip():
                r=json.loads(line); rows[r['id']]=r
    terms=set(re.findall(r'[a-z0-9]{3,}',q)); scored=[]
    for r in rows.values():
        text=(r.get('title','')+' '+r.get('summary','')).lower(); score=sum(1 for t in terms if t in text)
        if score: scored.append((score,r))
    for score,r in sorted(scored,key=lambda x:(-x[0],-len(x[1].get('title',''))))[:20]:
        print(json.dumps({'score':score,'title':r.get('title'),'url':r.get('url'),'source':r.get('source_name'),'published':r.get('published'),'confidence':r.get('confidence',0)},ensure_ascii=False))
    return 0
if __name__=='__main__': sys.exit(main())
