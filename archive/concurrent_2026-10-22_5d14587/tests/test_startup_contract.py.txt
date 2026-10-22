"""Repository-startup instructions must stay branch-neutral and merge-clean."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_project import startup_contract_checks


def test_active_startup_contract_is_resolved_and_branch_neutral():
    checks = startup_contract_checks(ROOT)
    assert all(checks.values()), checks


def test_current_review_records_three_passes_and_negative_submission_decision():
    review = (ROOT / 'reports/session_review_a23a7367.md').read_text()
    for heading in ('Pass 1 —', 'Pass 2 —', 'Pass 3 —'):
        assert heading in review
    assert 'DO NOT SUBMIT' in review
    assert 'not generate a new TIFF' in review


def test_readme_retains_the_complete_original_prompt():
    readme = (ROOT / 'README.md').read_text()
    marker = '## Original project prompt'
    assert marker in readme
    prompt = readme.split(marker, 1)[1]
    for required in ('Pass 1:', 'Pass 2:', 'Pass 3:', 'create a pull request', 'Verify no hallucinations'):
        assert required in prompt
    assert len(prompt) > 5000


@pytest.mark.parametrize('contents', [
    '# instructions\n<<<<<<< HEAD\nold\n=======\nnew\n>>>>>>> main\n',
    '# instructions\nUse arena/12345678-old-session\n',
    '# instructions\nNo session metadata here\n',
])
def test_startup_contract_rejects_conflicts_or_pinned_branches(tmp_path, contents):
    (tmp_path / 'AGENTS.md').write_text(contents)
    checks = startup_contract_checks(tmp_path)
    assert checks['startup_contract_exists']
    assert not all(checks.values())
