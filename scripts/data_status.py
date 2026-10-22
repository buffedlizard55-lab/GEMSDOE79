#!/usr/bin/env python3
"""Report the current pinned-input availability under data/raw; never downloads data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems79.data_status import inspect_runtime_inputs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        help="Optionally write the JSON report to a new path (existing files are not overwritten)",
    )
    args = parser.parse_args()
    result = inspect_runtime_inputs(ROOT)
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.report:
        destination = args.report if args.report.is_absolute() else ROOT / args.report
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(serialized)
    print(serialized, end="")
    return 0 if result["all_manifest_inputs_ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
