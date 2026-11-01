#!/usr/bin/env python3
"""Offline Assetwright incremental training loop.

Watches a LOCAL inbox of opt-in Android learning exports. Builds a validated
nearest-neighbor model package from reviewed numeric shape corrections, runs
held-out regression gates, and promotes the pack locally only on a pass.

No downloads, cloud services, GitHub pushes, GPU requirements, or GLB scraping.
External meshes remain candidates until licensed, reviewed and labeled.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time

from library_queue import scan_once

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "app/src/main/assets/mini_ai/training_examples.json"
DEFAULT_INBOX = REPO / "local-data/mini-ai/inbox"
DEFAULT_OUT = REPO / "local-data/mini-ai/trained"
DIMENSIONS = {
    "length": (3.4, 7.0, 4.8),
    "width": (1.45, 3.2, 2.05),
    "roofHeight": (1.05, 2.30, 1.52),
    "canopyLength": (0.85, 3.1, 1.8),
    "noseTaper": (0.25, 0.9, 0.55),
    "rearHaunch": (0.9, 1.3, 1.07),
}
IGNORED = set("a an the with and for of some make create build design me my that has is on in it vehicle car hover hoover craft".split())
SYNONYMS = {
    "broad": "wide", "wider": "wide", "large": "big",
    "longer": "long", "elongated": "long", "shorter": "short",
    "small": "compact", "slender": "narrow", "slim": "narrow",
    "greenhouse": "canopy", "windshield": "canopy",
    "sporty": "racer", "racing": "racer",
    "haunches": "haunch", "fenders": "haunch", "cab": "cockpit",
    "hoover": "hover",
}


def tokens(text: str) -> set[str]:
    return {SYNONYMS.get(s, s) for s in re.findall(r"[a-z0-9]+", text.lower()) if SYNONYMS.get(s, s) not in IGNORED}


def validate(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Example must be a JSON object")
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= 1000:
        raise ValueError("Invalid training prompt")
    result = {"prompt": prompt.strip()}
    for key, (low, high, _) in DIMENSIONS.items():
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Invalid {key} in example")
        result[key] = float(value)
    return result


def read_inbox(folder: Path) -> list[dict]:
    if not folder.exists():
        return []
    records: dict[str, dict] = {}
    for path in sorted(folder.glob("*.jsonl")):
        if path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError(f"Training export too large: {path.name}")
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not (record.get("schema") == "assetwright-approved-example-v1"
                    and record.get("approved_by_user") is True
                    and record.get("origin") == "android-corrected-vehicle"):
                raise ValueError(f"Unapproved or unknown record: {path.name}:{lineno}")
            result = validate(record)
            records[result["prompt"].lower()] = result
            if len(records) > 500:
                raise ValueError("Too many training examples (500 maximum)")
    return list(records.values())


def predict(prompt: str, examples: list[dict]) -> dict:
    exact = next((e for e in examples if e["prompt"].strip().lower() == prompt.strip().lower()), None)
    if exact is not None:
        return exact
    query = tokens(prompt)
    scored = []
    for e in examples:
        sample = tokens(e["prompt"])
        overlap = len(query & sample)
        similarity = overlap / math.sqrt(len(query) * len(sample)) if query and sample else 0.0
        if similarity > 0:
            scored.append((similarity, e))
    scored.sort(key=lambda item: item[0], reverse=True)
    nearest = scored[:4]
    output = {"prompt": prompt}
    for key, (low, high, default) in DIMENSIONS.items():
        if not nearest:
            value = default
        else:
            total = sum(score * score for score, _ in nearest)
            fitted = sum(e[key] * score * score for score, e in nearest) / total
            value = 0.90 * fitted + 0.10 * default
        output[key] = max(low, min(high, value))
    return output


def score(test_set: list[dict], training: list[dict]) -> float:
    if not test_set:
        raise ValueError("No held-out validation data")
    errors = []
    for row in test_set:
        pred = predict(row["prompt"], training)
        errors.extend(abs(pred[key] - row[key]) / (high - low)
                      for key, (low, high, _) in DIMENSIONS.items())
    return sum(errors) / len(errors)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def train_once(inbox: Path, output: Path) -> dict:
    seed = [validate(x) for x in json.loads(SEED.read_text(encoding="utf-8"))]
    review = read_inbox(inbox)
    if not review:
        return {"status": "no_approved_feedback", "message": "Put Android-approved *.jsonl files in the local inbox."}
    # Split synthetic seed examples before considering imported feedback.
    train = [x for i, x in enumerate(seed) if i % 7 != 0]
    heldout = [x for i, x in enumerate(seed) if i % 7 == 0]
    # Exclude held-out test prompts explicitly present among approved examples.
    review_keys = {x["prompt"].strip().lower() for x in review}
    heldout = [x for x in heldout if x["prompt"].strip().lower() not in review_keys]
    if len(heldout) < 5:
        raise ValueError("Insufficient non-overlapping held-out examples")
    baseline = score(heldout, train)
    candidate = score(heldout, list(reversed(review)) + train)
    dataset_digest = hashlib.sha256(json.dumps(review, sort_keys=True).encode()).hexdigest()
    passed = candidate <= baseline + 0.02
    report = {
        "schema": "assetwright-home-training-report-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": dataset_digest,
        "synthetic_training_count": len(train),
        "heldout_count": len(heldout),
        "approved_user_examples": len(review),
        "baseline_normalized_mae": round(baseline, 6),
        "candidate_normalized_mae": round(candidate, 6),
        "max_allowed_regression": 0.02,
        "status": "promoted" if passed else "rejected_regression",
        "description": "Example-based predictor package; no neural weights trained",
    }
    output.mkdir(parents=True, exist_ok=True)
    # All generated packs stay in local ignored directories.
    write_json(output / "latest_report.json", report)
    pack = {
        "schema": "assetwright-mini-ai-pack-v1",
        "version": dataset_digest[:12],
        "model_type": "approved-example-memory",
        "approved_count": len(review),
        "examples": review,
    }
    write_json(output / "candidate_pack.json", pack)
    if passed:
        write_json(output / "approved_pack.json", pack)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--watch", action="store_true", help="Continuously check local inbox for new approved records")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.poll_seconds < 10:
        parser.error("--poll-seconds must be >= 10")
    previous = None
    previous_library = None
    library_folder = REPO / "local-data/mini-ai/library-inbox"
    library_index = REPO / "local-data/mini-ai/candidates.jsonl"
    while True:
        try:
            # Independently catalog only properly licensed, reviewed GLBs.
            # Candidate metadata never enters the parameter trainer implicitly.
            library_files = sorted(library_folder.rglob("*")) if library_folder.exists() else []
            library_state = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size)
                                  for p in library_files if p.is_file())
            if library_state != previous_library:
                print(json.dumps(scan_once(library_folder, library_index), indent=2), flush=True)
                previous_library = library_state
            # Avoid repeated retraining when nothing in the feedback inbox has changed.
            paths = sorted(args.inbox.glob("*.jsonl")) if args.inbox.exists() else []
            state = hashlib.sha256()
            for path in paths:
                state.update(path.name.encode("utf-8"))
                state.update(hashlib.sha256(path.read_bytes()).digest())
            digest = state.hexdigest()
            if digest != previous:
                result = train_once(args.inbox, args.output)
                print(json.dumps(result, indent=2), flush=True)
                previous = digest
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            print("Training blocked: " + str(error), flush=True)
            if not args.watch:
                raise SystemExit(1)
        if not args.watch:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
