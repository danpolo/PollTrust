#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polltrust.adapters import (
    JsonFeedAdapter,
    RepositoryFixtureAdapter,
    Wikipedia2026PollingAdapter,
)
from polltrust.ingestion import merge_polls


def load_sources(path: Path):
    config = json.loads(path.read_text(encoding="utf-8"))
    adapters = []
    for source in config.get("sources", []):
        if not source.get("enabled", False):
            continue
        source_type = source["type"]
        if source_type == "json_feed":
            adapters.append(JsonFeedAdapter(source["name"], source["url"]))
        elif source_type == "repository_fixture":
            adapters.append(RepositoryFixtureAdapter(source["path"], source["name"]))
        elif source_type == "wikipedia_2026":
            adapters.append(
                Wikipedia2026PollingAdapter(
                    source["name"],
                    source["url"],
                    valid_from=source.get("valid_from", "2026-09-09"),
                )
            )
        else:
            raise ValueError(f"unsupported source type: {source_type}")
    return adapters


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/current-polls.json")
    parser.add_argument("--sources", default="data/sources.json")
    parser.add_argument("--election", default="data/election.json")
    args = parser.parse_args()

    path = Path(args.data)
    merged = json.loads(path.read_text(encoding="utf-8"))
    election = json.loads(Path(args.election).read_text(encoding="utf-8"))
    adapters = load_sources(Path(args.sources))

    if not adapters:
        print("No enabled poll sources; existing data left untouched.")
        return 0

    total_added = 0
    successful_sources = 0
    errors: list[str] = []

    for adapter in adapters:
        try:
            incoming = adapter.fetch()
            merged, added = merge_polls(merged, incoming, set(election["pollsters"]))
            total_added += added
            successful_sources += 1
            print(f"{adapter.name}: fetched {len(incoming)} valid polls, added {added}")
        except Exception as exc:
            errors.append(f"{adapter.name}: {exc}")
            print(f"WARNING {adapter.name}: {exc}", file=sys.stderr)

    if successful_sources:
        merged["last_successful_check"] = _now_iso()
        if total_added:
            merged["last_successful_update"] = merged["last_successful_check"]
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors and successful_sources == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
