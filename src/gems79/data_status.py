"""Read-only inventory of the pinned runtime data files.

A historical restore receipt records what a prior process verified; it does not
prove that ignored data/raw files still exist in the current checkout. This
module checks only current local presence, size, and SHA-256 against the pinned
manifest. It never downloads, repairs, relocates, or authenticates organizer data.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


_CORE_TRAINING_IDS = ("training_features", "labels")
_CORE_PIPELINE_IDS = ("training_features", "labels", "existing_faults", "sample_submission")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _strict_json(raw: bytes) -> Any:
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key!r}")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_entries(root: Path) -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    manifest_path = root / "registry/data_manifest.json"
    raw = manifest_path.read_bytes()
    manifest = _strict_json(raw)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise ValueError("data manifest must be a JSON object with a files array")

    entries = manifest["files"]
    seen_ids: set[str] = set()
    seen_destinations: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"data manifest entry {index} must be an object")
        file_id = entry.get("id")
        destination = entry.get("dest")
        checksum = entry.get("sha256")
        if not isinstance(file_id, str) or not file_id:
            raise ValueError(f"data manifest entry {index} has no valid id")
        if file_id in seen_ids:
            raise ValueError(f"duplicate data manifest id: {file_id}")
        seen_ids.add(file_id)
        if not isinstance(destination, str) or not destination:
            raise ValueError(f"data manifest entry {file_id} has no valid dest")
        rel = PurePosixPath(destination)
        raw_parts = destination.split("/")
        if (rel.is_absolute() or ".." in raw_parts or "\\" in destination
                or any(part in ("", ".") for part in raw_parts)
                or re.match(r"^[A-Za-z]:", destination)):
            raise ValueError(f"unsafe data manifest destination for {file_id}: {destination!r}")
        normalized = rel.as_posix()
        if normalized in seen_destinations:
            raise ValueError(f"duplicate data manifest destination: {normalized}")
        seen_destinations.add(normalized)
        if not isinstance(checksum, str) or not _SHA256_RE.fullmatch(checksum):
            raise ValueError(f"invalid SHA-256 pin for {file_id}")
        size = entry.get("bytes")
        if size is not None and (type(size) is not int or size < 0):
            raise ValueError(f"invalid byte-size pin for {file_id}")
    return manifest, raw, entries


def _historical_receipt_summary(root: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    receipt_path = root / "data/restore_receipt.json"
    if not receipt_path.is_file():
        return {
            "available": False,
            "matches_manifest_metadata": False,
            "current_availability_proof": False,
        }
    try:
        receipt = _strict_json(receipt_path.read_bytes())
        receipt_files = receipt.get("files") if isinstance(receipt, dict) else None
        if not isinstance(receipt_files, list):
            raise ValueError("receipt files must be an array")
        receipt_by_id = {}
        for row in receipt_files:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                raise ValueError("receipt contains a malformed file record")
            if row["id"] in receipt_by_id:
                raise ValueError(f"duplicate receipt id: {row['id']}")
            receipt_by_id[row["id"]] = row
        manifest_by_id = {row["id"]: row for row in entries}
        consistent = set(receipt_by_id) == set(manifest_by_id)
        if consistent:
            for file_id, manifest_row in manifest_by_id.items():
                receipt_row = receipt_by_id[file_id]
                for field in ("dest", "sha256"):
                    if receipt_row.get(field) != manifest_row.get(field):
                        consistent = False
                expected_size = manifest_row.get("bytes")
                if expected_size is not None and receipt_row.get("bytes") != expected_size:
                    consistent = False
        verified_count = receipt.get("verified_files_count") if isinstance(receipt, dict) else None
        return {
            "available": True,
            "entry_count": len(receipt_files),
            "verified_files_count_recorded": verified_count,
            "matches_manifest_metadata": bool(consistent),
            "current_availability_proof": False,
            "note": "Historical receipt metadata is not revalidated file presence.",
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, AttributeError):
        return {
            "available": True,
            "entry_count": None,
            "verified_files_count_recorded": None,
            "matches_manifest_metadata": False,
            "current_availability_proof": False,
            "note": "Historical receipt is unreadable or inconsistent; current files are checked independently.",
        }


def inspect_runtime_inputs(root: str | Path) -> dict[str, Any]:
    """Check each manifest destination under ``data/raw`` without side effects."""
    root = Path(root).resolve()
    manifest, manifest_raw, entries = _manifest_entries(root)
    try:
        raw_root = (root / "data/raw").resolve(strict=False)
        raw_root_error = None
    except (OSError, RuntimeError) as exc:
        raw_root = root / "data/raw"
        raw_root_error = type(exc).__name__
    rows: list[dict[str, Any]] = []

    for entry in entries:
        destination = PurePosixPath(entry["dest"])
        candidate = root / "data/raw" / Path(*destination.parts)
        row: dict[str, Any] = {
            "id": entry["id"],
            "dest": destination.as_posix(),
            "runtime_path": (Path("data/raw") / Path(*destination.parts)).as_posix(),
            "expected_sha256": entry["sha256"],
            "expected_bytes": entry.get("bytes"),
            "actual_sha256": None,
            "actual_bytes": None,
            "status": None,
        }
        try:
            if raw_root_error is not None:
                row["status"] = "unreadable"
                row["error_type"] = raw_root_error
            else:
                resolved = candidate.resolve(strict=False)
                if not resolved.is_relative_to(raw_root):
                    row["status"] = "unsafe_path"
                elif not candidate.exists():
                    row["status"] = "missing"
                elif not candidate.is_file():
                    row["status"] = "not_regular_file"
                else:
                    size = candidate.stat().st_size
                    checksum = _sha256_file(candidate)
                    row["actual_bytes"] = size
                    row["actual_sha256"] = checksum
                    size_matches = entry.get("bytes") is None or size == entry["bytes"]
                    hash_matches = checksum == entry["sha256"]
                    row["size_matches"] = size_matches
                    row["sha256_matches"] = hash_matches
                    row["status"] = "verified" if size_matches and hash_matches else "mismatch"
        except (OSError, RuntimeError) as exc:
            row["status"] = "unreadable"
            row["error_type"] = type(exc).__name__
        rows.append(row)

    verified_ids = {row["id"] for row in rows if row["status"] == "verified"}
    missing_count = sum(row["status"] == "missing" for row in rows)
    mismatch_count = sum(row["status"] == "mismatch" for row in rows)
    other_invalid_count = len(rows) - len(verified_ids) - missing_count - mismatch_count
    all_verified = len(rows) > 0 and len(verified_ids) == len(rows)
    training_ready = all(file_id in verified_ids for file_id in _CORE_TRAINING_IDS)
    pipeline_ready = all(file_id in verified_ids for file_id in _CORE_PIPELINE_IDS)

    if all_verified:
        state = "all_manifest_inputs_verified"
    elif mismatch_count or other_invalid_count:
        state = "blocked_mismatch_or_invalid_path"
    else:
        state = "blocked_missing_inputs"

    return {
        "schema_version": 1,
        "checker_version": "runtime-data-status-v1",
        "evidence_class": "RUNTIME-LOCAL-AVAILABILITY",
        "checked_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "state": state,
        "scope": (
            "Current file presence, byte size (when pinned), and SHA-256 under data/raw only. "
            "This does not authenticate organizer origin, establish license, or validate scientific semantics."
        ),
        "manifest_path": "registry/data_manifest.json",
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "runtime_root": "data/raw",
        "expected_count": len(entries),
        "verified_count": len(verified_ids),
        "missing_count": missing_count,
        "mismatch_count": mismatch_count,
        "other_invalid_count": other_invalid_count,
        "training_supervision_ready": training_ready,
        "core_pipeline_inputs_ready": pipeline_ready,
        "all_manifest_inputs_ready": all_verified,
        "historical_restore_receipt": _historical_receipt_summary(root, entries),
        "files": rows,
    }
