"""Orientation-independent, bounded AABB component relationship descriptors.

Part labels are anonymous. An overlap of axis-aligned bounding boxes is NOT
proof of a physical joint, semantic role, or actual mesh collision.
"""
from __future__ import annotations
import math

SCHEMA = "assetwright-component-graph-v1"
MAX_PARTS = 24
MAX_EDGES = 200
RELATIONS = ("overlapping_bounds", "near_bounds", "separate_bounds")


def build_graph(parts: list[dict], overall_min: list[float], overall_max: list[float]) -> dict:
    if not isinstance(parts, list):
        raise ValueError("Expected a list of parts")
    if len(overall_min) != 3 or len(overall_max) != 3:
        raise ValueError("Bad overall dimensions")
    dim = [b-a for a, b in zip(overall_min, overall_max)]
    if any(not math.isfinite(d) or d <= 0 for d in dim):
        raise ValueError("Degenerate source")
    scale = max(dim)
    usable = []
    for index, part in enumerate(parts):
        a, b = part.get("min"), part.get("max")
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != 3 or len(b) != 3:
            continue
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in a+b):
            continue
        triangles = part.get("triangles")
        if type(triangles) is not int or triangles < 1:
            continue
        extents = [y-x for x, y in zip(a,b)]
        if any(t < 0 for t in extents):
            continue
        center = [(x+y)/2 for x,y in zip(a,b)]
        usable.append((index, triangles, a, b, extents, center))
    if not usable:
        return {"schema": SCHEMA, "part_count": 0, "nodes": [],
                "edges": [], "pair_count": 0, "note": "No valid mesh-object bounding boxes"}
    # Favor substantial mesh parts, stable across importer object ordering.
    selected = sorted(usable, key=lambda x: (-x[1], -max(x[4]), x[0]))[:MAX_PARTS]
    total = sum(x[1] for x in selected)
    nodes = []
    for node_id, (_, triangles, a, b, extents, center) in enumerate(selected):
        nodes.append({
            "id": node_id,
            "triangle_fraction": round(triangles/total, 6),
            "extent_ratios": [round(v/scale, 6) for v in sorted(extents)],
            "center_radius": round(math.sqrt(sum(
                ((c-(x+y)/2)/scale)**2 for c,x,y in zip(center,overall_min,overall_max)
            )), 6)
        })
    edges = []
    for i in range(len(selected)):
        _, ta, amin, amax, ae, acenter = selected[i]
        for j in range(i+1,len(selected)):
            _, tb, bmin, bmax, be, bcenter = selected[j]
            gaps = [max(0.0, bmin[k]-amax[k], amin[k]-bmax[k]) for k in range(3)]
            gap = math.sqrt(sum(v*v for v in gaps)) / scale
            center_distance = math.sqrt(sum(((a-b)/scale)**2
                                           for a,b in zip(acenter,bcenter)))
            if gap <= 1e-7:
                relation = "overlapping_bounds"
            elif gap <= .08:
                relation = "near_bounds"
            else:
                relation = "separate_bounds"
            edges.append({
                "a": i, "b": j, "relation": relation,
                "gap_ratio": round(min(gap, 2.0), 6),
                "center_distance_ratio": round(min(center_distance, 2.0), 6),
                "triangle_ratio": round(min(ta,tb)/max(ta,tb), 6)
            })
    # Prefer the most spatially relevant pairs if a scene has many objects.
    edges.sort(key=lambda edge: (edge["gap_ratio"], edge["a"], edge["b"]))
    edges = edges[:MAX_EDGES]
    return {
        "schema": SCHEMA, "part_count": len(selected),
        "source_mesh_objects": len(usable),
        "nodes": nodes, "edges": edges, "pair_count": len(edges),
        "relation_counts": {label: sum(e["relation"]==label for e in edges)
                            for label in RELATIONS},
        "note": "Anonymous object AABB geometry; proximity is not a verified joint"
    }
