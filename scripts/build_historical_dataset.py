#!/usr/bin/env python3
"""Build PollTrust's sourced historical polling dataset deterministically.

The collector intentionally keeps only:
* polls from a defensible lineage of a currently active pollster;
* polls whose party/list configuration can be normalized to the eventual election;
* polls strictly before election day; and
* seat projections that sum to exactly 120 mandates.

Pre-final-list polls are retained when their table schema can be normalized
deterministically. Mergers are collapsed into the eventual list; where one
earlier list later split into multiple final lists, the poll stores an explicit
comparison group so the model collapses the official result the same way.

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

WIKI = "https://en.wikipedia.org/wiki/"  # retained for coverage-note references

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
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2022_Israeli_legislative_election&oldid=1360584369",
        "valid_from": "2022-09-16", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["likud", "yesh_atid", "national_unity", "shas", "jewish_home",
                        "labor", "utj", "yisrael_beiteinu", "religious_zionism",
                        "hadash_taal", "meretz", "raam", "balad"],
        "header_markers": ["Likud", "Yesh", "National", "Balad"],
    },
    {
        "election": "knesset-24",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2021_Israeli_legislative_election&oldid=1357147509",
        "valid_from": "2021-02-05", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["likud", "yesh_atid", "blue_white", "joint_list", "shas", "utj",
                        "yisrael_beiteinu", "meretz", "raam", "yamina", "new_hope",
                        "labor", "religious_zionism", "new_economic"],
        "header_markers": ["Likud", "Yesh", "Blue", "New"],
    },
    {
        "election": "knesset-23",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2020_Israeli_legislative_election&oldid=1357147489",
        "valid_from": "2020-01-17", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["blue_white", "likud", "joint_list", "labor_gesher_meretz",
                        "shas", "yisrael_beiteinu", "utj", "yamina", "otzma"],
        "header_markers": ["Blue", "Likud", "Joint", "Otzma"],
    },
    {
        "election": "knesset-22",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_September_2019_Israeli_legislative_election&oldid=1357147577",
        "valid_from": "2019-08-02", "meta_columns": 3, "pollster_column": 1,
        "party_order": ["likud", "blue_white", "joint_list", "shas", "utj", "yamina",
                        "labor_gesher", "yisrael_beiteinu", "democratic_union", "zehut", "otzma"],
        "header_markers": ["Likud", "Blue", "Joint", "Zehut"],
    },
    {
        "election": "knesset-21",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_April_2019_Israeli_legislative_election&oldid=1368358661",
        "valid_from": "2019-02-22", "meta_columns": 2, "pollster_column": 1,
        "party_order": ["likud", "labor", "blue_white", "kulanu", "raam_balad", "shas", "utj",
                        "urwp", "yisrael_beiteinu", "meretz", "hadash_taal", "new_right",
                        "gesher", "zehut"],
        "header_markers": ["Likud", "Labor", "Blue", "Zehut"],
    },
    {
        "election": "knesset-20",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2015_Israeli_legislative_election&oldid=1368358626",
        "valid_from": "2015-01-30", "meta_columns": 2, "pollster_column": 1,
        "party_order": ["likud", "yisrael_beiteinu", "yesh_atid", "zionist_union",
                        "jewish_home", "shas", "utj", "meretz", "joint_list", "yachad", "kulanu"],
        "header_markers": ["Likud", "Yisrael", "Yesh", "Kulanu"],
    },
    {
        "election": "knesset-19",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2013_Israeli_legislative_election&oldid=1368358600",
        "valid_from": "2012-12-07", "meta_columns": 2, "pollster_column": 1,
        "party_order": ["kadima", "likud_beiteinu", "labor", "shas", "utj", "jewish_home",
                        "ual_taal", "hadash", "balad", "meretz", "yesh_atid", "otzma",
                        "am_shalem", "hatnuah"],
        "header_markers": ["Kadima", "Likud", "Labor", "Hatnuah"],
    },
    {
        "election": "knesset-18",
        "url": "https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_2009_Israeli_legislative_election&oldid=1357147435",
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

LINEAGE_STARTS = {
    # Mano Geva is directly documented as CEO of Midgam in January 2009.
    "midgam_geva": "2008-12-23",
    # Kantar rows are kept only under the Kantar name; earlier TNS/Teleseker is not inherited.
    "kantar_hasid": "2019-08-02",
    # Generic Panels rows are attributed to Lazar only from the 2013 campaign,
    # where contemporary sources explicitly identify Menachem Lazar of Panels Politics.
    "lazar_research": "2012-12-07",
    # Maagar Mohot / Yitzhak Katz continuity is clear before 2009. A 2006
    # archive row was checked but excluded because the published vector totals 119.
    "maagar_mohot": "2008-12-23",
    # The shared Filber/Sharon Direct Polls lineage starts in the 2019 campaign.
    "direct_polls_shared": "2019-02-22",
}

HISTORICAL_COVERAGE_NOTES = {
    "midgam_geva": {
        "earliest_imported_campaign": "knesset-18",
        "note": "Mano Geva is directly documented as CEO of Midgam in January 2009; no earlier complete 120-seat election vector was found in the reviewed public archives.",
        "references": ["https://www.runi.ac.il/research-institutes/government/ips/herzliya-conference/hc2009/presentations"],
    },
    "kantar_hasid": {
        "earliest_imported_campaign": "knesset-22",
        "note": "Only rows explicitly branded Kantar are inherited. TNS/Teleseker rows are deliberately excluded because continuity to Dudi Hasid/Kantar was not established.",
        "references": ["https://www.globes.co.il/news/article.aspx?did=1001301132"],
    },
    "lazar_research": {
        "earliest_imported_campaign": "knesset-19",
        "note": "Panels Politics is treated as Menachem Lazar continuity from the 2013 campaign onward. Generic Panels rows from 2009 are excluded because personal continuity was not sufficiently established.",
        "references": ["https://jewishjournal.com/israel/121116/israelis-support-an-attack-on-assad-but-also-support-assad/"],
    },
    "maagar_mohot": {
        "earliest_imported_campaign": "knesset-18",
        "note": "Maagar Mohot continuity predates 2009. The reviewed 2006 election archive contains a Maagar Mohot projection totaling 119 seats, so it is documented but not repaired or imported.",
        "references": ["https://en.wikipedia.org/wiki/2006_Israeli_legislative_election"],
    },
    "direct_polls_shared": {
        "earliest_imported_campaign": "knesset-21",
        "note": "Historical Direct Polls rows are stored only as shared Filber/Sharon history and feed both current entities through the configured discounted prior.",
        "references": ["https://themadad.com/english/poll-accuracy-2022/"],
    },
}

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
    ("maagar_mohot", re.compile(r"\bma['’]?a?gar\s+mo(?:h|ch)ot\b|\bmaagar\s+mo(?:h|ch)ot\b|\bmaariv/maagar\b", re.I)),
    ("midgam_geva", re.compile(r"\bmidgam(?:\s+research)?\b|\bmeno\s+geva\b|\bmanu\s+geva\b", re.I)),
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


def parse_english_date(value: str, election_date: str, year_hint: int | None = None) -> str:
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
            year = year_hint if year_hint is not None else (election.year if parsed.month <= election.month else election.year - 1)
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
    # Some Wikipedia rows encode a seat projection together with the vote share,
    # e.g. "4(3.9%)". Keep the leading seat count. A pure percentage such as
    # "(3.1%)" means the party is below threshold and therefore has zero seats.
    seat_with_share = re.fullmatch(r"(\d+(?:\.\d+)?)\s*\([^)]*%\)", s)
    if seat_with_share:
        return float(seat_with_share.group(1))
    if "%" in s:
        return 0.0
    if allow_other_text:
        return _parse_other_text(s)
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    raise ValueError(f"unparseable seat cell {value!r}")



# Header-driven parsing lets us keep defensible polls from before the final
# candidate-list deadline. Wikipedia repeats a "Date / Polling firm / ..."
# header whenever the party configuration changes; we switch schemas at those
# boundaries instead of applying one final-list column order to the whole table.
_AGGREGATE_HEADER_TOKENS = {
    "gov", "government", "coalition", "opposition", "lead", "majority",
    "left", "right", "l", "r", "c", "bloc", "blocks", "total",
}


def _header_token(value: str) -> str:
    s = normalize(value).lower()
    s = s.replace("’", "'").replace("–", "-").replace("—", "-").replace("&", " and ")
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9+']+", " ", s)
    return " ".join(s.split()).strip()


def _party_concept(value: str) -> str | None:
    t = _header_token(value)
    compact = re.sub(r"[^a-z0-9]", "", t)
    if not compact:
        return None

    # Most-specific combined-list labels first.
    if "laborgeshermeretz" in compact:
        return "labor_gesher_meretz"
    if "laborgesher" in compact:
        return "labor_gesher"
    if "likud" in compact and ("beiteinu" in compact or "beitenu" in compact):
        return "likud_beiteinu"
    if ("raam" in compact or "ual" in compact) and "taal" in compact:
        return "raam_taal"
    if "raam" in compact and "balad" in compact:
        return "raam_balad"
    if "hadash" in compact and "taal" in compact:
        return "hadash_taal"
    if "labor" in compact and "meretz" in compact:
        return "labor_meretz"
    if ("jewishhome" in compact or "habayithayehudi" in compact) and "nationalunion" in compact:
        return "jewish_home_national_union"
    if (
        ("religiouszion" in compact and ("otzma" in compact or "noam" in compact))
        or ("rzp" in compact and "oy" in compact)
    ):
        return "religious_zionism"
    if ("jewishhome" in compact or "habayithayehudi" in compact) and ("tkuma" in compact or "otzma" in compact):
        return "urwp"
    if (
        ("yeshatid" in compact and ("hosen" in compact or "israelresilience" in compact))
        or "bluewhite" in compact
        or "blueandwhite" in compact
        or compact in {"bw", "bandw"}
    ):
        return "blue_white"
    if "nationalunity" in compact:
        return "national_unity"
    if "zionistunion" in compact:
        return "zionist_union"
    if "democraticunion" in compact:
        return "democratic_union"
    if "democraticisrael" in compact:
        return "democratic_israel"
    if "jointlist" in compact:
        return "joint_list"
    if "newhope" in compact:
        return "new_hope"
    if "newright" in compact:
        return "new_right"
    if "new economic" in t or compact in {"nep", "neweconomicparty"}:
        return "new_economic"
    if "religiouszion" in compact or compact in {"rz", "rzp"}:
        return "religious_zionism"
    if "unitedright" in compact or "rightwingpart" in compact or compact == "urwp":
        return "urwp"
    if "yisraelbeiteinu" in compact or "yisraelbeitenu" in compact or compact in {"yb", "israelourhome"}:
        return "yisrael_beiteinu"
    if "unitedtorah" in compact or compact == "utj":
        return "utj"
    if "yeshatid" in compact:
        return "yesh_atid"
    if "hosen" in compact or "israelresilience" in compact:
        return "hosen"
    if compact in {"taal", "taalparty"}:
        return "taal"
    if compact in {"raam", "raam"}:
        return "raam"
    if "balad" in compact:
        return "balad"
    if "hadash" in compact:
        return "hadash"
    if "otzma" in compact or compact == "oy":
        return "otzma"
    if compact == "noam" or compact.startswith("noam"):
        return "noam"
    if "jewishhome" in compact or "habayithayehudi" in compact or compact == "jh":
        return "jewish_home"
    if "nationalunion" in compact or compact == "tkuma":
        return "national_union"
    if "yamina" in compact:
        return "yamina"
    if "kulanu" in compact:
        return "kulanu"
    if "meretz" in compact:
        return "meretz"
    if "labor" in compact or "labour" in compact or compact == "emet":
        return "labor"
    if "hatnuah" in compact or compact == "hatn":
        return "hatnuah"
    if "gesher" in compact:
        return "gesher"
    if "telem" in compact:
        return "telem"
    if "israelis" in compact:
        return "israelis"
    if "tnufa" in compact:
        return "tnufa"
    if "likud" in compact:
        return "likud"
    if "shas" in compact:
        return "shas"
    if "zehut" in compact:
        return "zehut"
    if "yachad" in compact:
        return "yachad"
    if "kadima" in compact:
        return "kadima"
    if "amshalem" in compact:
        return "am_shalem"
    if compact in {"gil", "pensioners"}:
        return "gil"
    if "independence" in compact or "atzmaut" in compact:
        return "independence"
    if "greens" in compact or compact == "greenparty":
        return "greens"
    if compact == "other":
        return "other"
    return None


_ELECTION_CONCEPT_TARGETS: dict[str, dict[str, str]] = {
    "knesset-25": {
        "likud": "likud", "yesh_atid": "yesh_atid", "blue_white": "national_unity",
        "new_hope": "national_unity", "national_unity": "national_unity",
        "shas": "shas", "jewish_home": "jewish_home", "labor": "labor", "utj": "utj",
        "yisrael_beiteinu": "yisrael_beiteinu", "religious_zionism": "religious_zionism",
        "otzma": "religious_zionism", "noam": "religious_zionism",
        "hadash_taal": "hadash_taal", "taal": "hadash_taal", "hadash": "hadash_taal",
        "meretz": "meretz", "raam": "raam", "balad": "balad",
        "joint_list": "joint_list_pre_split",
    },
    "knesset-24": {
        "likud": "likud", "yesh_atid": "yesh_atid", "blue_white": "blue_white",
        "joint_list": "joint_list", "taal": "joint_list", "hadash": "joint_list",
        "balad": "joint_list", "shas": "shas", "utj": "utj",
        "yisrael_beiteinu": "yisrael_beiteinu", "meretz": "meretz", "raam": "raam",
        "yamina": "yamina", "new_hope": "new_hope", "labor": "labor",
        "religious_zionism": "religious_zionism", "otzma": "religious_zionism",
        "noam": "religious_zionism", "new_economic": "new_economic",
        "gesher": "likud", "jewish_home": "legacy_jewish_home",
        "telem": "legacy_telem", "israelis": "legacy_israelis", "tnufa": "legacy_tnufa",
    },
    "knesset-23": {
        "blue_white": "blue_white", "likud": "likud", "joint_list": "joint_list",
        "hadash_taal": "joint_list", "raam_balad": "joint_list",
        "labor": "labor_gesher_meretz", "labor_gesher": "labor_gesher_meretz",
        "meretz": "labor_gesher_meretz", "democratic_union": "labor_gesher_meretz",
        "labor_meretz": "labor_gesher_meretz", "labor_gesher_meretz": "labor_gesher_meretz",
        "shas": "shas", "yisrael_beiteinu": "yisrael_beiteinu", "utj": "utj",
        "yamina": "yamina", "new_right": "yamina", "jewish_home": "yamina",
        "national_union": "yamina", "urwp": "yamina", "otzma": "otzma",
    },
    "knesset-22": {
        "likud": "likud", "kulanu": "likud", "blue_white": "blue_white",
        "joint_list": "joint_list", "hadash_taal": "joint_list", "raam_balad": "joint_list",
        "hadash": "joint_list", "taal": "joint_list", "raam": "joint_list", "balad": "joint_list",
        "shas": "shas", "utj": "utj", "yamina": "yamina", "new_right": "yamina",
        "urwp": "yamina", "jewish_home": "yamina", "national_union": "yamina",
        "labor": "labor_gesher", "gesher": "labor_gesher", "labor_gesher": "labor_gesher",
        "yisrael_beiteinu": "yisrael_beiteinu",
        "democratic_union": "democratic_union", "democratic_israel": "democratic_union",
        "meretz": "democratic_union", "greens": "democratic_union",
        "zehut": "zehut", "otzma": "otzma",
    },
    "knesset-21": {
        "likud": "likud", "labor": "labor", "blue_white": "blue_white",
        "yesh_atid": "blue_white", "hosen": "blue_white", "telem": "blue_white",
        "kulanu": "kulanu", "joint_list": "joint_list_pre_split",
        "hadash_taal": "hadash_taal", "hadash": "hadash_taal", "taal": "hadash_taal",
        "raam_balad": "raam_balad", "raam": "raam_balad", "balad": "raam_balad",
        "shas": "shas", "utj": "utj", "urwp": "urwp", "jewish_home": "urwp",
        "national_union": "urwp", "otzma": "urwp", "yisrael_beiteinu": "yisrael_beiteinu",
        "meretz": "meretz", "new_right": "new_right", "gesher": "gesher", "zehut": "zehut",
        "hatnuah": "legacy_hatnuah",
    },
    "knesset-20": {
        "likud": "likud", "yisrael_beiteinu": "yisrael_beiteinu", "yesh_atid": "yesh_atid",
        "labor": "zionist_union", "hatnuah": "zionist_union", "zionist_union": "zionist_union",
        "jewish_home": "jewish_home", "national_union": "jewish_home",
        "shas": "shas", "utj": "utj", "meretz": "meretz",
        "joint_list": "joint_list", "hadash": "joint_list", "balad": "joint_list",
        "raam_taal": "joint_list", "raam": "joint_list", "taal": "joint_list",
        "yachad": "yachad", "otzma": "yachad", "kulanu": "kulanu",
    },
    "knesset-19": {
        "kadima": "kadima", "likud": "likud_beiteinu", "yisrael_beiteinu": "likud_beiteinu",
        "likud_beiteinu": "likud_beiteinu", "labor": "labor", "shas": "shas", "utj": "utj",
        "jewish_home": "jewish_home", "national_union": "jewish_home",
        "raam_taal": "ual_taal", "raam": "ual_taal", "taal": "ual_taal",
        "hadash": "hadash", "balad": "balad", "meretz": "meretz", "yesh_atid": "yesh_atid",
        "otzma": "otzma", "am_shalem": "am_shalem", "hatnuah": "hatnuah",
        "independence": "legacy_independence",
    },
    "knesset-18": {
        "kadima": "kadima", "labor": "labor", "shas": "shas", "likud": "likud",
        "yisrael_beiteinu": "yisrael_beiteinu", "raam_taal": "ual_taal",
        "raam": "ual_taal", "taal": "ual_taal", "hadash": "hadash", "balad": "balad",
        "jewish_home": "jewish_home", "national_union": "national_union",
        "jewish_home_national_union": "jewish_home_national_union_pre_split",
        "gil": "gil", "utj": "utj", "meretz": "meretz", "greens": "greens",
        "other": "other_nonwinning",
    },
}


def _target_for_header(election_id: str, value: str) -> str | None:
    concept = _party_concept(value)
    if concept is None:
        return None
    return _ELECTION_CONCEPT_TARGETS.get(election_id, {}).get(concept)


def _schema_from_header(row: list[str], source: dict[str, Any], election_id: str) -> dict[str, Any] | None:
    if not row:
        return None
    tokens = [_header_token(c) for c in row]
    pollster_column = next(
        (i for i, t in enumerate(tokens) if "polling firm" in t or t == "pollster"),
        None,
    )
    if pollster_column is None:
        return None
    outlet_column = next(
        (i for i, t in enumerate(tokens) if t in {"publisher", "media", "outlet"}),
        None,
    )
    party_columns: list[tuple[int, str]] = []
    for idx, cell in enumerate(row):
        if idx == 0 or idx == pollster_column or idx == outlet_column:
            continue
        target = _target_for_header(election_id, cell)
        if target:
            party_columns.append((idx, target))
    if len(party_columns) < 5:
        return None
    return {
        "pollster_column": pollster_column,
        "outlet_column": outlet_column,
        "party_columns": party_columns,
    }


def _fallback_schema(source: dict[str, Any]) -> dict[str, Any]:
    meta_columns = int(source["meta_columns"])
    pollster_column = int(source["pollster_column"])
    outlet_column = None
    if meta_columns >= 3:
        outlet_column = 1 if pollster_column == 2 else 2
    return {
        "pollster_column": pollster_column,
        "outlet_column": outlet_column,
        "party_columns": [
            (meta_columns + idx, party_id)
            for idx, party_id in enumerate(source["party_order"])
        ],
    }


def _comparison_groups_for_poll(
    election_id: str,
    poll_date: date,
    parties: dict[str, int | float],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []

    def collapse(key: str, components: list[str]) -> None:
        total = sum(float(parties.pop(component, 0)) for component in components)
        if total:
            parties[key] = int(total) if total.is_integer() else total
        groups.append({"key": key, "actual_components": components})

    if election_id == "knesset-25" and "joint_list_pre_split" in parties:
        groups.append({
            "key": "joint_list_pre_split",
            "actual_components": ["hadash_taal", "balad"],
        })
    if election_id == "knesset-24" and poll_date < date(2021, 1, 28):
        if "joint_list" in parties or "raam" in parties:
            collapse("joint_list_pre_raam_split", ["joint_list", "raam"])
    if election_id == "knesset-21" and "joint_list_pre_split" in parties:
        groups.append({
            "key": "joint_list_pre_split",
            "actual_components": ["hadash_taal", "raam_balad"],
        })
    if election_id == "knesset-18" and "jewish_home_national_union_pre_split" in parties:
        groups.append({
            "key": "jewish_home_national_union_pre_split",
            "actual_components": ["jewish_home", "national_union"],
        })
    return groups


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
    diag.setdefault("pre_final_normalized_rows", 0)

    polls: list[dict[str, Any]] = []
    election_day = date.fromisoformat(ELECTIONS[election_id]["date"])
    final_lists_from = date.fromisoformat(source["valid_from"])
    tables = _source_tables(source_text, source)
    diag["tables_matched"] += len(tables)

    for table in tables:
        current_year = election_day.year
        schema = _schema_from_header(table[0], source, election_id) or _fallback_schema(source)

        for row in table[1:]:
            if not row:
                continue

            # Wikipedia repeats headers inside a table whenever the party/list
            # configuration changes. Switch parsing schema at that boundary.
            replacement_schema = _schema_from_header(row, source, election_id)
            if replacement_schema is not None:
                schema = replacement_schema
                continue

            first_cell = normalize(row[0])
            if re.fullmatch(r"(?:19|20)\d{2}", first_cell):
                current_year = int(first_cell)
                continue
            try:
                poll_date_s = parse_english_date(first_cell, ELECTIONS[election_id]["date"], current_year)
            except ValueError:
                continue
            poll_date = date.fromisoformat(poll_date_s)
            if re.search(r"\b(?:19|20)\d{2}\b", first_cell):
                current_year = poll_date.year
            if poll_date >= election_day:
                diag["skipped_rows"].append({"reason": "election_day_or_future", "row": row[:6], "date": poll_date_s})
                continue

            pollster_column = int(schema["pollster_column"])
            if len(row) <= pollster_column:
                diag["malformed_rows"].append({"reason": "missing_pollster_cell", "row": row})
                continue
            raw_pollster = normalize(row[pollster_column])
            if re.search(r"\bstudents?\b", raw_pollster, re.I):
                diag["skipped_rows"].append({
                    "reason": "non_general_population", "pollster": raw_pollster,
                    "date": poll_date_s, "row": row,
                })
                continue
            pollster = resolve_pollster(raw_pollster)
            if pollster is None:
                if raw_pollster:
                    diag["unmatched_pollster_names"][raw_pollster] += 1
                continue
            lineage_start = date.fromisoformat(LINEAGE_STARTS[pollster])
            if poll_date < lineage_start:
                diag["skipped_rows"].append({
                    "reason": "before_lineage_cutoff", "pollster": raw_pollster,
                    "pollster_id": pollster, "date": poll_date_s, "row": row,
                })
                continue

            diag["matched_rows"] += 1
            parties: dict[str, int | float] = {}
            bad_cell = None
            missing_column = None
            for idx, party_id in schema["party_columns"]:
                if idx >= len(row):
                    missing_column = {"index": idx, "party": party_id}
                    break
                raw = row[idx]
                try:
                    value = parse_seat_cell(
                        raw,
                        allow_other_text=party_id == source.get("other_text_column"),
                    )
                except ValueError as exc:
                    bad_cell = {"party": party_id, "value": raw, "error": str(exc)}
                    break
                if value:
                    parties[party_id] = float(parties.get(party_id, 0)) + value
                elif party_id not in parties:
                    parties[party_id] = 0

            if missing_column:
                diag["malformed_rows"].append({
                    "reason": "too_few_columns", "pollster": raw_pollster, "date": poll_date_s,
                    "missing": missing_column, "actual": len(row), "row": row,
                })
                continue
            if bad_cell:
                diag["malformed_rows"].append({
                    "reason": "malformed_seat_cell", "pollster": raw_pollster, "date": poll_date_s,
                    **bad_cell, "row": row,
                })
                continue

            comparison_groups = _comparison_groups_for_poll(election_id, poll_date, parties)
            parties = {
                key: int(value) if float(value).is_integer() else value
                for key, value in parties.items()
            }
            total = sum(float(v) for v in parties.values())
            if abs(total - 120.0) > 0.001:
                diag["skipped_rows"].append({
                    "reason": "seat_total_not_120", "pollster": raw_pollster, "pollster_id": pollster,
                    "date": poll_date_s, "seat_total": total, "row": row,
                })
                continue

            outlet = None
            outlet_column = schema.get("outlet_column")
            if outlet_column is not None and outlet_column < len(row):
                outlet = normalize(row[outlet_column]) or None
            elif int(source["meta_columns"]) == 2:
                outlet = raw_pollster or None

            configuration = "final_lists" if poll_date >= final_lists_from else "pre_final_normalized"
            if configuration == "pre_final_normalized":
                diag["pre_final_normalized_rows"] += 1

            poll = {
                "pollster": pollster,
                "election": election_id,
                "date": poll_date_s,
                "source": source_url,
                "outlet": outlet,
                "source_pollster_name": raw_pollster,
                "party_configuration": configuration,
                "parties": parties,
            }
            if comparison_groups:
                poll["comparison_groups"] = comparison_groups
            polls.append(poll)
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
                summary = {
                    "tables_matched": diag.get("tables_matched"),
                    "matched_rows": diag.get("matched_rows"),
                    "pre_final_normalized_rows": diag.get("pre_final_normalized_rows"),
                    "malformed_rows": diag.get("malformed_rows", [])[:5],
                    "skipped_rows": diag.get("skipped_rows", [])[:5],
                    "unmatched_pollster_names": dict(diag.get("unmatched_pollster_names", {})),
                }
                raise RuntimeError(
                    f"no valid target-lineage 120-seat rows parsed for {source['election']}: {summary}"
                )
            all_polls.extend(rows)
            status = {
                "url": source["url"], "election": source["election"], "valid_from": source["valid_from"],
                "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
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

    raw = {
        "schema_version": 2,
        "demo_mode": False,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "builder": "scripts/build_historical_dataset.py",
            "source_policy": "Wikipedia election archives are the reproducible fallback; pre-final-list rows are retained only when their table schema can be normalized deterministically; TheMadad is a manual cross-check because it returns HTTP 403 in GitHub Actions.",
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
        "historical_coverage_notes": HISTORICAL_COVERAGE_NOTES,
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
