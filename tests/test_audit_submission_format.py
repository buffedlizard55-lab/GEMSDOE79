"""Regression checks for scripts/audit_submission_format.py (read-only format facts)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / 'data/reference/sample_submission.tif'
EVIDENCE = ROOT / 'evidence/official_format_audit_20261022.json'


def _load_module():
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src'), str(ROOT / 'vendor')]
    import audit_submission_format as mod
    return mod


@pytest.mark.skipif(not OFFICIAL.exists(), reason='pinned official sample not restored')
def test_official_sample_uses_nan_outside_footprint():
    mod = _load_module()
    with rasterio.open(OFFICIAL) as src:
        a = src.read(1)
    facts = mod.describe(OFFICIAL, np.isfinite(a))
    assert facts['fill_convention'] == 'nan_outside'
    assert facts['in_range_0_1'] is True
    assert facts['epsg'] == 32611 and facts['shape'] == [3730, 3292]


@pytest.mark.skipif(not EVIDENCE.exists(), reason='audit evidence not generated')
def test_evidence_records_zero_fill_artifacts_and_witness_definition():
    rec = json.loads(EVIDENCE.read_text())
    assert rec['evidence_class'] == 'REPOSITORY-MEASUREMENT'
    assert rec['official_sample']['fill_convention'] == 'nan_outside'
    for art in rec['local_artifacts']:
        assert art['in_range_0_1'] is True
        assert art['nan_pixels'] == 0
        assert art['fill_convention'] == 'zero_outside'
    witness = rec['novelty_witness']
    if witness['status'] == 'measured':
        assert witness['fraction_of_footprint_with_positive_support'] == 1.0
    assert 'not portal acceptance' in rec['scope'].lower()
