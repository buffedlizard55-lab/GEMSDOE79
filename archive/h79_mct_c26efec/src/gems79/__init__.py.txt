"""GEMSDOE79 lane H79-MCT: Mapper-Continuity scarp Traces.

Thin lane-specific code on top of the unmodified shared template ``vendor/gems57``
(metric, hide-and-recover holdout, evaluator, submission writer, uniqueness gates).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANE = "H79-MCT"
__all__ = ["ROOT", "LANE"]
