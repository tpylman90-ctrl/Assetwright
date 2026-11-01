"""Blender 3.6+/4.x headless importer and bounded geometry descriptor extractor.

Run: blender -b -t 2 --factory-startup --disable-autoexec --python \
       tools/mini_ai/blender_geometry_features.py -- /tmp/model.blend /tmp/features.json

This script never executes or saves original Blender project scripts.
No textures, meshes, GLBs or models are kept in the output: only a bounded
normalized geometry feature vector and counts.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from component_graph import build_graph
from mesh_islands import connected_bounds

MAX_OBJECTS = 500
MAX_TRIANGLES = 2_000_000
FEATURE_SCHEMA = "assetwright-geometry-descriptor-v1"

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 2:
        raise ValueError("Expected source model and descriptor output arguments")
    source, output = map(Path, args)
    assert source.is_file()
    ext = source.suffix.lower()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source), use_anim=False)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(source))
        else:
            bpy.ops.import_scene.obj(filepath=str(source))
    elif ext == ".glb":
        bpy.ops.import_scene.gltf(filepath=str(source))
    else:
        raise ValueError("Unsupported source extension: " + ext)
    dg = bpy.context.evaluated_depsgraph_get()
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects or len(objects) > MAX_OBJECTS:
        raise ValueError("No supported meshes or too many mesh objects")
    min_bound = [float("inf")] * 3
    max_bound = [-float("inf")] * 3
    total_triangles = 0
    total_vertices = 0
    total_surface = 0.0
    triangle_areas = []
    part_sizes = []
    part_boxes = []
    mesh_types = {}
    for obj in objects:
        evaluated = obj.evaluated_get(dg)
        mesh = evaluated.to_mesh()
        try:
            if mesh is None or not mesh.vertices:
                continue
            mesh.calc_loop_triangles()
            total_triangles += len(mesh.loop_triangles)
            total_vertices += len(mesh.vertices)
            if total_triangles > MAX_TRIANGLES:
                raise ValueError("Triangle budget exceeded")
            matrix = obj.matrix_world
            points = [matrix @ v.co for v in mesh.vertices]
            part_min = [float("inf")] * 3
            part_max = [-float("inf")] * 3
            for p in points:
                for axis in range(3):
                    part_min[axis] = min(part_min[axis], p[axis])
                    part_max[axis] = max(part_max[axis], p[axis])
                    min_bound[axis] = min(min_bound[axis], p[axis])
                    max_bound[axis] = max(max_bound[axis], p[axis])
            # Blender exporters often combine multiple disconnected shells
            # into one mesh object. Extract candidate geometric islands before
            # constructing proximity graphs, but do not invent semantic labels.
            islands = connected_bounds(
                points,
                (tuple(edge.vertices) for edge in mesh.edges),
                (tuple(tri.vertices) for tri in mesh.loop_triangles)
            )
            if len(islands) >= 2:
                part_boxes.extend(islands)
            else:
                part_boxes.append({
                    "min": part_min, "max": part_max,
                    "triangles": len(mesh.loop_triangles)
                })
            area = 0.0
            for tri in mesh.loop_triangles:
                a, b, c = (points[index] for index in tri.vertices)
                size = ((b - a).cross(c - a)).length * 0.5
                if math.isfinite(size):
                    area += size
                    if len(triangle_areas) < 2048:
                        triangle_areas.append(size)
            total_surface += area
            part_sizes.append(len(mesh.loop_triangles))
        finally:
            evaluated.to_mesh_clear()
    dims = [b - a for a, b in zip(min_bound, max_bound)]
    if total_triangles < 1 or not all(math.isfinite(x) and x > 0 for x in dims):
        raise ValueError("Degenerate geometry")
    largest = max(dims)
    sorted_dims = sorted(dims)
    ratio = [round(v / largest, 6) for v in sorted_dims]
    triangle_areas.sort()
    positive_areas = [a for a in triangle_areas if a > 0]
    med_area = positive_areas[len(positive_areas)//2] if positive_areas else 0
    max_part_ratio = max(part_sizes) / total_triangles
    # Dimensionless shape descriptors are orientation invariant: no assuming
    # source X/Y/Z identifies vehicle width, length, height.
    vector = [
        ratio[0], ratio[1],
        round(min(len(objects), 30) / 30, 6),
        round(min(total_triangles, MAX_TRIANGLES) / MAX_TRIANGLES, 6),
        round(min(total_vertices / max(total_triangles, 1), 3) / 3, 6),
        round(max_part_ratio, 6),
        round(min(total_surface / (largest * largest * 20), 1), 6),
        round(min(med_area / (largest * largest), 1), 6),
    ]
    # Never write raw model names/paths, textures or scene metadata.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "schema": FEATURE_SCHEMA,
        "normalization": "axis_sorted_scale_invariant",
        "feature_names": ["smallest_axis_ratio","middle_axis_ratio",
                          "mesh_parts_fraction","triangles_fraction",
                          "vertices_per_triangle","largest_part_fraction",
                          "normalized_surface_area","normalized_median_triangle_area"],
        "features": vector,
        "mesh_parts": len(objects),
        "triangles": total_triangles,
        "vertices": total_vertices,
        "component_graph": build_graph(part_boxes, min_bound, max_bound),
    }, sort_keys=True))
    print("ASSETWRIGHT_GEOMETRY_EXTRACTED", json.dumps({
        "triangles": total_triangles, "mesh_parts": len(objects)
    }))
if __name__ == "__main__":
    main()
