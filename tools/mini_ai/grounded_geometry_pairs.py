"""Join CC0 publisher descriptions to independently inspected Blender geometry.

Requires exact source asset ID, official CC0 provenance, valid SHA-256 and
bounded geometry descriptors. Objaverse caption-only records are not silently
treated as geometry pairs. Labels are not inferred from AABB proximity.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from pathlib import Path

SCHEMA = "assetwright-grounded-text-mesh-pairs-v1"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
MAX_PAIRS = 20000


def valid_geometry(item:dict)->bool:
    if item.get("license")!="CC0-1.0" or item.get("mesh_analysis")!="blender_geometry_inspected":
        return False
    geom=item.get("geometry")
    if not isinstance(geom,dict) or geom.get("schema")!="assetwright-geometry-descriptor-v1":
        return False
    sha=geom.get("source_sha256")
    vector=geom.get("features")
    if not isinstance(sha,str) or not HEX64.fullmatch(sha):
        return False
    if not isinstance(vector,list) or len(vector)!=8 or any(
        type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in vector):
        return False
    return True


def match(catalog:dict, research:dict)->tuple[dict,dict]:
    if catalog.get("schema")!="assetwright-description-geometry-catalog-v1":
        raise ValueError("Unrecognized description catalog")
    if research.get("schema")!="assetwright-cc0-shape-study-v1":
        raise ValueError("Unrecognized Blender study")
    by_id={}
    for item in research.get("assets",[]):
        if not isinstance(item,dict) or not valid_geometry(item):
            continue
        key=item.get("id")
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",key):
            continue
        # An ID collision with different geometry means the data is ambiguous.
        if key in by_id and item["geometry"]["source_sha256"]!=by_id[key]["geometry"]["source_sha256"]:
            by_id[key]=None
        elif key not in by_id:
            by_id[key]=item
    used_sha=set()
    rows=[]
    for row in catalog.get("records",[]):
        if not isinstance(row,dict) or row.get("source")!="Poly Haven" or row.get("license")!="CC0-1.0":
            continue
        id=row.get("id")
        source=by_id.get(id)
        if not isinstance(source,dict):
            continue
        text=row.get("publisher_description")
        name=row.get("name")
        if not isinstance(text,str) or len(text.strip())<12 or not isinstance(name,str) or not name.strip():
            continue
        if row.get("description_origin")!="publisher_metadata":
            continue
        sha=source["geometry"]["source_sha256"]
        if sha in used_sha:
            continue
        used_sha.add(sha)
        mesh=source["geometry"]
        pairs={
            "source_object_id":id,
            "source_page":row.get("source_page",""),
            "source":"Poly Haven",
            "license":"CC0-1.0",
            "source_mesh_sha256":sha,
            "source_mesh_format":mesh.get("source_format","unknown"),
            "caption":name.strip()+": "+text.strip(),
            "caption_origin":"publisher_metadata",
            "geometry_features":mesh["features"],
            "triangle_count":mesh.get("triangles"),
            "component_graph":mesh.get("component_graph"),
            "semantic_part_labels_status":"not_verified",
            "verified_component_roles":[],
        }
        rows.append(pairs)
        if len(rows)>=MAX_PAIRS:
            break
    report={
        "schema":"assetwright-grounded-pairs-report-v1",
        "descriptive_catalog_models":len(catalog.get("records",[])),
        "blender_study_models":len(research.get("assets",[])),
        "verified_text_mesh_pairs":len(rows),
        "unique_mesh_hashes":len(used_sha),
        "with_spatial_graph":sum(isinstance(p.get("component_graph"),dict)
                                 and p["component_graph"].get("part_count",0)>=2 for p in rows),
        "with_verified_component_roles":0,
        "note":"Publisher caption + exact Poly Haven source object + Blender mesh SHA. No inferred part identity."
    }
    return {"schema":SCHEMA,"pairs":rows},report


def run(catalog_file:Path,study_file:Path,out:Path,report_file:Path)->dict:
    catalog=json.loads(catalog_file.read_text(encoding="utf-8"))
    research=json.loads(study_file.read_text(encoding="utf-8"))
    matches,report=match(catalog,research)
    out.parent.mkdir(parents=True,exist_ok=True)
    report_file.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(matches,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    report_file.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--catalog",type=Path,required=True)
    cli.add_argument("--study",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    cli.add_argument("--report",type=Path,required=True)
    x=cli.parse_args()
    run(x.catalog,x.study,x.out,x.report)
