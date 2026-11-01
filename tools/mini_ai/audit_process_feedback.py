#!/usr/bin/env python3
"""Audit exported, user-approved Assetwright examples for construction mistakes.

No data is uploaded and no private examples are committed to Git. This
checks whether requested propulsion-unit counts were actually represented
in the saved procedural operation sequence; it does NOT verify mesh topology.
"""
import argparse
import json
from pathlib import Path
import re

BEFORE = re.compile(
    r"\b(1|2|3|one|two|three|single|twin|dual|triple)\s+"
    r"(?:(?:rear|main|central|primary|propulsion)\s+)?"
    r"(?:engines?|thrusters?|boosters?|drives?)\b", re.I
)
AFTER = re.compile(
    r"\b(?:engines?|thrusters?|boosters?|drives?)\s*(?:x\s*|:\s*)?(1|2|3)\b", re.I
)
COUNTS = {
    "1": 1, "one": 1, "single": 1,
    "2": 2, "two": 2, "twin": 2, "dual": 2,
    "3": 3, "three": 3, "triple": 3,
}


def requested_drive_count(prompt: str) -> int | None:
    match = BEFORE.search(prompt) or AFTER.search(prompt)
    if match is None:
        return None
    return COUNTS[match.group(1).lower()]


def review_example(record: dict) -> dict:
    prompt = record.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Missing prompt")
    program = record.get("construction_recipe", {})
    operations = program.get("operation_sequence", [])
    if not isinstance(operations, list):
        raise ValueError("Invalid construction recipe")
    drives = [op.get("parameters", {}).get("housings")
              for op in operations if op.get("operation") == "attach_rear_drive"]
    request = requested_drive_count(prompt)
    actual = drives[0] if len(drives) == 1 else None
    issues = []
    if request is not None and actual != request:
        issues.append({
            "category": "component_count_mismatch",
            "component": "rear propulsion housing",
            "requested_count": request,
            "recorded_count": actual,
            "recommendation": "Use requested engine count when generating both geometry and shape program",
        })
    return {
        "schema": "assetwright-process-audit-v1",
        "requested_engine_count": request,
        "recorded_engine_count": actual,
        "status": "mismatch" if issues else "no_detected_count_mismatch",
        "issues": issues,
        "note": "Checks construction recipes only; inspect an actual GLB for visual verification",
    }


def audit_file(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Input learning export too large")
    reviews = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("schema") != "assetwright-approved-example-v1":
            raise ValueError(f"Unrecognized example schema on line {index}")
        info = review_example(record)
        info["line"] = index
        reviews.append(info)
    return {
        "schema": "assetwright-audit-summary-v1",
        "examples_reviewed": len(reviews),
        "mismatches": sum(x["status"] == "mismatch" for x in reviews),
        "reviews": reviews,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approved_jsonl", type=Path)
    parser.add_argument("--output", type=Path, help="Optional private report path")
    args = parser.parse_args()
    result = audit_file(args.approved_jsonl)
    report = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
