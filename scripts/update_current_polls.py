#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from polltrust.adapters import JsonFeedAdapter, RepositoryFixtureAdapter
from polltrust.ingestion import merge_polls

def load_sources(path):
    config=json.loads(path.read_text(encoding="utf-8")); adapters=[]
    for source in config.get("sources",[]):
        if not source.get("enabled",False): continue
        if source["type"]=="json_feed": adapters.append(JsonFeedAdapter(source["name"],source["url"]))
        elif source["type"]=="repository_fixture": adapters.append(RepositoryFixtureAdapter(source["path"],source["name"]))
        else: raise ValueError(f"unsupported source type: {source['type']}")
    return adapters

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data/current-polls.json"); p.add_argument("--sources",default="data/sources.json"); p.add_argument("--election",default="data/election.json"); a=p.parse_args()
    path=Path(a.data); merged=json.loads(path.read_text(encoding="utf-8")); election=json.loads(Path(a.election).read_text(encoding="utf-8")); adapters=load_sources(Path(a.sources))
    if not adapters: print("No enabled poll sources; existing data left untouched."); return 0
    total=0; errors=[]
    for adapter in adapters:
        try:
            merged,added=merge_polls(merged,adapter.fetch(),set(election["pollsters"])); total+=added
        except Exception as exc:
            errors.append(str(exc)); print(f"WARNING {adapter.name}: {exc}",file=sys.stderr)
    if total: path.write_text(json.dumps(merged,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 2 if errors and not total else 0
if __name__=="__main__": raise SystemExit(main())
