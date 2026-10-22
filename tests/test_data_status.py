from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gems79.data_status import inspect_runtime_inputs


def _write_fixture(root: Path, files: dict[str, tuple[str, bytes]]) -> list[dict]:
    manifest_rows = []
    receipt_rows = []
    raw_root = root / "data/raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    for file_id, (dest, payload) in files.items():
        target = raw_root / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        checksum = hashlib.sha256(payload).hexdigest()
        row = {"id": file_id, "dest": dest, "sha256": checksum, "bytes": len(payload)}
        manifest_rows.append(row)
        receipt_rows.append({**row, "status": "restored"})
    manifest = {"schema_version": 1, "files": manifest_rows}
    receipt = {"schema_version": 1, "verified_files_count": len(receipt_rows), "files": receipt_rows}
    (root / "registry").mkdir(parents=True, exist_ok=True)
    (root / "registry/data_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "data/restore_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return manifest_rows


def test_runtime_data_status_verifies_current_files_and_separates_old_receipt(tmp_path):
    _write_fixture(tmp_path, {
        "training_features": ("training_features.tif", b"pinned features"),
        "labels": ("labels.tif", b"pinned labels"),
        "existing_faults": ("existing_faults.tif", b"pinned faults"),
        "sample_submission": ("sample_submission.tif", b"pinned sample"),
        "external_fixture": ("external/fixture.bin", b"pinned external data"),
    })

    result = inspect_runtime_inputs(tmp_path)

    assert result["evidence_class"] == "RUNTIME-LOCAL-AVAILABILITY"
    assert result["verified_count"] == result["expected_count"] == 5
    assert result["training_supervision_ready"] is True
    assert result["core_pipeline_inputs_ready"] is True
    assert result["all_manifest_inputs_ready"] is True
    assert result["historical_restore_receipt"]["matches_manifest_metadata"] is True
    assert result["historical_restore_receipt"]["current_availability_proof"] is False
    assert all(row["status"] == "verified" for row in result["files"])


def test_missing_raw_files_are_not_inferred_from_historical_receipt(tmp_path):
    rows = _write_fixture(tmp_path, {
        "training_features": ("training_features.tif", b"pinned features"),
        "labels": ("labels.tif", b"pinned labels"),
    })
    for row in rows:
        (tmp_path / "data/raw" / row["dest"]).unlink()

    result = inspect_runtime_inputs(tmp_path)

    assert result["state"] == "blocked_missing_inputs"
    assert result["verified_count"] == 0 and result["missing_count"] == 2
    assert result["training_supervision_ready"] is False
    assert result["all_manifest_inputs_ready"] is False
    assert result["historical_restore_receipt"]["matches_manifest_metadata"] is True
    assert result["historical_restore_receipt"]["current_availability_proof"] is False
    assert [row["status"] for row in result["files"]] == ["missing", "missing"]


def test_runtime_status_detects_hash_and_size_mismatch(tmp_path):
    _write_fixture(tmp_path, {"training_features": ("training_features.tif", b"original")})
    (tmp_path / "data/raw/training_features.tif").write_bytes(b"modified bytes")

    result = inspect_runtime_inputs(tmp_path)

    assert result["state"] == "blocked_mismatch_or_invalid_path"
    assert result["verified_count"] == 0 and result["mismatch_count"] == 1
    assert result["files"][0]["status"] == "mismatch"
    assert result["files"][0]["sha256_matches"] is False
    assert result["files"][0]["size_matches"] is False


@pytest.mark.parametrize("destination", [
    "../outside.bin", "nested//file.bin", "nested/./file.bin", "C:/outside.bin", "nested\\\\file.bin",
])
def test_runtime_status_rejects_unsafe_manifest_paths(tmp_path, destination):
    (tmp_path / "registry").mkdir()
    manifest = {
        "schema_version": 1,
        "files": [{
            "id": "escape",
            "dest": destination,
            "sha256": hashlib.sha256(b"x").hexdigest(),
            "bytes": 1,
        }],
    }
    (tmp_path / "registry/data_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe data manifest destination"):
        inspect_runtime_inputs(tmp_path)


def test_runtime_status_rejects_symlink_outside_data_root(tmp_path):
    rows = _write_fixture(tmp_path, {"escape": ("escape.bin", b"placeholder")})
    target = tmp_path / "outside.bin"
    target.write_bytes(b"pinned data placed outside raw root")
    link = tmp_path / "data/raw/escape.bin"
    link.unlink()
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable in test environment: {exc}")

    result = inspect_runtime_inputs(tmp_path)

    assert rows[0]["dest"] == "escape.bin"
    assert result["files"][0]["status"] == "unsafe_path"
    assert result["other_invalid_count"] == 1
    assert result["all_manifest_inputs_ready"] is False


def test_runtime_status_handles_symlink_loop_as_unreadable(tmp_path):
    _write_fixture(tmp_path, {"loop": ("loop.bin", b"placeholder")})
    link = tmp_path / "data/raw/loop.bin"
    link.unlink()
    try:
        link.symlink_to(link.name)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable in test environment: {exc}")

    result = inspect_runtime_inputs(tmp_path)

    assert result["files"][0]["status"] == "unreadable"
    assert result["files"][0]["error_type"] == "RuntimeError"
    assert result["other_invalid_count"] == 1


def test_current_checkout_runtime_status_is_machine_readable():
    root = Path(__file__).resolve().parents[1]
    result = inspect_runtime_inputs(root)

    assert result["expected_count"] == 13
    assert result["historical_restore_receipt"]["matches_manifest_metadata"] is True
    assert result["historical_restore_receipt"]["current_availability_proof"] is False
    assert len(result["files"]) == result["expected_count"]
