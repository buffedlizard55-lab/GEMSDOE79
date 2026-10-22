"""Fail-closed protection for terminal scientific lanes, not a promotion gate.

Software audits may read frozen evidence. Scientific runners and packaging must
not replace it after a duplicate/negative stop. There is deliberately no force
flag: a new lane requires its own prospectively reviewed registration/runner.
"""
from __future__ import annotations

import json
from pathlib import Path


class LaneClosedError(RuntimeError):
    """A mutating operation attempted to restart a terminal or unknown lane."""


def require_open_lane(root: Path, lane: str) -> None:
    """Reject missing, malformed, mismatched or terminal canonical run cards.

    Only explicit nonterminal lifecycle states are eligible to proceed. This
    guard grants neither scientific validity nor permission to submit. It must
    run before loading bulk inputs or writing any new evidence/artifact.
    """
    try:
        card = json.loads((Path(root) / 'run_card.json').read_text())
    except (OSError, ValueError) as exc:
        raise LaneClosedError(f'{lane}: cannot establish an open lane; no files changed') from exc
    if not isinstance(card, dict) or card.get('lane') != lane:
        raise LaneClosedError(f'{lane}: canonical lane missing or mismatched; no files changed')
    if (card.get('verdict') not in ('pending', 'in_progress') or
            card.get('stop_reason') or card.get('stopped') is True):
        raise LaneClosedError(
            f'{lane}: lane is closed ({card.get("verdict", "unknown")}); '
            'do not restart, retune, or repackage it. Audit the frozen evidence instead. '
            'No files changed.'
        )
