"""Independent V2 development audit of original native Kotlin rocker-channel GLBs.

Development only: not a blind benchmark, learned planner, production mesh,
Class-A surface, Boolean through-hole, or true propulsion-body seam weld.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from generated_glb_critic import inspect
from native_socket_audit import points_of

SCHEMA = "assetwright-native-rocker-v2-development"
FAMILIES = ("rockerdev_a", "rockerdev_b")
ORDER = ("sculpt_cockpit_shoulder", "recess_lower_rocker",
         "recess_rear_socket", "loft_rear_nacelle")


def halfspan(points):
    # glTF axes are (native X, native Z, -native Y).
    # Corresponding lower-hull station, not an insensitive bounding box.
    length = max(p[2] for p in points) - min(p[2] for p in points)
    # The native theta=225 and 315 degree vertices are present at both
    # 16 and 32 radial segments. Fix the angular station rather than
    # accepting arbitrary vertices from a broad vertical coordinate band.
    target_height = .8 - .38 / math.sqrt(2)
    ring = [abs(x) for x, y, z in points
            if abs(z - .05 * length) < .002
            and abs(y - target_height) < .002 and abs(x) > .05]
    if len(ring) != 2 or abs(ring[0] - ring[1]) > .0001:
        raise ValueError("Missing symmetric homologous lower-hull station")
    return sum(ring) / 2


def underbody_height(points):
    length = max(p[2] for p in points) - min(p[2] for p in points)
    ring = [y for x, y, z in points
            if abs(z - .05 * length) < .002 and abs(x) < .002]
    if len(ring) != 2:
        raise ValueError("Missing homologous underside station")
    return min(ring)


def inspect_case(root, family, name):
    stem = family + "__" + name
    metadata = json.loads((root / (stem + ".json")).read_text())
    path = root / (stem + ".glb")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if not (metadata.get("schema") == SCHEMA
            and metadata.get("generator") == "android-native-MiniGeometry"
            and metadata.get("phase") == "development"
            and metadata.get("family") == family
            and metadata.get("case") == stem
            and metadata.get("source_glb_sha256") == sha):
        raise ValueError("Invalid original GLB provenance: " + stem)
    if name == "baseline":
        expected = []
    elif name == "combined_four":
        expected = [{"operation": op, "strength": .725} for op in ORDER]
    else:
        expected = [{"operation": "recess_lower_rocker",
                     "strength": {"s250": .25, "s500": .5, "s900": .9}[name]}]
    if metadata.get("commands") != expected:
        raise ValueError("Unexpected native operation recipe: " + stem)
    report = inspect(path)
    matched = [part for part in report["parts"]
               if part["name"] == "Sculpted continuous body"]
    if len(matched) != 1:
        raise ValueError("Missing unique source hull")
    hull = matched[0]
    if (report["model_sha256"] != sha
            or report["triangles"] > 12000
            or report["invalid_triangles"] != 0
            or report["nonmanifold_edges"] != 0
            or hull["boundary_edges"] != 0
            or hull["nonmanifold_edges"] != 0
            or hull["signed_volume"] <= 0):
        raise ValueError("Structural audit failed: " + stem)
    hull_points = points_of(path)
    return {"source_sha256": sha,
            "halfspan_m": halfspan(hull_points),
            "underbody_height_m": underbody_height(hull_points),
            "triangles": report["triangles"], "hull_triangles": hull["triangles"],
            "mesh_parts": report["mesh_parts"]}


def run(root, out):
    result = {
        "schema": SCHEMA, "status": "development_proof_only",
        "families": {}, "checks": {},
        "limitations": "No trained V2 planner or fresh blind family. "
                       "No visual approval, Boolean through-cut, or welded "
                       "propulsion-body seams."
    }
    for family in FAMILIES:
        cases = {name: inspect_case(root, family, name) for name in (
            "baseline", "s250", "s500", "s900", "combined_four")}
        measured = [cases[name]["halfspan_m"] for name in (
            "baseline", "s250", "s500", "s900")]
        raised = [cases[name]["underbody_height_m"] for name in (
            "baseline", "s250", "s500", "s900")]
        checks = {
            "monotone_recess": all(a - b > .012
                                   for a, b in zip(measured, measured[1:])),
            "substantial_real_deformation": measured[0] - measured[-1] > .15,
            "monotone_side_silhouette_lift": all(b - a > .015
                                                 for a, b in zip(raised, raised[1:])),
            "meaningful_side_silhouette_lift": raised[-1] - raised[0] > .075,
            "same_mesh_part_count": len({
                case["mesh_parts"] for case in cases.values()}) == 1,
            "more_true_hull_stations": cases["s250"]["hull_triangles"]
                                      > cases["baseline"]["hull_triangles"],
            "composed_program_preserves_channel": (
                measured[2] > cases["combined_four"]["halfspan_m"] > measured[3]),
            "composed_program_preserves_underbody": (
                raised[2] < cases["combined_four"]["underbody_height_m"] < raised[3]),
        }
        result["families"][family] = cases
        result["checks"][family] = checks
    result["passed"] = all(all(c.values()) for c in result["checks"].values())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(2)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.source, args.out)
