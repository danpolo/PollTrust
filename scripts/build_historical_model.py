#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from polltrust.demo_data import build_demo_raw
from polltrust.model import build_model

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input"); p.add_argument("--output",default="data/historical-model.json"); a=p.parse_args()
    raw=json.loads(Path(a.input).read_text(encoding="utf-8")) if a.input else build_demo_raw()
    Path(a.output).write_text(json.dumps(build_model(raw),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0
if __name__=="__main__": raise SystemExit(main())
