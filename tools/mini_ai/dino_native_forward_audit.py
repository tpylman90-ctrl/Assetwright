"""Independent SHA-verified forward audit of learned original Kotlin GLBs.

Reads actual vertex/index buffers of target/student/constant-baseline assets.
No predicted file names, labels or AI-generated meshes substitute geometry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from dino_native_visual_school import expected_stems,read_source
from generated_glb_critic import _read_glb,_accessor,inspect

SCHEMA="assetwright-native-visual-reconstruction-v1"


def positions(path:Path):
    doc,buffer,digest=_read_glb(path)
    if len(doc.get("meshes",[]))!=1 or len(doc["meshes"][0]["primitives"])!=1:
        raise ValueError("Expected one original Kotlin shell")
    primitive=doc["meshes"][0]["primitives"][0]
    vertices=_accessor(doc,buffer,primitive["attributes"]["POSITION"],"positions")
    indices=_accessor(doc,buffer,primitive["indices"],"indices")
    return vertices,indices,digest


def audited(path:Path):
    report=inspect(path)
    if not (report["mesh_parts"]==1 and 900<=report["triangles"]<=3000
        and report["boundary_edges"]==0 and report["nonmanifold_edges"]==0
        and report["invalid_triangles"]==0 and report["inverted_closed_parts"]==0
        and report["parts"][0]["signed_volume"]>0):
        raise ValueError("Predicted native GLB has invalid actual topology")
    return report


def distance(target:Path,reconstruction:Path)->float:
    a,ai,_=positions(target)
    b,bi,_=positions(reconstruction)
    if len(a)!=len(b) or ai!=bi:
        raise ValueError("Source and own reconstructed GLBs do not share audited topology")
    mins=[min(v[i] for v in a) for i in range(3)]
    maxes=[max(v[i] for v in a) for i in range(3)]
    diagonal=math.sqrt(sum((hi-lo)**2 for lo,hi in zip(mins,maxes)))
    if diagonal<.1:
        raise ValueError("Degenerate target dimensions")
    error=sum(sum((x-y)**2 for x,y in zip(aa,bb)) for aa,bb in zip(a,b))
    return math.sqrt(error/(len(a)*3))/diagonal


def verify_reconstructed(source:Path,out:Path)->dict:
    target_cases={key:value for key,value in expected_stems().items()
                  if value[0]=="validation"}
    expected={stem+"__"+variant for stem in target_cases
              for variant in ("student","constant")}
    source_files={p.stem for p in out.glob("*.glb")}
    metadata_files={p.stem for p in out.glob("*.json")}
    if source_files!=expected or metadata_files!=expected:
        raise ValueError("Incomplete independent reconstructed original GLB batch")
    rows=[]
    for stem,identity in sorted(target_cases.items()):
        ground=read_source(source,stem,identity)
        source_path=source/(stem+".glb")
        assert audited(source_path)["model_sha256"]==ground["source_glb_sha256"]
        comparisons={}
        for variant in ("student","constant"):
            path=out/(stem+"__"+variant+".glb")
            report=audited(path)
            meta=json.loads(path.with_suffix(".json").read_text())
            if (meta.get("schema")!=SCHEMA or meta.get("case")!=stem
                or meta.get("variant")!=variant
                or meta.get("source_engine")!="AssetWright-AdvancedFormLab"
                or meta.get("reference_glb_sha256")!=ground["source_glb_sha256"]
                or meta.get("generated_glb_sha256")!=report["model_sha256"]):
                raise ValueError("Untrusted reconstructed native geometry record")
            operation=meta["chosen_operation"]
            if operation not in ("SECTION_LOFT","TANGENT_SWEEP","SECTION_TWIST",
                    "SUPERELLIPSE_PROFILE","LOWER_RECESS","RIBBED_FAIRING"):
                raise ValueError("Unknown native operation in actual mesh")
            strength=meta["chosen_strength"]
            if type(strength) not in (float,int) or not math.isfinite(strength) or not 0<=strength<=1:
                raise ValueError("Invalid original native prediction")
            comparisons[variant]={"operation":operation,
                                  "strength":strength,
                                  "rmse_normalized":distance(source_path,path),
                                  "sha256":report["model_sha256"],
                                  "triangles":report["triangles"]}
        rows.append({"case":stem,"target_source_sha256":ground["source_glb_sha256"],
                     "target_operation":ground["operation"],
                     "target_strength":ground["strength"],**comparisons})
    student_mse=sum(row["student"]["rmse_normalized"] for row in rows)/len(rows)
    baseline_mse=sum(row["constant"]["rmse_normalized"] for row in rows)/len(rows)
    correct=sum(row["student"]["operation"]==row["target_operation"] for row in rows)
    mean_strength=sum(abs(row["student"]["strength"]-row["target_strength"])
                      for row in rows)/len(rows)
    gain=(baseline_mse-student_mse)/baseline_mse if baseline_mse else 0.
    report={
        "schema":"assetwright-dino-original-forward-native-glb-audit-v1",
        "actual_original_target_glbs":len(rows),
        "actual_student_reconstructed_glbs":len(rows),
        "actual_constant_baseline_glbs":len(rows),
        "original_source_engine":"AssetWright-Kotlin-AdvancedFormLab",
        "original_native_vertices_and_indices_compared":True,
        "all_meshes_independently_structurally_valid":True,
        "predicted_operator_accuracy":correct/len(rows),
        "predicted_strength_mae":mean_strength,
        "student_mean_normalized_vertex_rmse":student_mse,
        "constant_mean_normalized_vertex_rmse":baseline_mse,
        "forward_improvement_fraction":gain,
        "strict_forward_geometry_gate":gain>=.10 and correct/len(rows)>=.55,
        "student_requires_dino_at_inference":False,
        "external_ai_meshes_used":False,
        "android_deployed":False,
        "human_visual_approval":False,
        "status":"audited_development_forward_geometry",
        "note":"Heldout synthetic source families; real native geometry checked, not aesthetic or open-domain ability.",
        "cases":rows
    }
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--reconstructed",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=verify_reconstructed(a.source,a.reconstructed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="cases"},indent=2))


if __name__=="__main__":
    main()
