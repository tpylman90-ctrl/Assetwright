"""Fail-closed v13 lineage and experimental gate preflight.

Run before training; no model weights are modified or deployed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_V10 = "562803bb19e1ef41ff55ab4ed2b5de6f53f29851caee8ac316bfab2e165d5ebc"
EXPECTED_V9 = "7bc18a1ceb7a9ebff28c384ea22134dc6eb7968f274986b63caa398c97725291"
REQUIRED = (
    "evaluation.json", "learning_history.json", "development_selection.json",
    "independent_1152_development_GLBS.json",
    "independent_1152_Kotlin_GLBS.json", "research_disposition.json",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(v12_archive: Path, parent: Path, identity: Path) -> dict:
    if not v12_archive.is_dir():
        raise ValueError("Missing archived v12 learning run")
    for name in REQUIRED:
        if not (v12_archive / name).is_file():
            raise ValueError(f"Missing v12 evidence: {name}")
    disposition = json.loads((v12_archive / "research_disposition.json").read_text())
    selection = json.loads((v12_archive / "development_selection.json").read_text())
    if disposition.get("status") != "research_only_rejected_parent_protected":
        raise ValueError("v12 disposition changed or unexpected")
    if disposition.get("android_neural_deployed") is not False:
        raise ValueError("Unexpected Android neural deployment")
    if disposition.get("frozen_parent_weight_sha256") != EXPECTED_V10:
        raise ValueError("Archived v10 lineage changed")
    if disposition.get("frozen_identity_weight_sha256") != EXPECTED_V9:
        raise ValueError("Archived v9 lineage changed")
    if sha256(parent) != EXPECTED_V10 or sha256(identity) != EXPECTED_V9:
        raise ValueError("Frozen parent or identity safetensors SHA-256 mismatch")
    if selection.get("source_split") != "development":
        raise ValueError("Development selection not frozen on development")
    if selection.get("selected") != disposition.get("selected_on_development_3D_only"):
        raise ValueError("Development selection does not match archived disposition")
    if disposition.get("blind_new_original_Kotlin_GLBS") != 1152:
        raise ValueError("Incomplete archived blind GLBs")
    return {
        "schema": "assetwright-v13-fail-closed-preflight-v1",
        "status": "lineage_verified_only_not_trained",
        "parent_v10_sha256": EXPECTED_V10,
        "identity_v9_sha256": EXPECTED_V9,
        "v12_dev_selected": selection["selected"],
        "v12_promoted": False,
        "android_neural_deployed": False,
        "v13_training_started": False,
        "v13_blind_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v12-archive", required=True, type=Path)
    parser.add_argument("--parent-v10", required=True, type=Path)
    parser.add_argument("--identity-v9", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = verify(args.v12_archive, args.parent_v10, args.identity_v9)
    result = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result)
    print(result, end="")


if __name__ == "__main__":
    main()
