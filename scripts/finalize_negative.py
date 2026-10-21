#!/usr/bin/env python3
"""Package an already-computed rejected surface; never continue an experiment.

This is reporting after a stop, not dot placement, fitting, tuning or a second
experiment. No HOLDOUT-DTI or canary result is invented for a blocked stage.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems57 import evaluate_holdout as evaluator
from gems57.grid import load_grid
from gems57.submission_writer import write_submission
from gems79.novelty import audit


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def finalize(surface_audit=None):
    if (ROOT / 'run_card.json').exists():
        raise FileExistsError('The negative run has already been finalized; use verify_project.py to re-check it.')
    prereg = json.loads((ROOT / 'registry/preregistration.json').read_text())
    ph = digest(ROOT / 'registry/preregistration.json')
    if ph != (ROOT / 'evidence/preregistration_sha256.txt').read_text().strip():
        raise ValueError('Preregistration drift')
    manifest = json.loads((ROOT / 'evidence/feature_cache.json').read_text())
    expected = next(r['sha256'] for r in manifest['files'] if r['name'] == 'fabric_offset_surface')
    cached = ROOT / '.cache/g79/fabric_offset_surface.npy'
    if digest(cached) != expected:
        raise ValueError('Previously computed surface bytes changed')
    grid = load_grid(ROOT / 'data/reference')
    surface = np.load(cached)
    before = surface_audit or audit(ROOT, surface, grid, phase='surface')
    if not before['duplicate'] or not before['certificate']['universal_overlap_blocker']:
        raise ValueError('This reporting command is only for a certified pre-placement duplicate stop')
    state_path = ROOT / 'evidence/experiment_state.json'
    state = json.loads(state_path.read_text())
    state.update(phase='duplicate_preplacement_stop', stopped=True,
                 stop_reason='universal_literal_overlap_witness',
                 scientific_stopped_utc=datetime.now(timezone.utc).isoformat(),
                 holdout_evaluations_performed=0, final_dot_placements_performed=0)
    write(state_path, state)
    # Retain the existing surface as a strictly research-only downloadable TIFF.
    # Masking mapped pixels/footprint is serialization policy, not a new detector.
    prediction = surface.astype(np.float32, copy=True)
    prediction[~grid.footprint | grid.catalogue] = 0
    name = f'g79-fabric-offset-surface-E1-20261021-{expected[:8]}-DO-NOT-SUBMIT'
    note = 'G79 fabric-offset surface E1; automatic duplicate stop before holdout or dots. Research only; do not submit.'
    path = ROOT / 'docs/downloads' / (name + '.tif')
    receipt = write_submission(
        path, prediction, ROOT / 'data/reference/sample_submission.tif', grid.footprint,
        catalogue=grid.catalogue, name=name, note=note,
        metadata={'lane': prereg['lane'], 'diagnostic_surface_only': True,
                  'surface_cache_sha256': expected, 'human_inspection_required': False,
                  'warning': 'DO NOT SUBMIT: literal novelty stop; no holdout or canary clearance'})
    # Report the serialized artifact too. This does not resume scientific work.
    final = audit(ROOT, prediction, grid, phase='final_artifact')
    registry_receipt = json.loads((ROOT / 'registry/registry_receipt.json').read_text())
    byte_distinct = receipt['sha256'] not in {r.get('sha256') for r in registry_receipt['files']}
    absent = dict(evidence_class='HOLDOUT-DTI', evaluator_version=evaluator.VERSION,
                  status='NOT RUN: mandatory pre-placement duplicate stop',
                  dti=None, ci95=None, withheld_positive_pixels=None)
    card = {
        'schema_version': 'gems79-run-card-v1',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'branch': 'arena/f61b17a2-gemsdoe79', 'lane': prereg['lane'],
        'hypothesis': prereg['hypothesis'], 'mechanism': prereg['mechanism'],
        'named_non_fault_process': prereg['named_non_fault_mimic'],
        'holdout_dti': absent, 'current_best_holdout_beaten': False,
        'leakage_canary': {'status': 'NOT RUN: stopped before any result was trusted',
                           'features_cleared': 0, 'required_threshold': .90,
                           'passed': False, 'auc': None},
        'correlation_overlap_vs_registry': {
            'surface_before_placement': {k:v for k,v in before.items() if k != 'shared_result'},
            'written_surface_after_export': {k:v for k,v in final.items() if k != 'shared_result'},
            'final_dots': {'status': 'NOT GENERATED: stopped before placement'}},
        'raster_sha256': receipt['sha256'], 'surface_cache_sha256': expected,
        'byte_distinct_from_verified_registry': byte_distinct,
        'byte_identity_registry_files': registry_receipt['verified'],
        'protocol_unique': False,
        'validator_output': {'shared_validator': receipt['validator'],
                             'reference_grid_validator': receipt['template_report']},
        'submission_name': name, 'submission_note': note,
        'submission_file': str(path.relative_to(ROOT)),
        'zip_file': str(path.with_suffix('.zip').relative_to(ROOT)),
        'artifact_kind': 'newly computed continuous research surface; not a cleared competition candidate',
        'positive_pixels': receipt['validator']['emitted_positive_pixels'],
        'final_dot_placements_performed': 0, 'experiment_count': 1,
        'max_experiments': 3, 'max_hours': 2,
        'ok_to_download': True, 'ok_to_submit': False,
        'human_intervention_needed_for_this_verdict': False,
        'promoted': False, 'approved_for_weekly_slot': False,
        'submission_slots_used': 0, 'organizer_submission_receipt': None,
        'verdict': 'negative', 'stop_reason': 'duplicate_surface_universal_overlap',
        'blockers': [
            'Literal positive-support overlap is 1.0 against a verified whole-footprint registry witness; threshold is 0.70.',
            'No candidate, irrespective of method, can pass that witness without changing the protocol or registry definition; no exemption was introduced.',
            'Canaries and HOLDOUT-DTI were not run after the mandatory stop; no performance improvement is established.',
            'Mirrored input consistency is verified, but organizer-origin byte identity is not authenticated.',
            'Current signed-in weekly capacity and selector approval are unavailable; no upload was attempted.'
        ],
        'source_feature_stack_sha256': manifest['source_feature_stack_sha256'],
        'preregistration_sha256': ph,
        'shared_template_commit': json.loads((ROOT / 'registry/template_pin.json').read_text())['commit']}
    write(ROOT / 'run_card.json', card)
    write(ROOT / 'evidence/run_card.json', card)
    state.update(phase='stopped_negative_reported', finished_utc=card['generated_utc'],
                 submission_file=card['submission_file'])
    write(state_path, state)
    print(json.dumps({k:card[k] for k in ('verdict','stop_reason','submission_file','raster_sha256','ok_to_submit')}, indent=2))
    return card


if __name__ == '__main__':
    finalize()
