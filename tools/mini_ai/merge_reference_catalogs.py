"""Merge licensed publisher descriptions and attributed CC0 Objaverse captions.

Keep caption licenses and asset licenses distinct. Do not relabel machine-
generated Cap3D captions as descriptions written by original model artists.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SCHEMA="assetwright-description-geometry-catalog-v1"

from semantic_reference_search import words

def caption_agreement(record:dict)->str:
    """Conservative lexical gate, NOT visual verification of model captions."""
    caption=record.get("cap3d_generated_caption") or ""
    if not caption:
        return "missing"
    name=set(words(record.get("name","")))
    described=set(words(
        record.get("publisher_description","")+" "+" ".join(record.get("tags",[]))))
    described.update(name)
    generated=set(words(caption))
    title_overlap=len(name&generated)
    description_overlap=len(described&generated)
    # Material disagreement is an explicit mismatch signal; one material
    # in the original may not match an entirely different caption material.
    material_groups=(
        {"bronze","copper","steel","iron","aluminium","aluminum"},
        {"porcelain","ceramic","clay","pottery"},
        {"wood","wooden","timber"},
        {"plastic","polymer","rubber"},
    )
    source_material={i for i,group in enumerate(material_groups)
                     if group&described}
    generated_material={i for i,group in enumerate(material_groups)
                        if group&generated}
    if source_material and generated_material and not (
        source_material&generated_material
    ):
        return "material_conflict"
    if title_overlap>=2 or (title_overlap>=1 and description_overlap>=2) or description_overlap>=3:
        return "lexically_supported_unverified"
    return "no_lexical_support"




def combine(poly:dict, objaverse:dict)->tuple[dict,dict]:
    if poly.get("schema")!=SCHEMA:
        raise ValueError("Unknown Poly Haven catalog")
    if objaverse.get("schema")!="assetwright-objaverse-verified-cc0-captions-v1":
        raise ValueError("Unknown Objaverse caption catalog")
    rows=[]
    for x in poly.get("records",[]):
        if x.get("license")=="CC0-1.0":
            rows.append(dict(x))
    cap_count=0
    cap_supported=0
    cap_quarantined=0
    for x in objaverse.get("records",[]):
        if x.get("object_license")!="CC0-1.0":
            continue
        if x.get("metadata_license")!="ODC-BY-1.0":
            continue
        uid=x.get("uid")
        if not isinstance(uid,str) or len(uid)!=32:
            continue
        caption=x.get("cap3d_generated_caption","")
        cap_license=x.get("cap3d_caption_license")
        if caption and cap_license!="ODC-BY-1.0":
            continue
        agreement=caption_agreement(x)
        if caption:
            cap_count+=1
            if agreement=="lexically_supported_unverified":
                cap_supported+=1
            else:
                cap_quarantined+=1
        rows.append({
            "id":"objaverse_"+uid,
            "source":"Objaverse 1.0",
            "license":"CC0-1.0",
            "source_page":x.get("original_asset_page") or
                "https://huggingface.co/datasets/allenai/objaverse",
            "source_asset_uid":uid,
            "name":x.get("name",""),
            "publisher_description":x.get("publisher_description",""),
            # Only conservatively supported automated captions are indexed
            # for modeling reference retrieval. Retain rejected ones for audit.
            "caption_text":caption if agreement=="lexically_supported_unverified" else "",
            "quarantined_caption":caption if caption and agreement!="lexically_supported_unverified" else "",
            "caption_agreement":agreement,
            "caption_origin":"Cap3D model-generated; not independently verified" if caption else None,
            "caption_license":"ODC-BY-1.0" if caption else None,
            "metadata_license":"ODC-BY-1.0",
            "metadata_source":x.get("metadata_source"),
            "caption_source":x.get("cap3d_source"),
            "category":"",
            "tags":x.get("tags",[]),
            "facets":{},
            "dimension_ratios":None,
            "description_quality":"descriptive" if len(caption or x.get("publisher_description",""))>=60 else "short",
        })
    report={
        "schema":"assetwright-merged-reference-coverage-v1",
        "records_total":len(rows),
        "poly_haven_cc0":sum(r["source"]=="Poly Haven" for r in rows),
        "objaverse_verified_cc0":sum(r["source"]=="Objaverse 1.0" for r in rows),
        "objaverse_with_cap3d":cap_count,
        "cap3d_lexically_supported_for_retrieval":cap_supported,
        "cap3d_quarantined_from_retrieval":cap_quarantined,
        "with_published_3d_dimensions":sum(r.get("dimension_ratios") is not None for r in rows),
        "with_actual_blender_mesh_features":sum("verified_blender_geometry" in r for r in rows),
        "license_note":"CC0 object rights; Objaverse/Cap3D metadata and generated captions separately ODC-By",
        "disclaimer":"Retrieval library only. Generated captions can be inaccurate; no semantic joints or mesh construction operations verified."
    }
    return {"schema":SCHEMA,"source":"Poly Haven CC0 and Objaverse verified CC0",
            "license_note":report["license_note"],"records":rows},report


def run(poly_path:Path,obj_path:Path,out:Path,report:Path)->dict:
    poly=json.loads(poly_path.read_text(encoding="utf-8"))
    objs=json.loads(obj_path.read_text(encoding="utf-8"))
    merged,summary=combine(poly,objs)
    out.parent.mkdir(parents=True,exist_ok=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(merged,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    report.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--poly",type=Path,required=True)
    cli.add_argument("--objaverse",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    cli.add_argument("--report",type=Path,required=True)
    args=cli.parse_args()
    run(args.poly,args.objaverse,args.out,args.report)
