"""Accumulate ONLY derived, licensed geometry observations across study cycles.

Stores no source meshes, textures or private Android training examples.
A unique source SHA-256 deduplicates retried Poly Haven downloads.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SCHEMA = "assetwright-cc0-shape-study-v1"
MAX_RECORDS = 200


def merge(current: dict, previous: dict | None = None) -> dict:
    if current.get("schema") != SCHEMA:
        raise ValueError("Unrecognized current study")
    if previous is not None and previous.get("schema") != SCHEMA:
        raise ValueError("Unrecognized previous study")
    by_hash = {}
    cycles = set()
    attempted = set()
    for source in (previous, current):
        if source is None:
            continue
        if isinstance(source.get("cycles"),list):
            cycles.update(i for i in source["cycles"] if type(i) is int and 0<i<=100000)
        if type(source.get("cycle")) is int:
            cycles.add(source["cycle"])
        for key in source.get("attempted_ids", []):
            if isinstance(key,str) and key and len(key)<=100:
                attempted.add(key)
        for item in source.get("assets",[]):
            key=item.get("id")
            if isinstance(key,str) and key and len(key)<=100:
                attempted.add(key)
            if item.get("license") != "CC0-1.0" or item.get("mesh_analysis") != "blender_geometry_inspected":
                continue
            geometry = item.get("geometry")
            if not isinstance(geometry,dict):
                continue
            sha = geometry.get("source_sha256")
            if not isinstance(sha,str) or len(sha)!=64 or not all(c in "0123456789abcdef" for c in sha):
                continue
            features = geometry.get("features")
            if not isinstance(features,list) or len(features)!=8:
                continue
            graph = geometry.get("component_graph")
            if graph is not None and (not isinstance(graph,dict) or
                                      graph.get("schema")!="assetwright-component-graph-v1"):
                continue
            by_hash[sha] = {
                "id":str(item.get("id",""))[:100],
                "source_page":str(item.get("source_page",""))[:250],
                "license":"CC0-1.0",
                "mesh_analysis":"blender_geometry_inspected",
                "geometry":{
                    "schema":"assetwright-geometry-descriptor-v1",
                    "source_sha256":sha,
                    "features":features,
                    **({"component_graph":graph} if graph is not None else {})
                }
            }
    if len(by_hash)>MAX_RECORDS:
        # Keep deterministic rather than biasing to most recent re-downloads.
        by_hash = dict(sorted(by_hash.items())[:MAX_RECORDS])
    return {
        "schema":SCHEMA,"cycle":current.get("cycle"),
        "cycles":sorted(cycles),
        "attempted_ids":sorted(attempted)[:3000],
        "source":"Poly Haven CC0",
        "assets":[by_hash[k] for k in sorted(by_hash)],
        "source_count":len(by_hash),
        "geometry_inspected_count":len(by_hash),
        "model_training_performed":False,
        "android_model_updated":False,
        "note":"Only compact derived observations; no raw meshes or semantic joint labels"
    }


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--current",type=Path,required=True)
    cli.add_argument("--previous",type=Path)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    current=json.loads(args.current.read_text(encoding="utf-8"))
    previous=(json.loads(args.previous.read_text(encoding="utf-8"))
              if args.previous and args.previous.is_file() else None)
    merged=merge(current,previous)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(merged,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Unique CC0 geometry records across",len(merged["cycles"]),"cycles:",
          len(merged["assets"]))


if __name__=="__main__":
    main()
