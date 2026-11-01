#!/usr/bin/env python3
"""Discover explicitly license-approved GLB candidates in a local folder.

Sidecar requirement: <file>.glb.license.json with:
  {"source_url":"https://...","license":"CC0-1.0",
   "reviewed_by_user":true,"confirmed_training_allowed":true,
   "asset_family":"vehicle","description":"..."}
Candidate records are NOT used by the parameter learner until the geometry is
inspected and mapped to reliable shape/part labels. No web scraping.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from import_glb import inspect_glb

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "local-data/mini-ai"


def scan_once(folder: Path, output: Path) -> dict:
    results = []
    blocked = []
    for path in sorted(folder.rglob("*.glb")) if folder.exists() else []:
        sidecar = path.with_suffix(path.suffix + ".license.json")
        try:
            if not sidecar.is_file():
                raise ValueError("missing reviewed license sidecar")
            terms = json.loads(sidecar.read_text(encoding="utf-8"))
            if not isinstance(terms, dict):
                raise ValueError("license sidecar must be JSON object")
            if terms.get("license") != "CC0-1.0":
                raise ValueError("not verified CC0-1.0")
            if terms.get("reviewed_by_user") is not True or terms.get("confirmed_training_allowed") is not True:
                raise ValueError("training/use permission not confirmed by user")
            source = terms.get("source_url")
            if not isinstance(source, str) or not source.startswith(("https://", "http://")):
                raise ValueError("missing source URL")
            family = terms.get("asset_family")
            description = terms.get("description")
            if not isinstance(family, str) or not family.strip():
                raise ValueError("asset family not labeled")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("asset description not labeled")
            if path.stat().st_size > 120 * 1024 * 1024:
                raise ValueError("GLB too large for starter intake")
            stats = inspect_glb(path)
            results.append({
                "schema": "assetwright-training-candidate-v1",
                "source_url": source, "license": "CC0-1.0",
                "manual_approval": True, "asset_family": family,
                "description": description,
                "input_filename": path.name,
                "local_path": str(path.resolve()),
                "status": "candidate_not_trained",
                **stats,
            })
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            blocked.append({"path": str(path), "reason": str(error)})
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        for record in results:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    temp.replace(output)
    return {"eligible_candidates": len(results), "blocked": blocked,
            "message": "Catalogued metadata only; no geometry model training performed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=DEFAULT_ROOT / "library-inbox")
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT / "candidates.jsonl")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=120)
    args = parser.parse_args()
    if args.poll_seconds < 10:
        parser.error("--poll-seconds must be at least 10")
    last = None
    while True:
        paths = (sorted(args.folder.rglob("*")) if args.folder.exists() else [])
        signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size)
                          for p in paths if p.is_file())
        if signature != last:
            print(json.dumps(scan_once(args.folder, args.output), indent=2), flush=True)
            last = signature
        if not args.watch:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
