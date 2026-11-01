#!/usr/bin/env python3
"""Inspect a user-shared Android review bundle and prepare a proposed shape fix.

This is an offline review bridge for ChatGPT/Forge + Assetwright, not an
autonomous mesh-understanding AI. The reviewer inspects the GLB and supplies
explicit geometry corrections. Android previews the proposal before the
user can approve it into local learning memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

from home_train import DIMENSIONS, validate
from import_glb import inspect_glb

SCHEMA = "assetwright-forge-review-v1"
PROPOSAL_SCHEMA = "assetwright-forge-proposal-v1"
EXPECTED_ENTRIES = {"review.json", "model.glb", "README.txt"}
MAX_BUNDLE = 30 * 1024 * 1024
MAX_GLB = 20 * 1024 * 1024
PARAMS = tuple(DIMENSIONS)


def inspect_bundle(bundle: Path) -> tuple[dict, bytes]:
    if not bundle.is_file() or bundle.stat().st_size > MAX_BUNDLE:
        raise ValueError("Review ZIP not found or exceeds 30MB")
    with zipfile.ZipFile(bundle, "r") as archive:
        infos = archive.infolist()
        names = [x.filename for x in infos]
        if len(names) != len(set(names)) or not {"review.json", "model.glb"}.issubset(names):
            raise ValueError("Missing files or duplicate entries in review ZIP")
        if set(names) - EXPECTED_ENTRIES:
            raise ValueError("Unexpected files in review ZIP")
        if any(x.file_size > MAX_GLB or x.compress_size > MAX_BUNDLE for x in infos):
            raise ValueError("Oversized archive member")
        if any(x.file_size > 0 and x.compress_size > 0 and
               x.file_size / x.compress_size > 150 for x in infos):
            raise ValueError("Unexpected compression ratio")
        info = archive.getinfo("review.json")
        if info.file_size > 24_000:
            raise ValueError("Review metadata too large")
        meta = json.loads(archive.read("review.json").decode("utf-8"))
        glb = archive.read("model.glb")
    if not isinstance(meta, dict) or meta.get("schema") != SCHEMA:
        raise ValueError("Unsupported Forge review schema")
    if meta.get("share_approval") != "user_exported_for_assistant_review":
        raise ValueError("Review lacks user export marker")
    digest = hashlib.sha256(glb).hexdigest()
    if meta.get("model_sha256") != digest:
        raise ValueError("GLB hash mismatch")
    params = meta.get("parameters")
    if not isinstance(params, dict) or set(params) != set(PARAMS):
        raise ValueError("Unexpected parameter schema")
    validated = validate({"prompt": meta.get("prompt"), **params})
    for k in PARAMS:
        if not math.isclose(validated[k], float(params[k]), abs_tol=1e-6):
            raise ValueError("Invalid parameter " + k)
    profile = meta.get("profile")
    if profile not in ("Mobile", "Balanced", "High detail"):
        raise ValueError("Unknown quality profile")
    request = meta.get("requested_changes")
    if not isinstance(request, str) or len(request) > 2000:
        raise ValueError("Invalid review request")
    if len(glb) > MAX_GLB:
        raise ValueError("GLB too large for review")
    # Run the existing structural GLB validator without altering the source.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "review.glb"
        source.write_bytes(glb)
        mesh_stats = inspect_glb(source)
    if mesh_stats["unmeasured_primitive_count"]:
        raise ValueError("Review GLB contains unsupported primitive types")
    if mesh_stats["triangle_count"] != meta.get("triangle_count"):
        raise ValueError("Model triangle count differs from review metadata")
    meta["validated_mesh"] = {
        "sha256": digest,
        "triangles": mesh_stats["triangle_count"],
        "parts": mesh_stats["mesh_count"],
        "bytes": len(glb),
    }
    return meta, glb


def make_proposal(meta: dict, changes: dict[str, float], notes: str) -> dict:
    if not isinstance(notes, str) or not 0 < len(notes.strip()) <= 2000:
        raise ValueError("A specific review explanation is required")
    if not changes or any(k not in PARAMS for k in changes):
        raise ValueError("Change at least one known geometry parameter")
    existing = meta["parameters"]
    target = dict(existing)
    for key, value in changes.items():
        low, high, _ = DIMENSIONS[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Out-of-bounds correction for " + key)
        target[key] = round(float(value), 5)
    if all(abs(float(existing[k]) - float(target[k])) <= 0.000001 for k in PARAMS):
        raise ValueError("Proposal does not modify geometry")
    return {
        "schema": PROPOSAL_SCHEMA,
        "source_sha256": meta["model_sha256"],
        "prompt": meta["prompt"],
        "notes": notes.strip(),
        "target": target,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Android-exported Forge review ZIP")
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--set", action="append", default=[], metavar="FIELD=NUMBER",
                        help="Explicit reviewer adjustment; repeat as needed")
    parser.add_argument("--notes", default="", help="Reviewer rationale for the correction")
    parser.add_argument("--output", type=Path, default=Path("local-data/mini-ai/forge-proposal.json"))
    args = parser.parse_args()
    meta, _ = inspect_bundle(args.bundle)
    print(json.dumps({k: v for k, v in meta.items() if k not in ("mesh_parts",)}, indent=2))
    if args.inspect_only:
        return
    changes = {}
    for item in args.set:
        if "=" not in item:
            parser.error("--set must be FIELD=NUMBER")
        key, number = item.split("=", 1)
        if key not in DIMENSIONS:
            parser.error("Unknown parameter: " + key)
        try:
            changes[key] = float(number)
        except ValueError:
            parser.error("Invalid number: " + number)
    proposal = make_proposal(meta, changes, args.notes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    print("Wrote review proposal: " + str(args.output))


if __name__ == "__main__":
    main()
