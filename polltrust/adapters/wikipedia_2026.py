from __future__ import annotations

import html
import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.request import Request, urlopen

from .base import PollSourceAdapter


PARTY_ORDER = [
    "likud",
    "together",
    "rzp_zehut",
    "otzma",
    "blue_white",
    "shas",
    "utj",
    "yisrael_beiteinu",
    "raam",
    "joint_list",
    "democrats",
    "yashar",
    "reservists_nep",
    "amcha_yisrael",
    "haredi_public",
    "others",
]

DEFAULT_VALID_FROM = "2026-09-09"

ALLOWED_OUTLETS = {
    "Channel 13",
    "Channel 14",
    "Channel 16",
    "HaHadashot 12",
    "i24 News",
    "Israel Hayom",
    "Kan 11",
    "Maariv",
    "Walla",
    "Zman Yisrael",
}

POLLSTER_ALIASES = {
    "midgam r&c": "midgam_geva",
    "kantar": "kantar_hasid",
    "lri+p4a": "lazar_research",
    "maagar mochot": "maagar_mohot",
    "direct polls": "direct_polls_sharon",
    "sf+nd": "next_data_filber",
    "mp+tm+sn+a": "hamadad_consortium",
    "mp, m, sn, a": "hamadad_consortium",
    "yossi tatika": "tatika",
}


def normalize(value: Any) -> str:
    text = html.unescape(str(value)).replace("\u200f", "").replace("\u200e", "")
    text = re.sub(r"\[\s*\d+[a-z]?\s*\]", "", text, flags=re.I)
    return " ".join(text.split()).strip()


class _TableParser(HTMLParser):
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


def resolve_pollster(value: str) -> str | None:
    return POLLSTER_ALIASES.get(normalize(value).lower())


def parse_poll_date(value: str, year: int = 2026) -> str:
    s = normalize(value).replace("–", "-").replace("—", "-")
    s = re.sub(r"\([^)]*\)", "", s).strip()
    range_match = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]{3,9})$", s)
    if range_match:
        s = f"{range_match.group(2)} {range_match.group(3)}"
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    for fmt in ("%d %b", "%d %B"):
        try:
            parsed = datetime.strptime(s, fmt)
            return parsed.replace(year=year).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"unsupported poll date {value!r}")


def parse_seat_cell(value: str) -> int:
    s = normalize(value).replace(",", "")
    if not s or s.lower() in {"-", "–", "—", "n/a", "—n/a", "-n/a"}:
        return 0
    leading_seats = re.fullmatch(r"(\d+)\s*\([^)]*%\)", s)
    if leading_seats:
        return int(leading_seats.group(1))
    if "%" in s:
        return 0
    if re.fullmatch(r"\(\d+(?:\.\d+)?\)", s):
        return 0
    if re.fullmatch(r"\d+", s):
        return int(s)
    raise ValueError(f"unsupported seat cell {value!r}")


def _matching_tables(source_text: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(source_text)
    markers = [
        "fieldwork",
        "polling firm",
        "publisher",
        "sample",
        "likud",
        "together",
        "haredi public",
        "gov.",
    ]
    matches: list[list[list[str]]] = []
    for table in parser.tables:
        header_blob = " ".join(" ".join(row) for row in table[:4]).lower()
        if all(marker in header_blob for marker in markers):
            matches.append(table)
    return matches


def parse_current_polling_page(
    source_text: str,
    source_url: str,
    *,
    valid_from: str = DEFAULT_VALID_FROM,
) -> list[dict[str, Any]]:
    cutoff = date.fromisoformat(valid_from)
    rows: list[dict[str, Any]] = []

    for table in _matching_tables(source_text):
        for raw_row in table[1:]:
            if len(raw_row) < 4:
                continue
            try:
                poll_date_s = parse_poll_date(raw_row[0])
            except ValueError:
                continue
            poll_date = date.fromisoformat(poll_date_s)
            if poll_date < cutoff:
                continue

            pollster = resolve_pollster(raw_row[1])
            if pollster is None:
                continue

            needed = 4 + len(PARTY_ORDER)
            if len(raw_row) < needed:
                continue

            parties: dict[str, int] = {}
            malformed = False
            for idx, party_id in enumerate(PARTY_ORDER):
                try:
                    parties[party_id] = parse_seat_cell(raw_row[4 + idx])
                except ValueError:
                    malformed = True
                    break
            if malformed or sum(parties.values()) != 120:
                continue

            outlet = normalize(raw_row[2])
            if outlet not in ALLOWED_OUTLETS:
                continue

            sample_size = None
            sample_text = normalize(raw_row[3]).replace(",", "")
            if sample_text.isdigit():
                sample_size = int(sample_text)

            rows.append({
                "pollster": pollster,
                "date": poll_date_s,
                "source": source_url,
                "outlet": outlet,
                "source_pollster_name": normalize(raw_row[1]),
                "sample_size": sample_size,
                "parties": parties,
            })

    if not rows:
        raise ValueError("Wikipedia 2026 adapter parsed no valid post-list-closure target polls")

    rows.sort(key=lambda p: (p["date"], p["pollster"], p.get("outlet") or ""), reverse=True)
    return rows


class Wikipedia2026PollingAdapter(PollSourceAdapter):
    """Deterministic adapter for the main 2026 Israeli election mandate-poll table."""

    def __init__(
        self,
        name: str,
        url: str,
        *,
        valid_from: str = DEFAULT_VALID_FROM,
        timeout: int = 30,
    ) -> None:
        self.name = name
        self.url = url
        self.valid_from = valid_from
        self.timeout = timeout

    def fetch(self) -> list[dict[str, Any]]:
        request = Request(
            self.url,
            headers={
                "User-Agent": "PollTrust/1.0 (+https://github.com/danpolo/PollTrust)",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            source_text = response.read().decode("utf-8")
        if len(source_text) < 1000:
            raise ValueError(f"{self.name}: source returned suspiciously little HTML")
        return parse_current_polling_page(
            source_text,
            self.url,
            valid_from=self.valid_from,
        )
