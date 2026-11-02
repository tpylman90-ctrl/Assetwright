"""Bounded, regression-gated Forge research training.

Not an autonomous text-to-3D generator. Automatically retrains a *coarse*
caption-to-eight-mesh-descriptors model on source-verified CC0 inputs and
retains the incumbent unless the replacement passes source-disjoint tests.
Self-generated geometry, weak part-name guesses, and user-private inputs are
NOT trusted supervision and never enter this loop.

The research model is public/derived only; never cache private personal
training weights, prompts or generated private assets in public GitHub CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from caption_mesh_train import (
    BUCKETS, DIMS, MODEL_SCHEMA, MIN_PAIRS, encode, error, fit, valid_rows,
)

SCHEMA = "assetwright-self-training-loop-report-v1"
CHAMPION_SCHEMA = "assetwright-research-champion-v1"
MIN_NEW_SOURCES = 2
MIN_HOLDOUT_SOURCES = 6
MIN_GAIN_OVER_CHAMPION = .01


def _sha(value: dict) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _split(rows: list) -> tuple[list, list]:
    # Keep the source-separated fixed evaluation split used by the trainer.
    return ([row for row in rows if int(row[0][:8], 16) % 5 != 0],
            [row for row in rows if int(row[0][:8], 16) % 5 == 0])


def _validate_model(model: dict, train_hashes: set[str] | None = None) -> None:
    if not isinstance(model, dict) or model.get("schema") != MODEL_SCHEMA:
        raise ValueError("Unknown incumbent research model schema")
    if model.get("android_deployable") is not False:
        raise ValueError("Research model must not be Android-deployable")
    if model.get("feature_count") != DIMS or model.get("weight_buckets") != BUCKETS:
        raise ValueError("Unsupported incumbent dimensions")
    bias, weights = model.get("bias"), model.get("weights")
    if (not isinstance(bias, list) or len(bias) != DIMS
        or not isinstance(weights, list) or len(weights) != DIMS
        or any(not isinstance(w, list) or len(w) != BUCKETS for w in weights)):
        raise ValueError("Malformed model parameters")
    numeric = bias + [x for row in weights for x in row]
    if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 20
           for v in numeric):
        raise ValueError("Unsafe model parameters")
    hashes = model.get("source_model_hashes")
    if (not isinstance(hashes, list) or len(set(hashes)) != len(hashes)
        or any(not isinstance(h, str) or len(h) != 64
               or any(c not in "0123456789abcdef" for c in h) for h in hashes)):
        raise ValueError("Malformed training-source lineage")
    if train_hashes is not None and not set(hashes).issubset(train_hashes):
        raise ValueError("Incumbent lineage includes unknown or held-out source")


def _per_feature_mse(rows: list, model: dict) -> list[float]:
    weights, bias = model["weights"], model["bias"]
    result = [0.] * DIMS
    for _, tok, targets in rows:
        scale = math.sqrt(len(tok))
        for k in range(DIMS):
            guess = max(0., min(1., bias[k] + sum(weights[k][i] for i in tok) / scale))
            result[k] += (guess - targets[k])**2
    return [v / len(rows) for v in result]


def _champion(previous: dict | None, train_hashes: set[str]) -> dict | None:
    if previous is None:
        return None
    if not isinstance(previous, dict) or previous.get("schema") != CHAMPION_SCHEMA:
        raise ValueError("Unknown saved champion manifest")
    model = previous.get("model")
    _validate_model(model, train_hashes)
    if previous.get("model_sha256") != _sha(model):
        raise ValueError("Saved champion hash mismatch")
    # Don't allow a previous model to claim evidence it does not have.
    return model


def evaluate_cycle(pairs: dict, previous: dict | None = None) -> tuple[dict, dict | None, dict | None]:
    rows = valid_rows(pairs)
    train, heldout = _split(rows)
    common = {
        "schema": SCHEMA,
        "source_scope": "Verified CC0 Poly Haven caption + Blender mesh hash",
        "grounded_unique_source_pairs": len(rows),
        "training_source_count": len(train),
        "frozen_source_disjoint_holdout_count": len(heldout),
        "self_generated_examples_accepted": 0,
        "weak_component_labels_accepted": 0,
        "private_model_weights_uploaded": False,
        "android_model_updated": False,
        "note": ("Model selection uses the same fixed source-separated holdout "
                 "over repeated cycles; a separate final blind test will "
                 "still be needed before Android use."),
    }
    train_hashes = {r[0] for r in train}
    incumbent = _champion(previous, train_hashes) if previous else None
    if len(rows) < MIN_PAIRS or len(heldout) < MIN_HOLDOUT_SOURCES:
        return {**common, "status": "insufficient_verified_data",
                "decision": "keep_incumbent" if incumbent else "no_champion"}, None, previous

    candidate_report, candidate = fit(pairs)
    if candidate is None:
        return {**common, "status": candidate_report["status"],
                "decision": "keep_incumbent" if incumbent else "no_champion"}, None, previous

    _validate_model(candidate, train_hashes)
    challenger_error = error(heldout, candidate["weights"], candidate["bias"])
    baseline = candidate_report["baseline_mse"]
    incumbent_error = (error(heldout, incumbent["weights"], incumbent["bias"])
                       if incumbent else None)
    added = (len(train_hashes - set(incumbent["source_model_hashes"]))
             if incumbent else len(train))
    safe_vs_baseline = candidate_report["status"] == "trained_passed_validation"
    safe_vs_incumbent = (incumbent_error is None
                         or challenger_error < incumbent_error * (1 - MIN_GAIN_OVER_CHAMPION))
    # Guard against improving aggregate error by catastrophically worsening
    # a single target dimension that matters for downstream geometry.
    per_feature_candidate = _per_feature_mse(heldout, candidate)
    per_feature_incumbent = (_per_feature_mse(heldout, incumbent) if incumbent else None)
    no_severe_regression = (per_feature_incumbent is None or all(
        new <= old * 2.0 + .012 for new, old
        in zip(per_feature_candidate, per_feature_incumbent)
    ))
    promote = (safe_vs_baseline and safe_vs_incumbent and no_severe_regression
               and added >= MIN_NEW_SOURCES)
    report = {
        **common,
        "status": "research_champion_promoted" if promote
                  else "candidate_rejected_keep_champion" if incumbent
                  else "candidate_rejected_no_champion",
        "decision": "promote_research_only" if promote
                    else "keep_incumbent" if incumbent else "no_champion",
        "incumbent_test_mse": round(incumbent_error, 8) if incumbent_error is not None else None,
        "candidate_test_mse": round(challenger_error, 8),
        "untrained_baseline_test_mse": baseline,
        "new_independent_training_sources": added,
        "candidate_relative_gain_vs_incumbent": (
            round((incumbent_error - challenger_error) / incumbent_error, 5)
            if incumbent_error is not None and incumbent_error > 0 else None
        ),
        "candidate_passed_blind_baseline_gate": safe_vs_baseline,
        "candidate_passed_incumbent_gate": safe_vs_incumbent,
        "candidate_passed_per_feature_regression_gate": no_severe_regression,
        "candidate_feature_mse": [round(e, 8) for e in per_feature_candidate],
        "incumbent_feature_mse": ([round(e, 8) for e in per_feature_incumbent]
                                  if per_feature_incumbent else None),
    }
    manifest = ({
        "schema": CHAMPION_SCHEMA, "model": candidate,
        "model_sha256": _sha(candidate),
        "source_lineage": "verified independent CC0 mesh checksums",
        "selection": "fixed source-separated validation; no self-generated pseudo-labels",
        "android_deployable": False,
    } if promote else previous)
    return report, candidate, manifest


def run(pairs_file: Path, out: Path, previous_file: Path | None = None) -> dict:
    pairs = json.loads(pairs_file.read_text(encoding="utf-8"))
    previous = (json.loads(previous_file.read_text(encoding="utf-8"))
                if previous_file is not None and previous_file.is_file() else None)
    report, candidate, manifest = evaluate_cycle(pairs, previous)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if candidate is not None:
        (out / "candidate.json").write_text(json.dumps(candidate, separators=(",", ":")) + "\n",
                                            encoding="utf-8")
    if manifest is not None:
        (out / "champion.json").write_text(json.dumps(manifest, separators=(",", ":")) + "\n",
                                           encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    x = parser.parse_args()
    run(x.pairs, x.out, x.previous)
