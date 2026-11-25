#!/usr/bin/env python3
"""Model-readable geometry descriptions from *measured* mesh data.

This module does not edit the input mesh, infer materials, identify semantic parts,
or train an AI. It packages numeric descriptions that a modeler or assistant can
read and use for controlled reference-matching iterations.
"""
import json
import math
from pathlib import Path

import numpy as np

from geometry_lab_desktop import plane_segments


def _safe_float(x):
    x = float(x)
    return round(x, 6) if math.isfinite(x) else None


def _quantiles(x):
    a = np.asarray(x)
    a = a[np.isfinite(a)]
    if not len(a):
        return {}
    return {str(p): _safe_float(np.percentile(a, p)) for p in (5, 25, 50, 75, 95)}


def _point(p):
    return [_safe_float(x) for x in p]


def _bounds(mesh):
    return {
        "minimum": _point(mesh.bounds[0]),
        "maximum": _point(mesh.bounds[1]),
        "dimensions": _point(mesh.extents),
        "centroid": _point(mesh.centroid),
        "units": "source units; glTF commonly uses metres but cannot be assumed for arbitrary imports",
    }


def _cross_sections(mesh, length_axis, count=28, angular_bins=48):
    """Section-to-envelope guides. Outer radial maxima; not true hole-aware contours."""
    verts = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    box = mesh.bounds
    dims = mesh.extents
    other = [i for i in range(3) if i != length_axis]
    mid = (box[0] + box[1]) * 0.5
    stations = []
    for frac in np.linspace(.035, .965, count):
        plane = box[0, length_axis] + dims[length_axis] * float(frac)
        cuts = plane_segments(verts, faces, length_axis, plane)
        pts = cuts.reshape(-1, 3)
        if not len(pts):
            stations.append({"fraction": _safe_float(frac), "segments": 0, "valid": False})
            continue
        uv = pts[:, other]
        lo, hi = uv.min(axis=0), uv.max(axis=0)
        origin = mid[other]
        d = uv - origin
        theta = np.arctan2(d[:, 1], d[:, 0])
        rad = np.linalg.norm(d, axis=1)
        outer = np.full(angular_bins, np.nan)
        occupancy = np.zeros(angular_bins, bool)
        nearest_deltas = np.full(angular_bins, np.nan)
        for k in range(angular_bins):
            angle = -math.pi + (k + .5) * 2 * math.pi / angular_bins
            diff = np.abs((theta - angle + math.pi) % (2 * math.pi) - math.pi)
            hit = diff <= (math.pi / angular_bins)
            if np.any(hit):
                outer[k] = rad[hit].max()
                occupancy[k] = True
                nearest_deltas[k] = diff[hit].min()
        # Missing bins remain explicit null; we never invent hidden geometry.
        xy = [[_safe_float(origin[0] + r * math.cos(-math.pi + (k + .5) * 2 * math.pi / angular_bins)),
               _safe_float(origin[1] + r * math.sin(-math.pi + (k + .5) * 2 * math.pi / angular_bins))]
              if math.isfinite(r) else None for k, r in enumerate(outer)]
        stations.append({
            "fraction": _safe_float(frac), "position": _safe_float(plane),
            "valid": True, "segments": int(len(cuts)),
            "axes": other, "outer_bounds": [_point(lo), _point(hi)],
            "outer_dimensions": _point(hi - lo),
            "outer_radial_contour": xy, "observed_bins": int(occupancy.sum()),
            "unobserved_bins": int(angular_bins - occupancy.sum()),
            "limitations": "Farthest intersection in each angle bin. Internal cavities, multi-islands and missing directions are not reconstructed.",
        })
    return stations


def _silhouettes(mesh, bins=100):
    v = np.asarray(mesh.vertices)
    result = {}
    for name, axes in (("side", (0, 1)), ("top", (0, 2)), ("end", (2, 1))):
        u, w = axes
        breaks = np.linspace(v[:, u].min(), v[:, u].max(), bins + 1)
        labels = np.clip(np.searchsorted(breaks, v[:, u], side="right") - 1, 0, bins - 1)
        low = np.full(bins, np.inf)
        high = np.full(bins, -np.inf)
        np.minimum.at(low, labels, v[:, w])
        np.maximum.at(high, labels, v[:, w])
        result[name] = {
            "axes": [u, w], "bins": [
                [_safe_float((breaks[i] + breaks[i + 1]) / 2),
                 _safe_float(low[i]), _safe_float(high[i])]
                for i in range(bins) if math.isfinite(low[i])
            ],
            "limitation": "Vertex-envelope projection, not a hole-aware raster silhouette.",
        }
    return result


def _patches(mesh, face_labels, max_patches=45):
    labels = np.asarray(face_labels, dtype=np.int64)
    count = int(labels.max() + 1) if len(labels) else 0
    if count == 0:
        return []
    areas = np.asarray(mesh.area_faces)
    sum_area = np.bincount(labels, weights=areas, minlength=count)
    order = np.argsort(sum_area)[::-1][:max_patches]
    centroid = np.asarray(mesh.triangles_center)
    normals = np.asarray(mesh.face_normals)
    result = []
    for lab in order:
        ix = np.flatnonzero(labels == lab)
        if not len(ix):
            continue
        group = mesh.faces[ix]
        pos = mesh.vertices[np.unique(group.reshape(-1))]
        weights = areas[ix]
        weighted_normal = np.average(normals[ix], axis=0, weights=weights) if weights.sum() else np.mean(normals[ix], axis=0)
        weighted_center = np.average(centroid[ix], axis=0, weights=weights) if weights.sum() else np.mean(centroid[ix], axis=0)
        result.append({
            "patch_id": int(lab), "faces": int(len(ix)),
            "area_source_units_squared": _safe_float(sum_area[lab]),
            "bounds_min": _point(pos.min(axis=0)),
            "bounds_max": _point(pos.max(axis=0)),
            "area_weighted_center": _point(weighted_center),
            "area_weighted_normal": _point(weighted_normal),
            "interpretation": "Connectivity + crease threshold patch; NOT a known hood, fender, or door.",
        })
    return result


def _spatial_features(mesh, curvature, sharpness, grid=(12, 5, 20), max_cells=28):
    xyz = np.asarray(mesh.vertices)
    norm = (xyz - mesh.bounds[0]) / mesh.extents.clip(1e-8)
    ind = (norm * (np.asarray(grid) - 1)).astype(int)
    ind = np.clip(ind, 0, np.asarray(grid) - 1)
    flat = np.ravel_multi_index(ind.T, grid)
    count = np.bincount(flat, minlength=math.prod(grid))
    convex = np.bincount(flat, weights=np.maximum(curvature, 0), minlength=len(count))
    concave = np.bincount(flat, weights=np.maximum(-curvature, 0), minlength=len(count))
    sharp = np.bincount(flat, weights=np.maximum(sharpness - 35, 0), minlength=len(count))
    signal = (convex + concave + sharp / 100) / np.maximum(1, count)
    ranked = np.argsort(signal)[::-1]
    result = []
    for idx in ranked:
        if count[idx] < 8 or signal[idx] <= 0:
            continue
        cell = np.unravel_index(idx, grid)
        center = (np.asarray(cell) + .5) / np.asarray(grid)
        result.append({
            "grid_cell": [int(a) for a in cell],
            "normalized_center": _point(center),
            "vertex_samples": int(count[idx]),
            "ridge_signal": _safe_float(convex[idx] / count[idx]),
            "valley_signal": _safe_float(concave[idx] / count[idx]),
            "crease_signal": _safe_float(sharp[idx] / count[idx]),
            "warning": "Density-dependent heuristic, not a semantic feature classification.",
        })
        if len(result) >= max_cells:
            break
    return result


def _compare_sections(a, b):
    out = []
    for st, ref in zip(a, b):
        if not st.get("valid") or not ref.get("valid"):
            continue
        av = np.asarray(st["outer_dimensions"])
        bv = np.asarray(ref["outer_dimensions"])
        if not np.all(np.isfinite(av)) or not np.all(np.isfinite(bv)):
            continue
        out.append({
            "fraction": st["fraction"],
            "reference_dims": st["outer_dimensions"],
            "candidate_dims": ref["outer_dimensions"],
            "candidate_minus_reference": _point(bv - av),
            "candidate_div_reference": _point(bv / np.maximum(av, 1e-6)),
        })
    return out


def build_modeling_packet(mesh, out, original_sha256, source_name, length_axis,
                          up_axis, curvature_broad, curvature_fine, sharpness,
                          patch_labels, crease_threshold, reference_mesh=None):
    """Create small, structured, uploadable files usable by AI assistants/modelers."""
    out = Path(out)
    section = _cross_sections(mesh, length_axis)
    sil = _silhouettes(mesh)
    patch = _patches(mesh, patch_labels)
    features = _spatial_features(mesh, np.asarray(curvature_fine), np.asarray(sharpness))
    face_area = np.asarray(mesh.area_faces)
    face_normals = np.asarray(mesh.face_normals)

    packet = {
        "schema": "assetwright.modeling_blueprint.v1",
        "source_file": source_name, "source_sha256": original_sha256,
        "geometry_only": True, "original_model_edited": False,
        "axes": {"length": int(length_axis), "up": int(up_axis),
                 "remaining": [int(i) for i in range(3) if i not in (length_axis, up_axis)]},
        "bounding_geometry": _bounds(mesh),
        "counts": {"vertices": int(len(mesh.vertices)), "triangles": int(len(mesh.faces)),
                   "area_source_units_squared": _safe_float(mesh.area)},
        "surface_complexity": {
            "surface_roughness_proxy": _quantiles(np.abs(curvature_fine)),
            "broad_curvature_proxy": _quantiles(curvature_broad),
            "fine_curvature_proxy": _quantiles(curvature_fine),
            "sharp_edge_angle_degrees": _quantiles(sharpness),
            "approx_face_area": _quantiles(face_area),
            "note": "These are density-sensitive diagnostics, not model-quality scores.",
        },
        "reconstruction_sections": section,
        "orthographic_envelopes": sil,
        "largest_surface_patches": patch,
        "feature_candidate_regions": features,
        "evidence_quality": {
            "inferred_semantic_labels": False,
            "connected_panel_patches_are_not_guaranteed_body_panels": True,
            "true_inner_cavities": False,
            "quad_topology_reconstruction": False,
            "reference_alignment_required": bool(reference_mesh is not None),
        },
        "modeling_guidance": [
            "Use normalized section stations to build primary volume and proportions first.",
            "Use broad curvature and largest candidate patches to decide where a continuous surface should run.",
            "Use high-crease and concavity regions to plan true panel cuts, intake depths and hard edges.",
            "Build mechanical parts as separate editable assemblies; do not bake all fine reconstruction noise into the base shell.",
            "Render the generated candidate from the same orthographic/three-quarter cameras and compare section widths, silhouettes and recess depth.",
            "Always preserve the reference model; write any edited model as a second GLB.",
        ],
    }
    (out / "modeling_blueprint.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")

    summary = [
        "# Assetwright — Assistant Geometry Brief",
        "",
        "Measured from original 3D geometry, not imagined from a rendered picture.",
        "Reference: " + source_name,
        "SHA256: " + original_sha256,
        "Vertex/triangle counts: %d / %d" % (len(mesh.vertices), len(mesh.faces)),
        "Bounds (source units): " + repr(_bounds(mesh)["dimensions"]),
        "Length/up axis indices: %d / %d" % (length_axis, up_axis),
        "Section stations: %d with radial bins at each station." % len(section),
        "Largest candidate surface patches: %d." % len(patch),
        "Candidate high-complexity spatial regions: %d." % len(features),
        "",
        "## Read this packet in order",
        "1. modeling_blueprint.json (structured measurements)",
        "2. construction_deltas.json (if a generated candidate was supplied)",
        "3. sections.png, silhouettes.png, diagnostic colored GLBs (visual verification)",
        "",
        "## Important",
        "Radial profiles measure OUTER intersections only; missing bins are null.",
        "Patches and feature locations are geometric candidates, not proven semantic parts.",
        "High triangle count alone does not establish high surface fidelity.",
        "No automatic training or stored neural weights is performed.",
        "Build → render → measure → improve; maintain separate original and edited files.",
    ]
    if reference_mesh is not None:
        candidate_sections = _cross_sections(reference_mesh, length_axis)
        deltas = {
            "schema": "assetwright.construction_delta.v1",
            "reference": source_name,
            "registration": "Only matched axis selection and same relative station fractions. No ICP.",
            "status": "Diagnostics only; confirm model orientation and scale before interpreting.",
            "station_width_height_deltas": _compare_sections(section, candidate_sections),
            "reference_bounds": _bounds(mesh),
            "candidate_bounds": _bounds(reference_mesh),
        }
        (out / "construction_deltas.json").write_text(json.dumps(deltas, indent=2), encoding="utf-8")
    (out / "ASSISTANT_GEOMETRY_BRIEF.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return {"modeling_blueprint": str(out / "modeling_blueprint.json"),
            "brief": str(out / "ASSISTANT_GEOMETRY_BRIEF.md"),
            "sections": len(section), "major_patches": len(patch)}
