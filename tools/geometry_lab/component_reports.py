#!/usr/bin/env python3
"""Non-destructive source-component GLB analysis for Assetwright Geometry Lab.

Groups by actual named GLB scene nodes and geometry instances, not inferred
semantic segments. Reports separate robotic arm, gripper, battery cassette,
enclosure and cabinet ONLY when source names support those labels.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


CATEGORIES = ["robotic arm", "gripper", "battery cassette", "enclosure", "control cabinet"]


def category_from_name(text):
    s = text.lower().replace("_", " ").replace("-", " ")
    if "gripper" in s or "end effector" in s:
        return "gripper"
    if "battery" in s or "cassette" in s or "cell swap" in s:
        return "battery cassette"
    if "control cabinet" in s or "electrical cabinet" in s or "control panel" in s:
        return "control cabinet"
    if "enclosure" in s or "housing" in s:
        return "enclosure"
    if "robot" in s or "manipulator" in s or "arm assembly" in s:
        return "robotic arm"
    return None


def components(scene):
    if isinstance(scene,trimesh.Trimesh):
        yield "Mesh 0", "Mesh 0", scene
        return
    nodes = list(scene.graph.nodes_geometry)
    if not nodes:
        for geometry_name,mesh in scene.geometry.items():
            if isinstance(mesh,trimesh.Trimesh):
                yield str(geometry_name),str(geometry_name),mesh
        return
    for node_name in nodes:
        matrix,geometry_name = scene.graph[node_name]
        mesh = scene.geometry.get(geometry_name)
        if not isinstance(mesh,trimesh.Trimesh) or len(mesh.faces)==0:
            continue
        derivative = mesh.copy()
        derivative.apply_transform(matrix)
        yield str(node_name),str(geometry_name),derivative


def inspect(name,geom,mesh,threshold=35.0):
    vertices=np.asarray(mesh.vertices)
    faces=np.asarray(mesh.faces)
    triangles=vertices[faces]
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    double_area=np.linalg.norm(cross,axis=1)
    area=float(double_area.sum()*.5)
    degenerate=int(np.count_nonzero(double_area<=1e-12))
    # Because vertices may be split at UV seams, indexed boundary counts can
    # over-report physically open regions.
    keys=np.sort(mesh.edges,axis=1)
    unique,counts=np.unique(keys,axis=0,return_counts=True)
    boundary=int(np.count_nonzero(counts==1))
    nonmanifold=int(np.count_nonzero(counts>2))
    adjacent_angles=np.rad2deg(mesh.face_adjacency_angles)
    sharp=float(np.mean(adjacent_angles>=threshold)) if len(adjacent_angles) else None
    mean=float(np.mean(adjacent_angles)) if len(adjacent_angles) else None
    p95=float(np.percentile(adjacent_angles,95)) if len(adjacent_angles) else None
    density=len(faces)/max(area,1e-9)
    warning=[]
    if degenerate:warning.append("Degenerate triangle faces detected")
    if nonmanifold:warning.append("Non-manifold indexed edges detected")
    if boundary:warning.append("Indexed boundary edges present (could be UV seams)")
    if sharp is not None and sharp>.45:warning.append("High proportion of sharp adjacent face transitions")
    return {
        "node_name":name,"mesh_name":geom,
        "source_component_label":name+" / "+geom,
        "semantic_category":category_from_name(name+" "+geom),
        "category_basis":"source node/geometry name" if category_from_name(name+" "+geom) else "unclassified",
        "triangles":int(len(faces)),"vertices":int(len(vertices)),
        "area_source_units_squared":area,
        "triangle_density_source_units_squared":float(density),
        "bounds":[list(map(float,box)) for box in mesh.bounds],
        "degenerate_triangles":degenerate,
        "boundary_index_edges":boundary,
        "nonmanifold_index_edges":nonmanifold,
        "sharp_adjacent_edge_fraction":sharp,
        "mean_face_bend_angle_degrees":mean,
        "p95_face_bend_angle_degrees":p95,
        "diagnostic_flags":warning
    }


def report(source,out,raw_bytes=None):
    src=trimesh.load(str(source),force="scene",process=False)
    entries=[inspect(name,geom,mesh) for name,geom,mesh in components(src)]
    total=sum(e["triangles"] for e in entries) or 1
    density=np.array([e["triangle_density_source_units_squared"] for e in entries if e["triangles"]>=100],dtype=float)
    median=float(np.median(density)) if len(density)>1 else None
    for e in entries:
        e["fraction_of_model_triangles"]=e["triangles"]/total
        if len(entries)>=3 and e["fraction_of_model_triangles"]>0.4:
            e["diagnostic_flags"].append("Component uses >40% of model triangles; inspect allocation")
        if median and e["triangles"]>1000 and e["triangle_density_source_units_squared"]>4*median:
            e["diagnostic_flags"].append("Triangle density >4x comparable component median")
    requested={}
    for category in CATEGORIES:
        indices=[i for i,e in enumerate(entries) if e["semantic_category"]==category]
        requested[category]={
            "status":"found by source name" if indices else "not identified in source names",
            "component_indices":indices
        }
    packet={
        "schema":"assetwright.desktop_component_reports.v1",
        "input":str(source),
        "source_sha256":hashlib.sha256(raw_bytes if raw_bytes is not None else Path(source).read_bytes()).hexdigest(),
        "source_preserved":True,
        "grouping":"GLB scene node + geometry instance",
        "total_components":len(entries),
        "model_triangle_count":total,
        "requested_assembly_groups":requested,
        "components":entries,
        "limitations":[
            "Named GLB components are not guaranteed to be logical mechanical parts.",
            "A single fused source mesh cannot be reliably divided into semantic arm/cabinet parts.",
            "Source name category hints must be verified; no automatic semantic segmentation.",
            "Indexed mesh boundaries can indicate UV seams rather than true holes.",
            "Face-adjacency angles and density are heuristic surface quality signals.",
            "Units are source coordinate units and may not be metres.",
            "All source meshes and original GLBs are preserved."
        ]
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"component_reports.json").write_text(json.dumps(packet,indent=2),encoding="utf8")
    columns=[
        "node_name","mesh_name","semantic_category","triangles","vertices",
        "fraction_of_model_triangles","area_source_units_squared",
        "triangle_density_source_units_squared","degenerate_triangles",
        "boundary_index_edges","nonmanifold_index_edges","sharp_adjacent_edge_fraction",
        "mean_face_bend_angle_degrees","p95_face_bend_angle_degrees"
    ]
    with (out/"component_reports.csv").open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        w.writeheader();w.writerows(entries)
    print(json.dumps({"status":"passed","component_count":len(entries),
                      "triangles":total,"category_matches":requested},indent=2))
    return packet


def smoke(out):
    scene=trimesh.Scene()
    labels=["Robotic Arm","Gripper","Battery Cassette","Enclosure","Control Cabinet"]
    for i,label in enumerate(labels):
        mesh=trimesh.creation.box(extents=[1.,1.,1.])
        mesh.apply_translation([i*2.,0,0])
        scene.add_geometry(mesh,geom_name=label,node_name=label)
    out.mkdir(parents=True,exist_ok=True)
    fixture=out/"component_test_fixture.glb"
    scene.export(str(fixture))
    data=fixture.read_bytes()
    parsed=report(fixture,out,raw_bytes=data)
    assert parsed["total_components"]==5
    for category in CATEGORIES:
        assert parsed["requested_assembly_groups"][category]["component_indices"],category
    assert fixture.read_bytes()==data
    return parsed


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path)
    p.add_argument("--out",type=Path,default=Path("component-analysis"))
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:smoke(args.out)
    else:
        if not args.input:p.error("--input GLB required")
        raw=args.input.read_bytes()
        report(args.input,args.out,raw_bytes=raw)
        assert raw==args.input.read_bytes(),"Source changed during inspection"
if __name__=="__main__":
    main()
