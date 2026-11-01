"""Train an evaluated compact geometry prototype model from licensed descriptors.

This is an unsupervised k-means shape prior, *not* a text-to-3D generator.
Its inputs are normalized numeric features extracted from imported 3D meshes.
It does not inspect/retain raw GLBs and cannot learn semantic part assembly.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "assetwright-geometry-prior-v1"
DIMS = 8
MIN_ASSETS = 4
MAX_ASSETS = 50


def validate_rows(report: dict) -> list[dict]:
    if report.get("schema") not in ("assetwright-cc0-shape-study-v1",):
        raise ValueError("Wrong study report schema")
    records = []
    fingerprints = set()
    for item in report.get("assets", []):
        geo = item.get("geometry", {})
        if not isinstance(geo, dict) or geo.get("schema") != "assetwright-geometry-descriptor-v1":
            continue
        if item.get("license") != "CC0-1.0" or item.get("mesh_analysis") != "blender_geometry_inspected":
            continue
        vec = geo.get("features")
        digest = geo.get("source_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            continue
        if not isinstance(vec, list) or len(vec) != DIMS or any(
            type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in vec
        ):
            continue
        if digest in fingerprints:
            continue
        fingerprints.add(digest)
        records.append({"id": item["id"], "features": [float(v) for v in vec], "sha256": digest})
    if len(records) > MAX_ASSETS:
        raise ValueError("Too many training records")
    return sorted(records, key=lambda row: row["sha256"])


def distance(a: list[float], b: list[float]) -> float:
    return sum((x-y)**2 for x,y in zip(a,b))


def mean(rows: list[list[float]]) -> list[float]:
    return [sum(row[i] for row in rows) / len(rows) for i in range(DIMS)]


def train_centroids(rows: list[list[float]], count: int = 2) -> list[list[float]]:
    if len(rows) < count:
        raise ValueError("Not enough rows")
    # Deterministic farthest-point initialization for repeatability.
    centers = [min(rows)]
    while len(centers) < count:
        centers.append(max(rows, key=lambda v: (min(distance(v, c) for c in centers), v)))
    for _ in range(25):
        groups = [[] for _ in centers]
        for row in rows:
            nearest = min(range(len(centers)), key=lambda i: distance(row, centers[i]))
            groups[nearest].append(row)
        updated = [mean(group) if group else center
                   for group,center in zip(groups,centers)]
        if all(distance(x,y) < 1e-14 for x,y in zip(centers,updated)):
            break
        centers = updated
    return centers


def evaluate(rows: list[list[float]], centers: list[list[float]]) -> float:
    return sum(min(distance(v, c) for c in centers) for v in rows) / len(rows)


def fit(report: dict) -> tuple[dict, dict | None]:
    rows = validate_rows(report)
    common = {
        "schema": "assetwright-geometry-prior-report-v1",
        "cycle": report.get("cycle"),
        "licensed_geometry_examples": len(rows),
        "source": "Poly Haven CC0",
        "scope": "unsupervised shape prior; no text-to-3D, no Android weights",
    }
    if len(rows) < MIN_ASSETS:
        return {**common, "status": "insufficient_data",
                "minimum_required": MIN_ASSETS,
                "note": "Need 4 different, validated Blender geometry descriptors"}, None
    # Deterministic holdout by source hash. No leakage from held-out examples.
    heldout = rows[::4]
    train = [r for i,r in enumerate(rows) if i % 4 != 0]
    if len(train) < 2:
        return {**common, "status": "insufficient_training_split"}, None
    train_vecs = [r["features"] for r in train]
    test_vecs = [r["features"] for r in heldout]
    baseline = evaluate(test_vecs, [mean(train_vecs)])
    centers = train_centroids(train_vecs, 2)
    candidate = evaluate(test_vecs, centers)
    # Regressions may happen on tiny samples; report them honestly.
    accepted = candidate <= baseline + 1e-10
    status = "trained_passed_validation" if accepted else "rejected_regression"
    report_out = {**common, "status": status,
        "train_examples": len(train), "holdout_examples": len(heldout),
        "baseline_mean_squared_distance": round(baseline, 8),
        "trained_mean_squared_distance": round(candidate, 8),
        "improvement_fraction": round((baseline-candidate)/baseline, 5) if baseline else 0,
    }
    model = {"schema": SCHEMA,
             "method": "2-means geometry descriptors",
             "feature_count": DIMS,
             "centroids": [[round(v, 6) for v in center] for center in centers],
             "trained_examples": len(train),
             "source_record_hashes": [r["sha256"] for r in train],
             "trained_from": "CC0 geometry descriptors only",
             "android_deployable": False,
             "status": status}
    return report_out, model


def run(source: Path, directory: Path) -> dict:
    info = json.loads(source.read_text(encoding="utf-8"))
    evaluation, model = fit(info)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
    if model is not None:
        (directory / "candidate_prior.json").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
        if evaluation["status"] == "trained_passed_validation":
            (directory / "validated_prior.json").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    return evaluation


if __name__ == "__main__":
    import argparse
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--report", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    result = run(args.report, args.out)
    print(json.dumps(result, indent=2))
