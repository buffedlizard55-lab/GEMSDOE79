#!/usr/bin/env python3
"""Exit 0 only for an approved slot candidate; exit 2 for a research-only file."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems79.status import submission_decision
from validate_submission import validate_path


def main():
    card = json.loads((ROOT / 'run_card.json').read_text())
    path = ROOT / card['submission_file']
    result = submission_decision(card, actual_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                  format_passed=validate_path(path)['format_passed'])
    print(json.dumps(result, indent=2))
    return 0 if result['ok_to_submit'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
