"""Lane G79B-SDPT (2026-10-22): terrain-only scarp dipole-persistence + trace objects.

Preregistered in registry/preregistration_g79b.json before any experiment.
The 30-channel base stack and HGB training recipe reproduce the archived
H79-MCT lane (archive/h79_mct_c26efec/src/gems79/*.py.txt) as the CONTROL;
G79B adds explicit scarp-physics interaction channels and an object-level
trace reranking stage. Shared evaluator/writer/validator/uniqueness code in
vendor/gems57 is used unmodified.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANE = "G79B-SDPT"
