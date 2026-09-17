#!/usr/bin/env python3
"""Build PollTrust's sourced historical polling dataset deterministically.

The collector intentionally keeps only:
* polls from a defensible lineage of a currently active pollster;
* polls after the election-specific final-list configuration is stable;
* polls strictly before election day; and
* seat projections that sum to exactly 120 mandates.

Every candidate row that is not imported is represented in diagnostics instead
of being silently discarded.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WIKI = "https://en.wikipedia.org/wiki/"

ELECTIONS: dict[str, dict[str, Any]] = {
    "knesset-25": {
        "date": "2022-11-01",
        "result": {
            "likud": 32, "yesh_atid": 24, "national_unity": 12, "shas": 11,
            "jewish_home": 0, "labor": 4, "utj": 7, "yisrael_beiteinu": 6,
            "religious_zionism": 14, "hadash_taal": 5, "meretz": 0,
            "raam": 5, "balad": 0,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "religious_zionism"],
    },
    "knesset-24": {
        "date": "2021-03-23",
        "result": {
            "likud": 30, "yesh_atid": 17, "blue_white": 8, "joint_list": 6,
            "shas": 9, "utj": 7, "yisrael_beiteinu": 7, "meretz": 6,
            "raam": 4, "yamina": 7, "new_hope": 6, "labor": 7,
            "religious_zionism": 6, "new_economic": 0,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "religious_zionism"],
    },
    "knesset-23": {
        "date": "2020-03-02",
        "result": {
            "blue_white": 33, "likud": 36, "joint_list": 15,
            "labor_gesher_meretz": 7, "shas": 9, "yisrael_beiteinu": 7,
            "utj": 7, "yamina": 6, "otzma": 0,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "yamina", "otzma"],
    },
    "knesset-22": {
        "date": "2019-09-17",
        "result": {
            "likud": 32, "blue_white": 33, "joint_list": 13, "shas": 9,
            "utj": 7, "yamina": 7, "labor_gesher": 6,
            "yisrael_beiteinu": 8, "democratic_union": 5, "zehut": 0,
            "otzma": 0,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "yamina", "otzma"],
    },
    "knesset-21": {
        "date": "2019-04-09",
        "result": {
            "likud": 35, "labor": 6, "blue_white": 35, "kulanu": 4,
            "raam_balad": 4, "shas": 8, "utj": 8, "urwp": 5,
            "yisrael_beiteinu": 5, "meretz": 4, "hadash_taal": 6,
            "new_right": 0, "gesher": 0, "zehut": 0,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "urwp", "new_right"],
    },
    "knesset-20": {
        "date": "2015-03-17",
        "result": {
            "likud": 30, "yisrael_beiteinu": 6, "yesh_atid": 11,
            "zionist_union": 24, "jewish_home": 8, "shas": 7, "utj": 6,
            "meretz": 5, "joint_list": 13, "yachad": 0, "kulanu": 10,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "jewish_home", "yachad"],
    },
    "knesset-19": {
        "date": "2013-01-22",
        "result": {
            "kadima": 2, "likud_beiteinu": 31, "labor": 15, "shas": 11,
            "utj": 7, "jewish_home": 12, "ual_taal": 4, "hadash": 4,
            "balad": 3, "meretz": 6, "yesh_atid": 19, "otzma": 0,
            "am_shalem": 0, "hatnuah": 6,
        },
        "truth_bias_parties": None,
    },
    "knesset-18": {
        "date": "2009-02-10",
        "result": {
            "kadima": 28, "labor": 13, "shas": 11, "likud": 27,
            "yisrael_beiteinu": 15, "ual_taal": 4, "hadash": 4, "balad": 3,
            "jewish_home": 3, "national_union": 4, "gil": 0, "utj": 5,
            "meretz": 3, "greens": 0, "other_nonwinning": 0,
        },
        "truth_bias_parties": ["likud", "shas", "utj", "jewish_home", "national_union"],
    },
}

SOURCES: list[dict[str, Any]] = [
    {
        "election": "knesset-25",
        "url": WIKI + "Opinion_polling_for_the_2022_Israeli_legislative_election",
        "valid_from": "2022-09-16", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["likud", "yesh_atid", "national_unity", "shas", "jewish_home",
                        "labor", "utj", "yisrael_beiteinu", "religious_zionism",
                        "hadash_taal", "meretz", "raam", "balad"],
        "header_markers": ["Likud", "Yesh", "National", "Balad"],
    },
    {
        "election": "knesset-24",
        "url": WIKI + "Opinion_polling_for_the_2021_Israeli_legislative_election",
        "valid_from": "2021-02-05", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["likud", "yesh_atid", "blue_white", "joint_list", "shas", "utj",
                        "yisrael_beiteinu", "meretz", "raam", "yamina", "new_hope",
                        "labor", "religious_zionism", "new_economic"],
        "header_markers": ["Likud", "Yesh", "Blue", "New"],
    },
    {
        "election": "knesset-23",
        "url": WIKI + "Opinion_polling_for_the_2020_Israeli_legislative_election",
        "valid_from": "2020-01-17", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["blue_white", "likud", "joint_list", "labor_gesher_meretz",
                        "shas", "yisrael_beiteinu", "utj", "yamina", "otzma"],
        "header_markers": ["Blue", "Likud", "Joint", "Otzma"],
    },
    {
        "election": "knesset-22",
        "url": WIKI + "Opinion_polling_for_the_September_2019_Israeli_legislative_election",
        "valid_from": "2019-08-02", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["likud", "blue_white", "joint_list", "shas", "utj", "yamina",
                        "labor_gesher", "yisrael_beiteinu", "democratic_union", "zehut", "otzma"],
        "header_markers": ["Likud", "Blue", "Joint", "Zehut"],
    },
    {
        "election": "knesset-21",
        "url": WIKI + "Opinion_polling_for_the_April_2019_Israeli_legislative_election",
        "valid_from": "2019-02-22", "meta_columns": 2, "pollster_column": 1,
        "party_order": ["likud", "labor", "blue_white", "kulanu", "raam_balad", "shas", "utj",
                        "urwp", "yisrael_beiteinu", "meretz", "hadash_taal", "new_right",
                        "gesher", "zehut"],
        "header_markers": ["Likud", "Labor", "Blue", "Zehut"],
    },
    {
        "election": "knesset-20",
        "url": WIKI + "Opinion_polling_for_the_2015_Israeli_legislative_election",
        "valid_from": "2015-01-30", "meta_columns": 2, "pollster_column": 1,
        "party_order": ["likud", "yisrael_beiteinu", "yesh_atid", "zionist_union",
                        "jewish_home", "shas", "utj", "meretz", "joint_list", "yachad", "kulanu"],
        "header_markers": ["Likud", "Yisrael", "Yesh", "Kulanu"],
    },
    {
        "election": "knesset-19",
        "url": WIKI + "Opinion_polling_for_the_2013_Israeli_legislative_election",
        "valid_from": "2012-12-07", "meta_columns": 2, "pollster_column": 1,
        "party_order": ["kadima", "likud_beiteinu", "labor", "shas", "utj", "jewish_home",
                        "ual_taal", "hadash", "balad", "meretz", "yesh_atid", "otzma",
                        "am_shalem", "hatnuah"],
        "header_markers": ["Kadima", "Likud", "Labor", "Hatnuah"],
    },
    {
        "election": "knesset-18",
        "url": WIKI + "Opinion_polling_for_the_2009_Israeli_legislative_election",
        "valid_from": "2008-12-23", "meta_columns": 3, "pollster_column": 2,
        "party_order": ["kadima", "labor", "shas", "likud", "yisrael_beiteinu", "ual_taal",
                        "hadash", "balad", "jewish_home", "national_union", "gil", "utj",
                        "meretz", "greens", "other_nonwinning"],
        "header_markers": ["Media", "Pollster", "Kadima", "Other"],
        "other_text_column": "other_nonwinning",
    },
]

HISTORICAL_POLLSTERS = [
    "midgam_geva", "kantar_hasid", "lazar_research", "maagar_mohot", "direct_polls_shared"
]

ACTIVE_POLLSTERS = [
    {"id": "midgam_geva", "historical_id": "midgam_geva", "name_he": "מדגם / מנו גבע", "outlet_he": "חדשות 12"},
    {"id": "kantar_hasid", "historical_id": "kantar_hasid", "name_he": "קנטאר / דודי חסיד", "outlet_he": "כאן 11"},
    {"id": "lazar_research", "historical_id": "lazar_research", "name_he": "לזר מחקרים / מנחם לזר", "outlet_he": "מעריב"},
    {"id": "maagar_mohot", "historical_id": "maagar_mohot", "name_he": "מאגר מוחות / יצחק כ״ץ", "outlet_he": "כלי תקשורת נוכחי"},
    {"id": "direct_polls_sharon", "name_he": "Direct Polls / צוריאל שרון", "outlet_he": "i24NEWS",
     "lineage_note_he": "חלק מהערכת האמינות ההיסטורית מבוסס על התקופה שבה הסוקר פעל במסגרת Direct Polls המשותפת. משקל היסטוריה זו מופחת ויורד ככל שמצטברים נתונים עצמאיים מהפעילות הנוכחית."},
    {"id": "next_data_filber", "name_he": "NEXT DATA / שלמה פילבר", "outlet_he": "ערוץ 14",
     "lineage_note_he": "חלק מהערכת האמינות ההיסטורית מבוסס על התקופה שבה הסוקר פעל במסגרת Direct Polls המשותפת. משקל היסטוריה זו מופחת ויורד ככל שמצטברים נתונים עצמאיים מהפעילות הנוכחית."},
    {"id": "hamadad_consortium", "name_he": "המדד / קונסורציום חדשות 13", "outlet_he": "חדשות 13"},
    {"id": "tatika", "name_he": "יוסי טאטיקה / Tatika Research & Media", "outlet_he": "כלי תקשורת נוכחי"},
]

_ALIAS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("direct_polls_shared", re.compile(r"\bdirect\s+polls?\b", re.I)),
    ("kantar_hasid", re.compile(r"\bkantar\b", re.I)),
    ("lazar_research", re.compile(r"\bpanels(?:\s+politics)?\b", re.I)),
    ("maagar_mohot", re.compile(r"\bma['’]?a?gar\s+mo(?:h|c)ot\b|\bmaagar\s+mo(?:h|c)ot\b", re.I)),
    ("midgam_geva", re.compile(r"\bmidgam(?:\s+research)?\b", re.I)),
]

class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and self.table is None:
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("th", "td"):
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self.cell is not None and self.row is not None:
            self.row.append(normalize("".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            if self.table:
                self.tables.append(self.table)
            self.table = None


def normalize(value: Any) -> str:
    text = html.unescape(str(value)).replace("\u200f", "").replace("\u200e", "")
    text = re.sub(r"\[\s*\d+[a-z]?\s*\]", "", text, flags=re.I)
    return " ".join(text.split()).strip()


def resolve_pollster(raw: str) -> str | None:
    value = normalize(raw)
    low = value.lower()
    if "panel project hamidgam" in low or "panel hamidgam project" in low:
        return None
    if "מנו גבע" in value:
        return "midgam_geva"
    if "דודי חסיד" in value:
        return "kantar_hasid"
    if "מנחם לזר" in value:
        return "lazar_research"
    if "יצחק כץ" in value:
        return "maagar_mohot"
    if "שלמה פילבר" in value and "צוריאל שרון" in value:
        return "direct_polls_shared"
    for pollster_id, pattern in _ALIAS_PATTERNS:
        if pattern.search(value):
            return pollster_id
    return None


def parse_english_date(value: str, election_date: str) -> str:
    s = normalize(value).replace("–", "-").replace("—", "-")
    s = re.sub(r"\([^)]*\)", "", s).strip()
    range_match = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\s+(.+)$", s)
    if range_match:
        s = f"{range_match.group(2)} {range_match.group(3)}"
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b %y", "%d %B %y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    election = date.fromisoformat(election_date)
    for fmt in ("%d %b", "%d %B", "%b %d", "%B %d"):
        try:
            parsed = datetime.strptime(s, fmt)
            year = election.year if parsed.month <= election.month else election.year - 1
            return parsed.replace(year=year).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"unsupported English date {value!r}")


def _parse_other_text(value: str) -> float:
    s = normalize(value)
    if not s or s in {"-", "–", "—", "N/A", "N/a", "n/a"}:
        return 0.0
    if "%" in s:
        return 0.0
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    numbers = [float(x) for x in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", s)]
    if numbers:
        return sum(numbers)
    raise ValueError(f"unparseable other-party cell {value!r}")


def parse_seat_cell(value: str, *, allow_other_text: bool = False) -> float:
    s = normalize(value).replace(",", "")
    if not s or s in {"-", "–", "—", "N/A", "N/a", "n/a", "N/a—"}:
        return 0.0
    if "%" in s:
        return 0.0
    if allow_other_text:
        return _parse_other_text(s)
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    raise ValueError(f"unparseable seat cell {value!r}")


def _source_tables(source_text: str, source: dict[str, Any]) -> list[list[list[str]]]:
    parser = TableParser()
    parser.feed(source_text)
    selected = []
    markers = [m.lower() for m in source.get("header_markers", [])]
    for table in parser.tables:
        blob = " ".join(" ".join(row) for row in table[:4]).lower()
        if all(marker in blob for marker in markers):
            selected.append(table)
    return selected


def parse_wikipedia_archive(
    source_text: str,
    election_id: str,
    source_url: str,
    *,
    diagnostics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    source = next((s for s in SOURCES if s["election"] == election_id and s["url"] == source_url), None)
    if source is None:
        source = next((s for s in SOURCES if s["election"] == election_id), None)
    if source is None:
        raise ValueError(f"no parser configuration for {election_id}")

    diag = diagnostics if diagnostics is not None else {}
    diag.setdefault("unmatched_pollster_names", Counter())
    diag.setdefault("malformed_rows", [])
    diag.setdefault("skipped_rows", [])
    diag.setdefault("matched_rows", 0)
    diag.setdefault("tables_matched", 0)

    polls: list[dict[str, Any]] = []
    election_day = date.fromisoformat(ELECTIONS[election_id]["date"])
    valid_from = date.fromisoformat(source["valid_from"])
    party_order = list(source["party_order"])
    meta_columns = int(source["meta_columns"])
    pollster_column = int(source["pollster_column"])
    tables = _source_tables(source_text, source)
    diag["tables_matched"] += len(tables)

    for table in tables:
        for row in table[1:]:
            if not row:
                continue
            try:
                poll_date_s = parse_english_date(row[0], ELECTIONS[election_id]["date"])
            except ValueError:
                continue
            poll_date = date.fromisoformat(poll_date_s)
            if poll_date < valid_from:
                diag["skipped_rows"].append({"reason": "before_stable_list_cutoff", "row": row[:6], "date": poll_date_s})
                continue
            if poll_date >= election_day:
                diag["skipped_rows"].append({"reason": "election_day_or_future", "row": row[:6], "date": poll_date_s})
                continue
            if len(row) <= pollster_column:
                diag["malformed_rows"].append({"reason": "missing_pollster_cell", "row": row})
                continue
            raw_pollster = normalize(row[pollster_column])
            pollster = resolve_pollster(raw_pollster)
            if pollster is None:
                if raw_pollster:
                    diag["unmatched_pollster_names"][raw_pollster] += 1
                continue
            diag["matched_rows"] += 1
            need = meta_columns + len(party_order)
            if len(row) < need:
                diag["malformed_rows"].append({
                    "reason": "too_few_columns", "pollster": raw_pollster, "date": poll_date_s,
                    "expected_min": need, "actual": len(row), "row": row,
                })
                continue
            parties: dict[str, int | float] = {}
            bad_cell = None
            for idx, party_id in enumerate(party_order):
                raw = row[meta_columns + idx]
                try:
                    value = parse_seat_cell(raw, allow_other_text=party_id == source.get("other_text_column"))
                except ValueError as exc:
                    bad_cell = {"party": party_id, "value": raw, "error": str(exc)}
                    break
                parties[party_id] = int(value) if float(value).is_integer() else value
            if bad_cell:
                diag["malformed_rows"].append({
                    "reason": "malformed_seat_cell", "pollster": raw_pollster, "date": poll_date_s,
                    **bad_cell, "row": row,
                })
                continue
            total = sum(float(v) for v in parties.values())
            if abs(total - 120.0) > 0.001:
                diag["skipped_rows"].append({
                    "reason": "seat_total_not_120", "pollster": raw_pollster, "pollster_id": pollster,
                    "date": poll_date_s, "seat_total": total, "row": row,
                })
                continue
            outlet = None
            if meta_columns >= 3 and len(row) > 2:
                outlet = normalize(row[1] if pollster_column == 2 else row[2]) or None
            elif meta_columns == 2:
                outlet = normalize(row[pollster_column]) or None
            polls.append({
                "pollster": pollster,
                "election": election_id,
                "date": poll_date_s,
                "source": source_url,
                "outlet": outlet,
                "source_pollster_name": raw_pollster,
                "parties": parties,
            })
    return polls


def parse_archive(source_text: str, election_id: str, source_url: str) -> list[dict[str, Any]]:
    return parse_wikipedia_archive(source_text, election_id, source_url)


def fetch_cached(url: str, cache_dir: Path, refresh: bool = False) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    path = cache_dir / f"{key}.html"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PollTrust historical dataset builder/2.0 (https://github.com/danpolo/PollTrust)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        data = response.read().decode("utf-8")
    if len(data) < 500:
        raise RuntimeError(f"source returned suspiciously little data: {url}")
    path.write_text(data, encoding="utf-8")
    return data


def _jsonable_diag(diag: dict[str, Any]) -> dict[str, Any]:
    out = dict(diag)
    if isinstance(out.get("unmatched_pollster_names"), Counter):
        out["unmatched_pollster_names"] = dict(out["unmatched_pollster_names"].most_common())
    return out


def _deduplicate(polls: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    same_day: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    duplicates: list[dict[str, Any]] = []
    unique: list[dict[str, Any]] = []
    for poll in polls:
        vector = tuple(sorted((k, float(v)) for k, v in poll["parties"].items()))
        key = (poll["pollster"], poll["election"], poll["date"], vector)
        if key in seen:
            duplicates.append({"kept": seen[key], "duplicate": poll})
            continue
        seen[key] = poll
        unique.append(poll)
        same_day[(poll["pollster"], poll["election"], poll["date"])].append(poll)
    conflicts = []
    for key, rows in same_day.items():
        vectors = {tuple(sorted((k, float(v)) for k, v in p["parties"].items())) for p in rows}
        if len(vectors) > 1:
            conflicts.append({"pollster": key[0], "election": key[1], "date": key[2], "polls": rows})
    return unique, duplicates, conflicts


def build(output: Path, cache_dir: Path, refresh: bool = False, allow_partial: bool = False) -> dict[str, Any]:
    all_polls: list[dict[str, Any]] = []
    source_status: list[dict[str, Any]] = []
    aggregate_unmatched: Counter[str] = Counter()
    aggregate_malformed: list[dict[str, Any]] = []
    aggregate_skipped: list[dict[str, Any]] = []

    for source in SOURCES:
        diag: dict[str, Any] = {}
        try:
            text = fetch_cached(source["url"], cache_dir, refresh)
            rows = parse_wikipedia_archive(text, source["election"], source["url"], diagnostics=diag)
            if not rows:
                raise RuntimeError("no valid target-lineage 120-seat rows parsed")
            all_polls.extend(rows)
            status = {
                "url": source["url"], "election": source["election"], "valid_from": source["valid_from"],
                "polls": len(rows), "ok": True, "diagnostics": _jsonable_diag(diag),
            }
        except Exception as exc:
            status = {
                "url": source["url"], "election": source["election"], "valid_from": source["valid_from"],
                "polls": 0, "ok": False, "error": str(exc), "diagnostics": _jsonable_diag(diag),
            }
            if not allow_partial:
                source_status.append(status)
                raise
        source_status.append(status)
        aggregate_unmatched.update(diag.get("unmatched_pollster_names", {}))
        for row in diag.get("malformed_rows", []):
            aggregate_malformed.append({"election": source["election"], **row})
        for row in diag.get("skipped_rows", []):
            aggregate_skipped.append({"election": source["election"], **row})

    unique, duplicates, conflicts = _deduplicate(all_polls)
    if conflicts and not allow_partial:
        raise RuntimeError(f"found {len(conflicts)} conflicting same-pollster/day historical rows")

    raw = {
        "schema_version": 2,
        "demo_mode": False,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "builder": "scripts/build_historical_dataset.py",
            "source_policy": "Wikipedia election archives are the reproducible fallback; TheMadad is a manual cross-check because it returns HTTP 403 in GitHub Actions.",
            "sources": source_status,
            "diagnostics": {
                "unmatched_pollster_names": dict(aggregate_unmatched.most_common()),
                "unmatched_party_names": {},
                "malformed_rows": aggregate_malformed,
                "skipped_rows": aggregate_skipped,
                "duplicates_removed": duplicates,
                "conflicting_same_day_rows": conflicts,
            },
        },
        "elections": [{"id": election_id, **election} for election_id, election in ELECTIONS.items()],
        "polls": sorted(unique, key=lambda p: (p["election"], p["date"], p["pollster"], p.get("outlet") or "")),
        "historical_pollsters": HISTORICAL_POLLSTERS,
        "active_pollsters": ACTIVE_POLLSTERS,
        "shared_prior": {
            "historical_id": "direct_polls_shared",
            "targets": ["direct_polls_sharon", "next_data_filber"],
            "discount": 0.5,
        },
        "analysis": {
            "max_days_before": 120,
            "max_staleness_days": 45,
            "clusters": {
                "midgam_geva": "legacy_tv",
                "kantar_hasid": "legacy_tv",
                "lazar_research": "legacy_press",
                "maagar_mohot": "legacy_press",
                "direct_polls_shared": "direct_shared",
            },
            "truth_bias_bloc_parties": ["likud", "shas", "utj"],
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/historical-polls.json")
    parser.add_argument("--cache-dir", default=".cache/historical")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    raw = build(Path(args.output), Path(args.cache_dir), args.refresh, args.allow_partial)
    counts_e = Counter(p["election"] for p in raw["polls"])
    counts_p = Counter(p["pollster"] for p in raw["polls"])
    print(f"wrote {len(raw['polls'])} polls to {args.output}")
    print("by election:", dict(sorted(counts_e.items())))
    print("by pollster:", dict(sorted(counts_p.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
