"""CLI software checks only: no scientific experiment or new artifact."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/generate_unique_submission.py'


def test_archived_generator_help_is_read_only():
    result = subprocess.run([sys.executable, str(SCRIPT), '--help'],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert 'Current lane is CLOSED' in result.stdout
    assert 'would not prove' in result.stdout
    assert '--top-k' in result.stdout


def test_archived_generator_still_refuses_before_creating_outputs(tmp_path):
    destination = tmp_path / 'must-not-exist'
    result = subprocess.run(
        [sys.executable, str(SCRIPT), 'not-a-new-lane', 'software test',
         '--out', str(destination)], capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert 'no files changed' in result.stderr.lower()
    assert not destination.exists()
