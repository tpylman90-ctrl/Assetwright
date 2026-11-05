"""Train our OWN CAD-to-visual student from frozen DINOv2 multi-view lessons.

The student sees supported CAD operation sequences, never teacher images or
downloaded geometry during inference. It predicts only numeric shape features,
not actual vertices or prompt-to-3D geometry. Research-only, fail-closed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from deep_dino_curriculum import VIEWS
from visual_transfer_student import project_teacher
from zero_to_cad_dinov2_teacher import MODEL as DINO, SCHEMA as TEACHER
from zero_to_cad_visual_student import DIM, input_features, prepared

MODEL = "assetwright-owned-deep-dino-student-v1"
ADVANCED = frozenset(("loft", "sweep", "fillet", "chamfer", "shell",
                       "cutBlind", "cutThruAll", "cut", "union", "revolve"))
OUT = 24
HIDDEN = 64


def validated_rows(manifest: dict, teacher: dict, split: str) -> list[dict]:
    if (manifest.get("teacher_views") != list(VIEWS) or
            teacher.get("view_count") != len(VIEWS) or
            teacher.get("model_id") != DINO or
            teacher.get("schema") != TEACHER or
            manifest.get("dataset_revision") != teacher.get("dataset_revision")):
        raise ValueError("Mismatched pinned multi-view teacher cohort")
    originals = {row["source_id"]: row for row in manifest["records"]}
    records = prepared(manifest, teacher, split)
    images = {row["source_id"]: row for row in teacher["records"]}
    for row in records:
        item = originals[row["source_id"]]
        if images[row["source_id"]].get("view_count") != len(VIEWS):
            raise ValueError("Missing four-view DINO supervision")
        # Prevent production-unavailable face-count metadata leaking into input.
        row["x"] = input_features(item["operations"], None)
        row["advanced"] = bool(ADVANCED.intersection(item["operations"]))
    return records


def check_splits(train: list[dict], heldout: list[dict]) -> None:
    train_ids = [row["source_id"] for row in train]
    valid_ids = [row["source_id"] for row in heldout]
    hashes = [row["hash"] for row in train + heldout]
    if (len(set(train_ids)) != len(train_ids) or
            len(set(valid_ids)) != len(valid_ids) or
            set(train_ids).intersection(valid_ids) or
            len(set(hashes)) != len(hashes)):
        raise ValueError("Duplicate or leaked CAD code/image source")
    if len(train) < 200 or len(heldout) < 60:
        raise ValueError("Not a deep enough independent source study")


def split_for_development(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    # Predeclared SHA split; never choose hyperparameters using official validation.
    dev = [r for r in rows if int(r["hash"][:8], 16) % 5 == 0]
    fit = [r for r in rows if int(r["hash"][:8], 16) % 5 != 0]
    if len(dev) < 24 or len(fit) < 150:
        raise ValueError("Insufficient disjoint, source-hashed development groups")
    return fit, dev


def fit(train_doc: dict, train_teacher: dict,
        valid_doc: dict, valid_teacher: dict) -> tuple[dict, dict]:
    if (train_doc.get("dataset_revision") != valid_doc.get("dataset_revision") or
            train_doc.get("dataset") != valid_doc.get("dataset")):
        raise ValueError("Training and official validation source revision mismatch")
    train = validated_rows(train_doc, train_teacher, "train")
    heldout = validated_rows(valid_doc, valid_teacher, "validation")
    check_splits(train, heldout)
    development_train, development = split_for_development(train)

    # Imported only by an opt-in research run; no NumPy dependency in Android.
    import numpy as np
    def matrices(rows):
        return (np.array([r["x"] for r in rows], dtype=np.float64),
                np.array([r["y"] for r in rows], dtype=np.float64))
    x, y = matrices(development_train)
    xd, yd = matrices(development)
    xv, yv = matrices(heldout)
    if x.shape[1] != DIM or y.shape[1] != OUT:
        raise ValueError("Unexpected original-student input or teacher feature shape")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Unbounded numeric visual supervision")

    # Baselines trained on EXACTLY the same samples as the challenger.
    mean = y.mean(axis=0)
    bias_x = np.column_stack((x, np.ones(len(x))))
    penalty = np.eye(DIM + 1) * 2.0
    penalty[-1, -1] = 0.0
    ridge = np.linalg.solve(bias_x.T @ bias_x + penalty, bias_x.T @ y)
    baseline_mean = np.tile(mean, (len(xv), 1))
    baseline_linear = np.column_stack((xv, np.ones(len(xv)))) @ ridge

    rng = np.random.default_rng(1441)
    weights = {
        "w1": rng.normal(0.0, 0.085, (DIM, HIDDEN)),
        "b1": np.zeros(HIDDEN),
        "w2": rng.normal(0.0, 0.065, (HIDDEN, OUT)),
        "b2": np.zeros(OUT),
    }
    moments = {key: np.zeros_like(w) for key, w in weights.items()}
    variances = {key: np.zeros_like(w) for key, w in weights.items()}
    best = None
    best_score = float("inf")
    stage_scores = []
    global_step = 0

    def forward(a, model):
        hidden = np.tanh(a @ model["w1"] + model["b1"])
        return hidden, hidden @ model["w2"] + model["b2"]

    # Foundation -> advanced -> focused refinement, with cumulative weights.
    basic = [r for r in development_train if not r["advanced"]]
    if len(basic) < 32:
        basic = development_train
    stages = (
        ("shape_foundations", basic, 85, 1.0),
        ("cad_composition", development_train, 170, 1.0),
        ("advanced_geometry_focus", development_train, 115, 1.8),
    )
    for stage_name, stage_rows, epochs, advanced_weight in stages:
        xx, yy = matrices(stage_rows)
        source_weights = np.array(
            [advanced_weight if row["advanced"] else 1.0 for row in stage_rows],
            dtype=np.float64)
        for epoch in range(epochs):
            hidden, pred = forward(xx, weights)
            delta = (pred - yy) * (2.0 / (len(xx) * OUT)) * source_weights[:, None]
            grad = {}
            grad["w2"] = hidden.T @ delta + 0.0002 * weights["w2"]
            grad["b2"] = delta.sum(axis=0)
            back = (delta @ weights["w2"].T) * (1.0 - hidden * hidden)
            grad["w1"] = xx.T @ back + 0.0002 * weights["w1"]
            grad["b1"] = back.sum(axis=0)
            global_step += 1
            lr = 0.012 / (1 + 0.002 * global_step)
            for key in weights:
                gradients = np.clip(grad[key], -3.0, 3.0)
                moments[key] = 0.9 * moments[key] + 0.1 * gradients
                variances[key] = 0.999 * variances[key] + 0.001 * gradients**2
                mm = moments[key] / (1 - 0.9**global_step)
                vv = variances[key] / (1 - 0.999**global_step)
                weights[key] -= lr * mm / (np.sqrt(vv) + 1.e-8)
            if (epoch + 1) % 5 == 0:
                _, dev_pred = forward(xd, weights)
                score = float(np.mean((dev_pred - yd)**2))
                if score < best_score:
                    best_score = score
                    best = {key: value.copy() for key, value in weights.items()}
        stage_scores.append({"stage": stage_name, "epochs": epochs,
                             "best_development_mse": round(best_score, 8)})
    if best is None:
        raise ValueError("No independently selected student checkpoint")
    _, learned = forward(xv, best)
    error = lambda a, b: float(np.mean((a-b)**2))
    mean_err, linear_err, learned_err = (
        error(baseline_mean, yv), error(baseline_linear, yv), error(learned, yv))
    adv_idx = [i for i, row in enumerate(heldout) if row["advanced"]]
    advanced = ({"examples": len(adv_idx),
                 "linear_mse": error(baseline_linear[adv_idx], yv[adv_idx]),
                 "owned_mse": error(learned[adv_idx], yv[adv_idx])}
                if len(adv_idx) >= 8 else {"examples": len(adv_idx), "not_scored": True})
    gains = {"vs_mean": (mean_err-learned_err) / mean_err if mean_err else 0,
             "vs_linear": (linear_err-learned_err) / linear_err if linear_err else 0}
    # Never accept an overfit MLP solely because it beats a constant mean.
    accepted = (gains["vs_mean"] >= 0.03 and gains["vs_linear"] >= 0.02 and
                (advanced.get("not_scored") or
                 advanced["owned_mse"] <= advanced["linear_mse"] * 1.02))
    report = {
        "schema": "assetwright-deep-dino-evaluation-v1",
        "status": "validated_research_only" if accepted else "rejected_or_inconclusive",
        "teacher": DINO, "teacher_frozen": True,
        "dataset_revision": train_doc["dataset_revision"],
        "training_examples": len(train), "internal_fit_examples": len(development_train),
        "internal_development_examples": len(development),
        "official_validation_examples": len(heldout),
        "teacher_views_per_example": len(VIEWS),
        "heldout_mean_signature_mse": round(mean_err, 8),
        "heldout_linear_cad_signature_mse": round(linear_err, 8),
        "heldout_owned_deep_student_mse": round(learned_err, 8),
        "improvement": {key: round(val, 6) for key, val in gains.items()},
        "advanced_operator_holdout": advanced,
        "development_stage_history": stage_scores,
        "training_source_hashes_sha256": hashlib.sha256(
            "\n".join(sorted(row["hash"] for row in train)).encode()).hexdigest(),
        "official_validation_source_hashes_sha256": hashlib.sha256(
            "\n".join(sorted(row["hash"] for row in heldout)).encode()).hexdigest(),
        "native_geometry_accuracy_evaluated": False,
        "arbitrary_text_to_3d_evaluated": False,
        "android_deployed": False,
        "external_ai_generates_3d": False,
        "note": "Learns visual signatures from CAD operation records, not mesh reconstruction.",
    }
    checkpoint = {"schema": MODEL, "source": "AssetWright-owned CPU research student",
                  "teacher": DINO, "frozen_teacher_at_inference": False,
                  "inference_input": "supported_CAD_operation_sequence_only",
                  "output": "projected_24D_visual_signature",
                  "weights": {key: value.tolist() for key, value in best.items()},
                  "input_dimensions": DIM, "hidden_dimensions": HIDDEN,
                  "output_dimensions": OUT, "source_revision": train_doc["dataset_revision"],
                  "training_source_hashes_sha256": report["training_source_hashes_sha256"],
                  "validated_on_official_split": accepted,
                  "approved_for_geometry_generation": False,
                  "android_deployable": False}
    return report, checkpoint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("train", "train-teacher", "validation", "validation-teacher", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    files = [args.train, args.train_teacher, args.validation, args.validation_teacher]
    report, checkpoint = fit(*(json.loads(path.read_text()) for path in files))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "candidate_student.json").write_text(json.dumps(checkpoint) + "\n")
    (args.out / "validated_research_student.json").unlink(missing_ok=True)
    if report["status"] == "validated_research_only":
        (args.out / "validated_research_student.json").write_text(json.dumps(checkpoint) + "\n")
    print(json.dumps(report, indent=2))
    # A failed research comparison stays visible and unpromoted; do not
    # silently lower thresholds or label it successful deep understanding.
    if report["status"] != "validated_research_only":
        raise SystemExit("Candidate did not beat both independent baselines")


if __name__ == "__main__":
    main()
