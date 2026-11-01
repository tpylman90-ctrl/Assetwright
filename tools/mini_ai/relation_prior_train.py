"""Learn anonymous component-layout priors from CC0 Blender part graphs.

Part-to-part AABB relationships are noisy spatial observations, not verified
physical joints or semantic assemblies. We keep the prior off Android until
reviewed semantic labels and construction tests exist.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from shape_prior_train import mean, train_centroids, evaluate

SCHEMA = "assetwright-component-layout-prior-v1"
DIMS = 8
MIN_MODELS = 4
MAX_MODELS = 50


def summarize(graph: dict) -> list[float]:
    if not isinstance(graph, dict) or graph.get("schema") != "assetwright-component-graph-v1":
        raise ValueError("Unknown graph schema")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("Invalid nodes/edges")
    n = len(nodes)
    if not 2 <= n <= 24 or not 1 <= len(edges) <= 200:
        raise ValueError("Not enough distinct mesh objects")
    used = set()
    metrics = []
    counts = {"overlapping_bounds": 0, "near_bounds": 0, "separate_bounds": 0}
    for edge in edges:
        a, b = edge.get("a"), edge.get("b")
        rel = edge.get("relation")
        if type(a) is not int or type(b) is not int or not 0 <= a < b < n:
            raise ValueError("Invalid part pair")
        if (a,b) in used or rel not in counts:
            raise ValueError("Repeated pair or unknown relation")
        used.add((a,b))
        values = [edge.get("gap_ratio"), edge.get("center_distance_ratio"),
                  edge.get("triangle_ratio")]
        if any(type(v) not in (float,int) or not math.isfinite(v) or v < 0 or v > 2 for v in values):
            raise ValueError("Invalid pair feature")
        if values[2] > 1:
            raise ValueError("Triangle ratio must be <= 1")
        counts[rel] += 1
        metrics.append(values)
    for node in nodes:
        r = node.get("center_radius")
        if type(r) not in (float,int) or not math.isfinite(r) or not 0 <= r <= 2:
            raise ValueError("Invalid node center radius")
    count = len(metrics)
    return [
        round(counts["overlapping_bounds"]/count,6),
        round(counts["near_bounds"]/count,6),
        round(counts["separate_bounds"]/count,6),
        round(sum(m[0] for m in metrics)/count/2,6),
        round(sum(m[1] for m in metrics)/count/2,6),
        round(sum(m[2] for m in metrics)/count,6),
        round(n/24,6),
        round(sum(node["center_radius"] for node in nodes)/n/2,6),
    ]


def read_rows(study: dict) -> list[dict]:
    if study.get("schema") != "assetwright-cc0-shape-study-v1":
        raise ValueError("Unsupported study report")
    seen = set()
    rows = []
    for item in study.get("assets", []):
        if item.get("license") != "CC0-1.0" or item.get("mesh_analysis") != "blender_geometry_inspected":
            continue
        geometry = item.get("geometry") or {}
        sha = geometry.get("source_sha256")
        if not isinstance(sha,str) or len(sha)!=64 or sha in seen:
            continue
        graph = geometry.get("component_graph")
        try:
            vector = summarize(graph)
        except (ValueError,KeyError,TypeError):
            continue
        seen.add(sha)
        rows.append({"hash": sha, "features": vector})
    if len(rows) > MAX_MODELS:
        raise ValueError("Too many relationship models")
    return sorted(rows,key=lambda row:row["hash"])


def fit(study: dict) -> tuple[dict,dict|None]:
    rows = read_rows(study)
    common = {
        "schema": "assetwright-component-layout-report-v1",
        "cycle": study.get("cycle"),
        "licensed_multi_part_models": len(rows),
        "scope": "anonymous AABB relation-profile clustering; not semantic attachment training"
    }
    if len(rows) < MIN_MODELS:
        return {**common,"status":"insufficient_multi_part_data",
                "minimum_required":MIN_MODELS},None
    # Held-out split is by entire source model, never by edge within a model.
    test = rows[::4]
    train = [row for i,row in enumerate(rows) if i % 4 != 0]
    if len(train)<2 or len(test)<1:
        return {**common,"status":"insufficient_holdout"},None
    x = [row["features"] for row in train]
    y = [row["features"] for row in test]
    baseline = evaluate(y,[mean(x)])
    centers = train_centroids(x,2)
    trained = evaluate(y,centers)
    passed = trained <= baseline + 1e-10
    status = "trained_passed_validation" if passed else "rejected_regression"
    validation = {**common,"status":status,"train_models":len(x),"holdout_models":len(y),
                  "baseline_mse":round(baseline,8),"candidate_mse":round(trained,8),
                  "improvement_fraction":round((baseline-trained)/baseline,5) if baseline else 0}
    model = {
        "schema":SCHEMA, "method":"two-prototype anonymous component-layout learner",
        "features":DIMS, "centroids":[[round(v,6) for v in row] for row in centers],
        "source_model_hashes":[row["hash"] for row in train],
        "android_deployable":False,
        "status":status,
        "disclaimer":"Bounding boxes only; no physical contact or semantic component types"
    }
    return validation,model


def run(source:Path,output:Path)->dict:
    study=json.loads(source.read_text(encoding="utf-8"))
    report,model=fit(study)
    output.mkdir(parents=True,exist_ok=True)
    (output/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if model is not None:
        (output/"candidate_layout.json").write_text(json.dumps(model,indent=2)+"\n",encoding="utf-8")
        if report["status"]=="trained_passed_validation":
            (output/"validated_layout.json").write_text(json.dumps(model,indent=2)+"\n",encoding="utf-8")
    return report


if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--report",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    print(json.dumps(run(args.report,args.out),indent=2))
