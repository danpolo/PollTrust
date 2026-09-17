#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from polltrust.demo_data import build_demo_raw
from polltrust.model import build_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/historical-polls.json")
    parser.add_argument("--output", default="data/historical-model.json")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Build the synthetic demo model explicitly. Production builds never fall back to demo data.",
    )
    args = parser.parse_args()

    if args.demo:
        raw = build_demo_raw()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            raise SystemExit(
                f"production historical input not found: {input_path}. "
                "Run scripts/build_historical_dataset.py first, or pass --demo explicitly."
            )
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        if raw.get("demo_mode"):
            raise SystemExit("refusing to build a production model from demo historical input")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_model(raw), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
