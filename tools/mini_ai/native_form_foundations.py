"""Original CPU form-classification student, grounded in Kotlin-built GLBs.

No externally generated meshes, pretrained weights or source-label features.
Heldout native shape families are an INTERNAL development test only.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
from generated_glb_critic import inspect,_read_glb,_accessor

SCHEMA="assetwright-native-form-foundation-v1"
MODEL="assetwright-owned-geometric-form-student-v1"
KINDS=("CYLINDER","ROUNDED_BOX","ELLIPSOID","TAPERED_LOFT","ARCH_SWEEP")
TRAIN_FAMILIES=("train1","train2","train3")
VALIDATION_FAMILIES=("validation1","validation2")
TRAIN_CONTROLS=(.35,.60,.90)
VALID_CONTROLS=(.45,.75)
FEATURE_NAMES=("end_taper","mid_bulge","lateral_path_bend","corner_fullness")

def shape_features(path:Path)->tuple[list[float],dict]:
    doc,blob,_=_read_glb(path)
    if len(doc.get("meshes",[]))!=1 or len(doc["meshes"][0].get("primitives",[]))!=1:
        raise ValueError("Expected exactly one connected original form")
    primitive=doc["meshes"][0]["primitives"][0]
    coords=_accessor(doc,blob,primitive["attributes"]["POSITION"],"positions")
    rings=defaultdict(list)
    for x,y,z in coords:
        rings[round(z,4)].append((x,y))
    rings=[(z,pts) for z,pts in sorted(rings.items()) if len(pts)>=16]
    if len(rings)<9 or len({len(pts) for _,pts in rings})>2:
        raise ValueError("Missing regular original cross sections")
    extents=[]
    for _,ring in rings:
        xs=[x for x,_ in ring]; ys=[y for _,y in ring]
        xmid=(min(xs)+max(xs))*.5
        zmid=(min(ys)+max(ys))*.5
        rx=(max(xs)-min(xs))*.5
        rz=(max(ys)-min(ys))*.5
        if rx<=.001 or rz<=.001:
            raise ValueError("Collapsed sampled cross section")
        extents.append((xmid,zmid,rx,rz,ring))
    first,last,center=extents[0],extents[-1],extents[len(extents)//2]
    widths=[e[2] for e in extents]
    end_taper=abs(first[2]-last[2])/max(.001,(first[2]+last[2])*.5)
    mid_bulge=1.-(first[2]+last[2])/(2*max(widths))
    total_width=max(x for _,pts in rings for x,_ in pts)-min(x for _,pts in rings for x,_ in pts)
    lateral_bend=abs(center[0]-(first[0]+last[0])*.5)/max(.001,total_width*.5)
    corner=max(abs(x-center[0])/center[2]*abs(y-center[1])/center[3]
               for x,y in center[4])
    features=[end_taper,mid_bulge,lateral_bend,corner]
    if any(not math.isfinite(x) or x<-.002 or x>3 for x in features):
        raise ValueError("Unphysical measured morphology")
    return features,{"ring_count":len(rings),"source_vertices":len(coords)}

def read_source(root:Path,stem:str)->dict:
    manifest=json.loads((root/(stem+".json")).read_text())
    path=root/(stem+".glb")
    raw=path.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    pieces=stem.split("__")
    if len(pieces)!=4:
        raise ValueError("Malformed original study case")
    phase,family,kind,level=pieces
    if not (manifest.get("schema")==SCHEMA and manifest.get("case")==stem
            and manifest.get("source_glb_sha256")==sha
            and manifest.get("original_generator")=="AssetWright-Kotlin-NativeFormLab"
            and manifest.get("phase")==phase and manifest.get("family")==family
            and manifest.get("kind")==kind.upper() and kind.upper() in KINDS):
        raise ValueError("Untrusted or mislabeled original GLB")
    if phase=="train":
        families=TRAIN_FAMILIES; strengths=TRAIN_CONTROLS
        levels=("s350","s600","s900")
    elif phase=="validation":
        families=VALIDATION_FAMILIES; strengths=VALID_CONTROLS
        levels=("s450","s750")
    else:
        raise ValueError("Unrecognized split")
    if family not in families or level not in levels:
        raise ValueError("Unrecognized source family or strength level")
    if abs(manifest.get("control",-1)-strengths[levels.index(level)])>1e-6:
        raise ValueError("Misreported original native parameter")
    if any(type(manifest.get(key)) not in (int,float) or not math.isfinite(manifest[key])
           for key in ("length","width","height")):
        raise ValueError("Invalid original dimensions")
    structural=inspect(path)
    if (structural["model_sha256"]!=sha or structural["mesh_parts"]!=1
            or structural["triangles"]>5000 or structural["triangles"]<200
            or structural["boundary_edges"]!=0
            or structural["nonmanifold_edges"]!=0
            or structural["invalid_triangles"]!=0
            or structural["inverted_closed_parts"]!=0
            or structural["parts"][0]["signed_volume"]<=0):
        raise ValueError("Native form failed independent mesh topology audit")
    features,extra=shape_features(path)
    return {"sha256":sha,"stem":stem,"phase":phase,"family":family,
            "class":kind.upper(),"features":features,
            "triangles":structural["triangles"],"morphology":extra}

def load_dataset(folder:Path)->list[dict]:
    expected=[f"{phase}__{family}__{kind.lower()}__{level}"
              for phase,families,levels in (
                  ("train",TRAIN_FAMILIES,("s350","s600","s900")),
                  ("validation",VALIDATION_FAMILIES,("s450","s750")))
              for family in families for kind in KINDS for level in levels]
    discovered={p.stem for p in folder.glob("*.json")}
    if discovered!=set(expected):
        raise ValueError("Incomplete or unexpected original native form curriculum")
    rows=[read_source(folder,stem) for stem in expected]
    hashes=[r["sha256"] for r in rows]
    if len(set(hashes))!=len(hashes):
        raise ValueError("Duplicated native GLB train/validation source")
    if set(r["family"] for r in rows if r["phase"]=="train") & set(
        r["family"] for r in rows if r["phase"]=="validation"):
        raise ValueError("Source-family leakage")
    return rows

def fit_student(rows:list[dict],epochs:int=1000)->dict:
    """Fit original from-scratch five-class linear softmax on GLB geometry."""
    if len(rows)!=45 or any(r["phase"]!="train" for r in rows):
        raise ValueError("Exactly 45 original native training forms required")
    if Counter(r["class"] for r in rows)!={kind:9 for kind in KINDS}:
        raise ValueError("Imbalanced geometry learning examples")
    means=[sum(r["features"][i] for r in rows)/len(rows)
           for i in range(len(FEATURE_NAMES))]
    scales=[max(.04,math.sqrt(sum((r["features"][i]-means[i])**2
             for r in rows)/len(rows))) for i in range(len(means))]
    dimensions=len(means)+1
    weights=[[0.0]*dimensions for _ in KINDS]
    for _ in range(epochs):
        gradient=[[0.0]*dimensions for _ in KINDS]
        for row in rows:
            x=[(v-avg)/std for v,avg,std in zip(row["features"],means,scales)]+[1.]
            logits=[sum(wi*xi for wi,xi in zip(w,x)) for w in weights]
            top=max(logits)
            e=[math.exp(v-top) for v in logits]
            total=sum(e)
            for j in range(len(KINDS)):
                delta=e[j]/total-(1. if KINDS[j]==row["class"] else 0.)
                for k in range(dimensions):
                    gradient[j][k]+=delta*x[k]/len(rows)
        for j in range(len(KINDS)):
            for k in range(dimensions):
                penalty=.002*weights[j][k] if k<dimensions-1 else 0.
                weights[j][k]-=.18*(gradient[j][k]+penalty)
    return {"schema":MODEL,"classes":list(KINDS),
            "feature_names":list(FEATURE_NAMES),"mean":means,"std":scales,
            "weights":weights,"training_source_sha256":sorted(r["sha256"] for r in rows),
            "training_samples":len(rows),"method":"from-scratch-multinomial-logistic",
            "frozen_previous_operator_model":True,"android_deployable":False}

def predict(model:dict,features:list[float])->tuple[str,float]:
    x=[(v-avg)/std for v,avg,std in zip(features,model["mean"],model["std"])]+[1.]
    logits=[sum(wi*xi for wi,xi in zip(w,x)) for w in model["weights"]]
    top=max(logits)
    shifted=[math.exp(v-top) for v in logits]
    best=max(range(len(logits)),key=lambda i:logits[i])
    return model["classes"][best],shifted[best]/sum(shifted)

def score(model:dict,rows:list[dict])->dict:
    predictions=[]
    for row in rows:
        guess,confidence=predict(model,row["features"])
        predictions.append({"source_sha256":row["sha256"],
            "expected":row["class"],"predicted":guess,
            "confidence":round(confidence,6),"correct":guess==row["class"]})
    per_class={kind:sum(p["correct"] for p in predictions if p["expected"]==kind)
               for kind in KINDS}
    return {"sample_count":len(rows),
            "accuracy":sum(p["correct"] for p in predictions)/len(rows),
            "per_class_correct":per_class,"per_class_total":len(rows)//len(KINDS),
            "predictions":predictions}

def run(source:Path,out:Path)->dict:
    rows=load_dataset(source)
    train=[r for r in rows if r["phase"]=="train"]
    heldout=[r for r in rows if r["phase"]=="validation"]
    candidate=fit_student(train)
    heldout_results=score(candidate,heldout)
    counts=Counter(r["class"] for r in train)
    majority=max(KINDS,key=lambda k:counts[k])
    baseline=sum(r["class"]==majority for r in heldout)/len(heldout)
    passed=(heldout_results["accuracy"]>=.90
            and all(v>=3 for v in heldout_results["per_class_correct"].values())
            and heldout_results["accuracy"]-baseline>=.60)
    summary={"schema":"assetwright-native-form-foundations-evaluation-v1",
        "status":"passed_development_holdout" if passed else "rejected_development_candidate",
        "source":"65 original source-hashed native Kotlin GLBs",
        "train_glbs":len(train),"heldout_glbs":len(heldout),
        "train_families":list(TRAIN_FAMILIES),
        "heldout_families":list(VALIDATION_FAMILIES),
        "note":"Synthetic split by native generator dimensions; NOT independent real-world assets",
        "baseline_majority_accuracy":baseline,
        "candidate_accuracy":heldout_results["accuracy"],
        "per_class_correct":heldout_results["per_class_correct"],
        "per_class_total":heldout_results["per_class_total"],
        "all_meshes_structurally_valid":True,
        "train_source_hashes":candidate["training_source_sha256"],
        "heldout_source_hashes":sorted(r["sha256"] for r in heldout),
        "external_ai_geometry_used":False,
        "previous_native_vehicle_model_modified":False,
        "android_deployed":False}
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(summary,indent=2)+"\n")
    (out/"development_predictions.json").write_text(json.dumps(heldout_results,indent=2)+"\n")
    (out/"candidate_shape_student.json").write_text(json.dumps(candidate,indent=2)+"\n")
    if not passed:
        raise SystemExit("Development form learner REJECTED; diagnostic evidence retained")
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.source,args.out),indent=2))
