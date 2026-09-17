#!/usr/bin/env python3
"""One-time/resumable builder for PollTrust's production historical dataset.

Fetches configured HTML poll archives, caches immutable source snapshots, parses
poll tables deterministically, validates 120-seat rows, and writes the raw input
expected by build_historical_model.py. Re-running is safe and uses the cache
unless --refresh is supplied.
"""
from __future__ import annotations
import argparse, hashlib, html, json, re, sys, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

SOURCES=[
 {"election":"knesset-25","url":"https://themadad.com/allpolls25/","parser":"hebrew_table"},
 {"election":"knesset-24","url":"https://themadad.com/%D7%A1%D7%A7%D7%A8%D7%99%D7%9D-%D7%9C%D7%91%D7%97%D7%99%D7%A8%D7%95%D7%AA-%D7%9C%D7%9B%D7%A0%D7%A1%D7%AA-24-%D7%9E%D7%A8%D7%A5-2021/","parser":"hebrew_table"},
 # Older election archives. These are fallback public tables; only rows from
 # pollster lineages we explicitly recognize are retained.
 {"election":"knesset-23","url":"https://en.wikipedia.org/wiki/Opinion_polling_for_the_2020_Israeli_legislative_election","parser":"english_wiki"},
 {"election":"knesset-22","url":"https://en.wikipedia.org/wiki/Opinion_polling_for_the_September_2019_Israeli_legislative_election","parser":"english_wiki"},
 {"election":"knesset-21","url":"https://en.wikipedia.org/wiki/Opinion_polling_for_the_April_2019_Israeli_legislative_election","parser":"english_wiki"},
 {"election":"knesset-20","url":"https://en.wikipedia.org/wiki/Opinion_polling_for_the_2015_Israeli_legislative_election","parser":"english_wiki"},
]
ELECTIONS={
 "knesset-25":{"date":"2022-11-01","result":{"likud":32,"yesh_atid":24,"religious_zionism":14,"national_unity":12,"shas":11,"utj":7,"yisrael_beiteinu":6,"raam":5,"hadash_taal":5,"labor":4,"meretz":0,"balad":0}},
 "knesset-24":{"date":"2021-03-23","result":{"likud":30,"yesh_atid":17,"shas":9,"blue_white":8,"yamina":7,"utj":7,"labor":7,"yisrael_beiteinu":7,"religious_zionism":6,"joint_list":6,"new_hope":6,"meretz":6,"raam":4}},
 "knesset-23":{"date":"2020-03-02","result":{"likud":36,"blue_white":33,"joint_list":15,"shas":9,"utj":7,"labor_gesher_meretz":7,"yisrael_beiteinu":7,"yamina":6}},
 "knesset-22":{"date":"2019-09-17","result":{"blue_white":33,"likud":32,"joint_list":13,"shas":9,"yisrael_beiteinu":8,"utj":7,"yamina":7,"labor_gesher":6,"democratic_union":5}},
 "knesset-21":{"date":"2019-04-09","result":{"likud":35,"blue_white":35,"shas":8,"utj":8,"hadash_taal":6,"labor":6,"yisrael_beiteinu":5,"urwp":5,"meretz":4,"kulanu":4,"raam_balad":4}},
 "knesset-20":{"date":"2015-03-17","result":{"likud":30,"zionist_union":24,"joint_list":13,"yesh_atid":11,"kulanu":10,"jewish_home":8,"shas":7,"yisrael_beiteinu":6,"utj":6,"meretz":5}},
}
POLLSTERS={
 "מנו גבע":"midgam_geva","דודי חסיד":"kantar_hasid","מנחם לזר":"lazar",
 "יצחק כץ":"maagar_mohot_katz","שלמה פילבר וצוריאל שרון":"direct_polls_shared",
}
PARTIES={
 "הליכוד":"likud","יש עתיד":"yesh_atid","ש״ס":"shas","שס":"shas",
 "יהדות התורה":"utj","ישראל ביתנו":"yisrael_beiteinu","העבודה":"labor",
 "מרצ":"meretz","רע״מ":"raam","רעם":"raam","בל״ד":"balad","בלד":"balad",
 "הציונות הדתית":"religious_zionism","הציונות הדתית / זהות":"religious_zionism",
 "עוצמה":"otzma","עוצמה יהודית":"otzma","המחנה הממלכתי":"national_unity",
 "כחול לבן":"blue_white","ימינה":"yamina","תקווה חדשה":"new_hope",
 "הרשימה המשותפת":"joint_list","חדש תע״ל":"hadash_taal","חד״ש תע״ל":"hadash_taal",
 "חד״ש-תע״ל":"hadash_taal",
}

WIKI_PARTIES={
 "Likud":"likud","Blue and White":"blue_white","Blue & White":"blue_white","Joint List":"joint_list",
 "Shas":"shas","UTJ":"utj","United Torah Judaism":"utj","Yisrael Beitenu":"yisrael_beiteinu",
 "Yamina":"yamina","Labor–Gesher–Meretz":"labor_gesher_meretz","Labor-Gesher-Meretz":"labor_gesher_meretz",
 "Labor–Gesher":"labor_gesher","Labor-Gesher":"labor_gesher","Democratic Union":"democratic_union",
 "Hadash–Ta'al":"hadash_taal","Hadash-Ta'al":"hadash_taal","Labor":"labor","Meretz":"meretz",
 "Kulanu":"kulanu","Jewish Home":"jewish_home","Union of Right-Wing Parties":"urwp",
 "Ra'am–Balad":"raam_balad","Ra'am-Balad":"raam_balad","Zionist Union":"zionist_union","Yesh Atid":"yesh_atid",
}

META={"מספר הסקר","מספר","תאריך","משיבים","נדגמים","כלי תקשורת","מפרסם","עורך משאלים","סוקר"}

class TableParser(HTMLParser):
 def __init__(self):
  super().__init__(); self.tables=[]; self.table=None; self.row=None; self.cell=None
 def handle_starttag(self,tag,attrs):
  if tag=="table": self.table=[]
  elif self.table is not None and tag=="tr": self.row=[]
  elif self.row is not None and tag in ("th","td"): self.cell=[]
 def handle_data(self,data):
  if self.cell is not None: self.cell.append(data)
 def handle_endtag(self,tag):
  if tag in ("th","td") and self.cell is not None:
   self.row.append(" ".join("".join(self.cell).split())); self.cell=None
  elif tag=="tr" and self.row is not None:
   if any(self.row): self.table.append(self.row)
   self.row=None
  elif tag=="table" and self.table is not None:
   if self.table: self.tables.append(self.table)
   self.table=None

def normalize(s): return html.unescape(" ".join(str(s).replace("\u200f","").replace("\u200e","").split())).strip()
def parse_date(s):
 s=normalize(s)
 for fmt in ("%d/%m/%Y","%d.%m.%Y","%Y-%m-%d"):
  try: return datetime.strptime(s,fmt).date().isoformat()
  except ValueError: pass
 raise ValueError(f"unsupported date {s!r}")

def _header_index(headers,*names):
 for name in names:
  for i,h in enumerate(headers):
   if name in h: return i
 return None

def parse_archive(source_text,election_id,source_url):
 p=TableParser(); p.feed(source_text); polls=[]
 for table in p.tables:
  if len(table)<2: continue
  headers=[normalize(x) for x in table[0]]
  di=_header_index(headers,"תאריך"); pi=_header_index(headers,"עורך משאלים","סוקר")
  if di is None or pi is None: continue
  outlet_i=_header_index(headers,"כלי תקשורת","מפרסם")
  party_cols={i:PARTIES[h] for i,h in enumerate(headers) if h in PARTIES}
  if not party_cols: continue
  for row in table[1:]:
   if len(row)<=max(di,pi): continue
   pollster=POLLSTERS.get(normalize(row[pi]))
   if not pollster: continue
   parties={}
   for i,pid in party_cols.items():
    if i>=len(row): continue
    raw=normalize(row[i]).replace(",","")
    if raw in ("","—","-"): continue
    try: seats=float(raw)
    except ValueError: continue
    if seats>=0: parties[pid]=int(seats) if seats.is_integer() else seats
   # Poll tables can omit below-threshold parties. Missing seats are represented
   # explicitly as zero only for parties in that election's final-result universe.
   universe=set(ELECTIONS[election_id]["result"])
   normalized={pid:parties.get(pid,0) for pid in universe}
   # Preserve campaign parties not present in the final Knesset too.
   normalized.update({k:v for k,v in parties.items() if k not in normalized})
   if sum(normalized.values())!=120: continue
   polls.append({"pollster":pollster,"election":election_id,"date":parse_date(row[di]),
     "source":source_url,"outlet":normalize(row[outlet_i]) if outlet_i is not None and outlet_i<len(row) else None,
     "parties":normalized})
 return polls


def parse_wikipedia_archive(source_text,election_id,source_url):
 p=TableParser(); p.feed(source_text); polls=[]
 for table in p.tables:
  if len(table)<2: continue
  headers=[normalize(x) for x in table[0]]
  di=_header_index(headers,"Date"); pi=_header_index(headers,"Polling firm","Polling Firm")
  if di is None or pi is None: continue
  outlet_i=_header_index(headers,"Publisher")
  party_cols={}
  for i,h in enumerate(headers):
   clean=re.sub(r"\[[^]]+\]","",h).strip()
   if clean in WIKI_PARTIES: party_cols[i]=WIKI_PARTIES[clean]
  if not party_cols: continue
  for row in table[1:]:
   if len(row)<=max(di,pi): continue
   firm=normalize(row[pi])
   pollster=None
   for label,pid in POLLSTERS.items():
    if label and label.lower() in firm.lower(): pollster=pid; break
   if not pollster: continue
   try: poll_date=parse_english_date(row[di],ELECTIONS[election_id]["date"])
   except ValueError: continue
   parties={}
   for i,pid in party_cols.items():
    if i>=len(row): continue
    raw=normalize(row[i]).replace(",","")
    m=re.match(r"^\d+(?:\.\d+)?$",raw)
    if m: parties[pid]=float(raw)
   universe=set(ELECTIONS[election_id]["result"]); normalized={pid:parties.get(pid,0) for pid in universe}
   normalized.update({k:v for k,v in parties.items() if k not in normalized})
   if abs(sum(normalized.values())-120)>.001: continue
   normalized={k:int(v) if float(v).is_integer() else v for k,v in normalized.items()}
   polls.append({"pollster":pollster,"election":election_id,"date":poll_date,"source":source_url,
    "outlet":normalize(row[outlet_i]) if outlet_i is not None and outlet_i<len(row) else None,"parties":normalized})
 return polls

def parse_english_date(value,election_date):
 s=re.sub(r"\[[^]]+\]","",normalize(value)).replace("–","-")
 # For date ranges, use the later fieldwork/publication date.
 if "-" in s and re.match(r"^\d{1,2}\s*-\s*\d{1,2}\s+",s):
  first,rest=s.split("-",1); month_year=rest.strip().split(maxsplit=1)
  if len(month_year)==2: s=month_year[0]+" "+month_year[1]
 for fmt in ("%d %b %Y","%d %B %Y","%d %b %y","%d %B %y"):
  try: return datetime.strptime(s,fmt).date().isoformat()
  except ValueError: pass
 # Some archive rows omit the year; infer it from the election campaign.
 for fmt in ("%d %b","%d %B"):
  try:
   d=datetime.strptime(s,fmt); ed=datetime.fromisoformat(election_date)
   year=ed.year if d.month<=ed.month else ed.year-1
   return d.replace(year=year).date().isoformat()
  except ValueError: pass
 raise ValueError(f"unsupported English date {value!r}")

def fetch_cached(url,cache_dir,refresh=False):
 cache_dir.mkdir(parents=True,exist_ok=True); key=hashlib.sha256(url.encode()).hexdigest()[:16]
 path=cache_dir/f"{key}.html"
 if path.exists() and not refresh: return path.read_text(encoding="utf-8")
 req=urllib.request.Request(url,headers={"User-Agent":"PollTrust historical builder/1.0"})
 with urllib.request.urlopen(req,timeout=30) as r: data=r.read().decode("utf-8")
 if len(data)<500: raise RuntimeError(f"source returned suspiciously little data: {url}")
 path.write_text(data,encoding="utf-8"); return data

def build(output,cache_dir,refresh=False,allow_partial=False):
 all_polls=[]; status=[]
 for src in SOURCES:
  try:
   text=fetch_cached(src["url"],cache_dir,refresh); rows=(parse_wikipedia_archive(text,src["election"],src["url"]) if src.get("parser")=="english_wiki" else parse_archive(text,src["election"],src["url"]))
   if not rows: raise RuntimeError("no valid 120-seat rows parsed")
   all_polls.extend(rows); status.append({"url":src["url"],"election":src["election"],"polls":len(rows),"ok":True})
  except Exception as exc:
   status.append({"url":src["url"],"election":src["election"],"polls":0,"ok":False,"error":str(exc)})
   if not allow_partial: raise
 # Deduplicate exact pollster/date/party vectors.
 seen=set(); unique=[]
 for p in all_polls:
  key=(p["pollster"],p["election"],p["date"],tuple(sorted(p["parties"].items())))
  if key not in seen: seen.add(key); unique.append(p)
 raw={"schema_version":1,"demo_mode":False,"as_of":datetime.now(timezone.utc).isoformat(),
  "provenance":{"builder":"scripts/build_historical_dataset.py","sources":status},
  "elections":[{"id":eid,**e} for eid,e in ELECTIONS.items()],
  "polls":sorted(unique,key=lambda p:(p["election"],p["date"],p["pollster"])),
  "historical_pollsters":["midgam_geva","kantar_hasid","lazar","maagar_mohot_katz","direct_polls_shared"],
  "active_pollsters":[
   {"id":"midgam_geva","historical_id":"midgam_geva","name_he":"מנו גבע / מדגם","outlet_he":"חדשות 12"},
   {"id":"kantar_hasid","historical_id":"kantar_hasid","name_he":"דודי חסיד / קנטאר","outlet_he":"כאן 11"},
   {"id":"lazar","historical_id":"lazar","name_he":"מנחם לזר / לזר מחקרים","outlet_he":"מעריב"},
   {"id":"maagar_mohot_katz","historical_id":"maagar_mohot_katz","name_he":"יצחק כץ / מאגר מוחות","outlet_he":"ערוץ 16"},
   {"id":"direct_polls_sharon","name_he":"צוריאל שרון / דיירקט פולס","outlet_he":"i24NEWS","lineage_note_he":"חלק מהאומדן ההיסטורי נשען על עבר משותף עם שלמה פילבר בדיירקט פולס; משקלו יפחת ככל שיצטברו בחירות עצמאיות."},
   {"id":"next_data_filber","name_he":"שלמה פילבר / NEXT DATA","outlet_he":"ערוץ 14","lineage_note_he":"חלק מהאומדן ההיסטורי נשען על עבר משותף עם צוריאל שרון בדיירקט פולס; משקלו יפחת ככל שיצטברו בחירות עצמאיות."},
   {"id":"hamadad","name_he":"המדד","outlet_he":"חדשות 13"},
   {"id":"tatika","name_he":"יוסי טאטיקה / טאטיקה","outlet_he":"ישראל היום"}],
  "shared_prior":{"historical_id":"direct_polls_shared","targets":["direct_polls_sharon","next_data_filber"],"discount":0.5},
  "analysis":{"truth_bias_bloc_parties":["likud","shas","utj","religious_zionism","otzma"],"clusters":{"midgam_geva":"legacy_tv","kantar_hasid":"legacy_tv","lazar":"legacy_press","maagar_mohot_katz":"legacy_press","direct_polls_shared":"direct_shared"},"max_days_before":120,"max_staleness_days":45}}
 output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return raw

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",default="data/historical-polls.json"); ap.add_argument("--cache-dir",default=".cache/historical"); ap.add_argument("--refresh",action="store_true"); ap.add_argument("--allow-partial",action="store_true"); a=ap.parse_args()
 raw=build(Path(a.output),Path(a.cache_dir),a.refresh,a.allow_partial)
 print(f"wrote {len(raw['polls'])} polls to {a.output}")
 return 0
if __name__=="__main__": raise SystemExit(main())
