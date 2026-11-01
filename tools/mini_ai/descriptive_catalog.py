#!/usr/bin/env python3
"""Build a CC0 text/object-shape corpus from Poly Haven's official model API.

Never scrape websites, invent descriptions, relicense external metadata, or
claim geometry was downloaded unless a source hash and Blender descriptor
exist. Original publisher metadata is kept separate from computed features.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

SCHEMA = "assetwright-description-geometry-catalog-v1"
MAX_MODELS = 20_000
MAX_TEXT = 1300
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
ALLOWED_ATTRS = {"material", "condition", "style", "color", "colors",
                 "rigged", "animated", "origin", "category", "size",
                 "setting", "object_type", "surface", "use"}


def safe_text(value: object, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    return text[:limit]


def axis_ratios(raw: object) -> list[float] | None:
    if not isinstance(raw, (list,tuple)) or len(raw) != 3:
        return None
    if not all(type(v) in (float,int) and math.isfinite(v) and v > 0 for v in raw):
        return None
    values = sorted(float(x) for x in raw)
    if values[-1] > 1e12 or values[0] < 1e-10:
        return None
    return [round(values[0]/values[2],6), round(values[1]/values[2],6)]


def attributes(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}
    result = {}
    for name, data in raw.items():
        if name not in ALLOWED_ATTRS:
            continue
        if type(data) in (str,int,float,bool):
            value = safe_text(str(data),90)
            if value:
                result[name] = value
        elif isinstance(data,list):
            items = [safe_text(v,50) for v in data[:8] if isinstance(v,str)]
            result[name] = [s for s in items if s]
    return result


def build(catalog: dict, historical: dict | None = None) -> tuple[dict,dict]:
    if not isinstance(catalog,dict):
        raise ValueError("Official model catalog must be a JSON object")
    linked = {}
    if isinstance(historical,dict) and historical.get("schema")=="assetwright-cc0-shape-study-v1":
        for item in historical.get("assets",[]):
            if not isinstance(item,dict):
                continue
            geometry = item.get("geometry")
            if not isinstance(geometry,dict):
                continue
            if item.get("license")!="CC0-1.0" or item.get("mesh_analysis")!="blender_geometry_inspected":
                continue
            identifier = item.get("id")
            sha = geometry.get("source_sha256")
            features = geometry.get("features")
            if isinstance(identifier,str) and isinstance(sha,str) and len(sha)==64 and \
               isinstance(features,list) and len(features)==8:
                linked[identifier] = {"sha256":sha,
                                      "features":features}
    records=[]
    for asset_id,item in sorted(catalog.items()):
        if not isinstance(asset_id,str) or not ID_RE.fullmatch(asset_id):
            continue
        if not isinstance(item,dict) or item.get("type")!=2:
            continue
        name=safe_text(item.get("name"),140)
        description=safe_text(item.get("description"))
        category=safe_text(item.get("category"),200)
        if not name:
            continue
        tags=[safe_text(x,48) for x in item.get("tags",[])[:24]
              if isinstance(x,str)] if isinstance(item.get("tags"),list) else []
        facets=attributes(item.get("attributes"))
        ratio=axis_ratios(item.get("dimensions"))
        # Do not let generated or unlicensed inferred captions masquerade as
        # creator-provided descriptions. Separate these fields explicitly.
        record={
            "id":asset_id, "source":"Poly Haven","license":"CC0-1.0",
            "source_page":"https://polyhaven.com/a/"+asset_id,
            "name":name,"publisher_description":description,
            "category":category,"tags":tags,"facets":facets,
            "dimension_ratios":ratio,
            "description_origin":"publisher_metadata",
            "description_quality":"descriptive" if len(description)>=60 else
                                  "short" if description else "missing",
        }
        if asset_id in linked:
            record["verified_blender_geometry"] = linked[asset_id]
        records.append(record)
        if len(records)>=MAX_MODELS:
            break
    counts=Counter(r["description_quality"] for r in records)
    categories=Counter(r["category"].split("/")[0] or "Uncategorized" for r in records)
    reported={
        "schema":"assetwright-description-geometry-report-v1",
        "source":"Poly Haven","license":"CC0-1.0",
        "total_models":len(records),
        "with_publisher_descriptions":sum(bool(r["publisher_description"]) for r in records),
        "with_descriptive_60_char_text":counts["descriptive"],
        "with_structured_attributes":sum(bool(r["facets"]) for r in records),
        "with_published_dimensions":sum(r["dimension_ratios"] is not None for r in records),
        "with_verified_blender_geometry":sum("verified_blender_geometry" in r for r in records),
        "top_category_families":categories.most_common(20),
        "description_notes":"Descriptions and tags are publisher metadata; not human-verified construction labels.",
        "license_source":"https://polyhaven.com/license",
        "api_credit":"Powered by Poly Haven",
    }
    return {"schema":SCHEMA,"source":"Poly Haven",
            "license":"CC0-1.0","records":records},reported


def run(out:Path, report_out:Path,history:Path|None=None) -> dict:
    # Import here to keep the pure data extractor testable without network.
    from forge_asset_cycle import api_json
    raw=api_json("/assets?t=models")
    previous=(json.loads(history.read_text(encoding="utf-8"))
              if history is not None and history.is_file() else None)
    dataset, report=build(raw,previous)
    if not dataset["records"]:
        raise ValueError("Official API returned no usable model records")
    out.parent.mkdir(parents=True,exist_ok=True)
    report_out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dataset,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    report_out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out",type=Path,required=True)
    cli.add_argument("--report",type=Path,required=True)
    cli.add_argument("--history",type=Path)
    args=cli.parse_args()
    run(args.out,args.report,args.history)
