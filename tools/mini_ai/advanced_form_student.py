"""Advanced form morphology and inverse-control learning on ORIGINAL Kotlin GLBs.

Trains a 6-class from-scratch softmax and six measured response curves using
only actual source-hashed positions. Class labels and construction commands
are SUPERVISION only, never feature inputs. No pretrained mesh generator.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

from generated_glb_critic import _accessor, _read_glb, inspect

SCHEMA = "assetwright-advanced-native-forms-v1"
MODEL = "assetwright-advanced-geometry-student-v1"
OPERATIONS = (
    "SECTION_LOFT", "TANGENT_SWEEP", "SECTION_TWIST",
    "SUPERELLIPSE_PROFILE", "LOWER_RECESS", "RIBBED_FAIRING",
)
TRAIN_LEVELS = (.08,.17,.26,.35,.44,.53,.62,.71,.80,.89)
VALID_LEVELS = (.135,.365,.595,.825)
SHIFT_LEVELS = (.21,.41,.61,.81)
PHASES = {
    "train": (tuple("advtrain%02d" % i for i in range(1,13)),TRAIN_LEVELS),
    "validation": (tuple("advval%d" % i for i in range(1,5)),VALID_LEVELS),
    "aspect_shift": (tuple("advshift%d" % i for i in range(1,5)),SHIFT_LEVELS),
}
SIGNAL_FOR = {
    "SECTION_LOFT": 0, "TANGENT_SWEEP": 1, "SECTION_TWIST": 2,
    "SUPERELLIPSE_PROFILE": 3, "LOWER_RECESS": 4, "RIBBED_FAIRING": 5,
}
FEATURES = (
    "double_shoulder_profile", "centerline_curvature",
    "cross_section_twist", "rounded_corner_fullness",
    "paired_lower_surface_recess", "midsection_rib_amplitude",
)
EXPECTED = 912
TRIANGLE_LIMIT = 3000


def features_from_glb(path: Path, stations: int, segments: int) -> tuple[list[float], dict]:
    doc, blob, _ = _read_glb(path)
    if len(doc.get("meshes",[])) != 1:
        raise ValueError("Advanced form must have one source mesh")
    prims = doc["meshes"][0].get("primitives",[])
    if len(prims) != 1:
        raise ValueError("Expected one original native indexed shell")
    prim = prims[0]
    verts = _accessor(doc, blob, prim["attributes"]["POSITION"], "positions")
    if segments != 24 or stations != 24 or len(verts) != (stations+1)*segments+2:
        raise ValueError("Missing reviewed corresponding source sections")
    rings = [verts[i*segments:(i+1)*segments] for i in range(stations+1)]
    def ring_data(row):
        # glTF: x=source X, y=source Z-up, z=-source Y (longitudinal).
        cx = (row[0][0]+row[12][0])*.5
        cy = (row[6][1]+row[18][1])*.5
        w = abs(row[0][0]-row[12][0])*.5
        h = abs(row[6][1]-row[18][1])*.5
        cz = sum(point[2] for point in row)/segments
        if min(w,h) <= .025:
            raise ValueError("Collapsed source profile")
        return cx,cy,cz,w,h
    stats=[ring_data(row) for row in rings]
    width=[p[3] for p in stats]
    cx=[p[0] for p in stats]
    length=abs(stats[-1][2]-stats[0][2])
    if length < 1 or length > 12.1:
        raise ValueError("Invalid measured axial extent")
    # All six signals are calculated from generic physical source sections.
    # No model input contains a form name, strength label or source filename.
    shoulder=(width[7]+width[18])/(2*width[0])-1.
    end_expected = min(2*width[0]*.20,length*.08)
    path_bend = abs(cx[12]-(cx[0]+cx[-1])*.5)/max(.02,end_expected)
    last=rings[-1]
    theta=math.atan2(last[0][1]-stats[-1][1],
                     last[0][0]-stats[-1][0])
    twist=abs(theta)/(math.pi*.47)
    center=rings[12]
    corner=(abs(center[3][0]-stats[12][0])/stats[12][3]*
            abs(center[3][1]-stats[12][1])/stats[12][4])-.5
    upper=abs(center[3][0]-stats[12][0])
    lower=abs(center[21][0]-stats[12][0])
    recess=1-lower/max(upper,.025)
    rib=1-width[12]/max(.025,(width[6]+width[18])*.5)
    measured=[shoulder,path_bend,twist,corner,recess,rib]
    if any(not math.isfinite(x) or abs(x)>2.5 for x in measured):
        raise ValueError("Unphysical original GLB geometry descriptor")
    # The swept-frame profile must be transverse to its physical path
    # tangent rather than merely a row of translated circles.
    a,b=stats[5],stats[7]
    dx=b[0]-a[0]
    dy=b[2]-a[2]
    local=cx[6]
    rx=rings[6][0][0]-local
    ry=rings[6][0][2]-stats[6][2]
    tangent_dot=abs(dx*rx+dy*ry)/max(1.e-7,
        math.hypot(dx,dy)*math.hypot(rx,ry))
    return measured, {
        "source_vertex_count":len(verts),
        "measured_length":length,
        "frame_tangent_abs_dot":tangent_dot,
    }


def expected_cases() -> set[str]:
    return {
        "__".join((phase,family,op.lower(),"s%03d" % round(level*1000)))
        for phase,(families,levels) in PHASES.items()
        for family in families for op in OPERATIONS for level in levels
    }


def load_case(source: Path, stem: str) -> dict:
    path=source/(stem+".glb")
    meta=json.loads((source/(stem+".json")).read_text())
    raw=path.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    parts=stem.split("__")
    if len(parts)!=4:
        raise ValueError("Malformed original advanced shape identity")
    phase,family,name,level=parts
    if phase not in PHASES:
        raise ValueError("Unknown advanced study split")
    families,levels=PHASES[phase]
    if family not in families or name.upper() not in OPERATIONS:
        raise ValueError("Unexpected family or native operation")
    expected_levels={"s%03d" % round(x*1000):x for x in levels}
    if level not in expected_levels:
        raise ValueError("Unreviewed source strength")
    if not (
        meta.get("schema")==SCHEMA and meta.get("phase")==phase
        and meta.get("family")==family and meta.get("case")==stem
        and meta.get("operation")==name.upper()
        and meta.get("native_generator")=="AssetWright-AdvancedFormLab"
        and meta.get("source_glb_sha256")==sha
        and meta.get("segments")==24 and meta.get("stations")==24
        and type(meta.get("strength")) in (float,int)
        and abs(meta["strength"]-expected_levels[level])<1e-5
        and all(type(meta.get(key)) in (int,float) and
                math.isfinite(meta[key]) and meta[key]>0 for key in
                ("length","width","height"))
    ):
        raise ValueError("Invalid original GLB provenance or partition")
    report=inspect(path)
    if not (
        report["model_sha256"]==sha and report["mesh_parts"]==1
        and 1000<=report["triangles"]<=TRIANGLE_LIMIT
        and report["boundary_edges"]==0
        and report["nonmanifold_edges"]==0
        and report["invalid_triangles"]==0
        and report["inverted_closed_parts"]==0
        and report["parts"][0]["signed_volume"]>0
    ):
        raise ValueError("Real GLB failed independent closed-shell audit")
    values,physical=features_from_glb(path,24,24)
    if name.upper()=="TANGENT_SWEEP" and physical["frame_tangent_abs_dot"]>.03:
        raise ValueError("Sweep frames are not perpendicular to actual path")
    return {"sha256":sha,"phase":phase,"family":family,
            "class":name.upper(),"strength":expected_levels[level],
            "features":values,"triangles":report["triangles"]}


def load_dataset(source:Path) -> list[dict]:
    expected=expected_cases()
    actual={path.stem for path in source.glob("*.glb")}
    manifests={path.stem for path in source.glob("*.json")}
    if actual != expected or manifests != expected or len(expected)!=EXPECTED:
        raise ValueError("Incomplete/extra native GLB source or metadata")
    rows=[load_case(source,stem) for stem in sorted(expected)]
    if len({r["sha256"] for r in rows})!=EXPECTED:
        raise ValueError("Repeated native mesh, even with different labels")
    phases=[{r["family"] for r in rows if r["phase"]==phase}
            for phase in PHASES]
    if any(set(phases[i])&set(phases[j]) for i in range(3) for j in range(i+1,3)):
        raise ValueError("Train/evaluation source family leakage")
    return rows


def train_classifier(rows:list[dict],epochs:int=350)->dict:
    """Owned from-scratch six-class multinomial logistic student."""
    if len(rows)!=720 or any(r["phase"]!="train" for r in rows):
        raise ValueError("Expect exactly 720 new native training GLBs")
    if Counter(r["class"] for r in rows)!={k:120 for k in OPERATIONS}:
        raise ValueError("Unbalanced advanced form source learning")
    mean=[sum(r["features"][i] for r in rows)/len(rows)
          for i in range(len(FEATURES))]
    std=[max(.025,math.sqrt(sum((r["features"][i]-mean[i])**2
         for r in rows)/len(rows))) for i in range(len(FEATURES))]
    xdata=[[(v-m)/s for v,m,s in zip(row["features"],mean,std)]+[1.0]
           for row in rows]
    labels=[OPERATIONS.index(row["class"]) for row in rows]
    weights=[[0.0]*7 for _ in OPERATIONS]
    for _ in range(epochs):
        gradients=[[0.0]*7 for _ in OPERATIONS]
        for x,label in zip(xdata,labels):
            logits=[sum(a*b for a,b in zip(w,x)) for w in weights]
            top=max(logits)
            e=[math.exp(z-top) for z in logits]
            norm=sum(e)
            for j in range(len(OPERATIONS)):
                err=e[j]/norm-(1. if j==label else 0.)
                for k in range(7):
                    gradients[j][k]+=err*x[k]/len(rows)
        for j in range(len(OPERATIONS)):
            for k in range(7):
                reg=.003*weights[j][k] if k<6 else 0.
                weights[j][k]-=.32*(gradients[j][k]+reg)
    return {
        "schema":MODEL,"classes":list(OPERATIONS),"features":list(FEATURES),
        "mean":mean,"std":std,"weights":weights,
        "method":"original_linear_softmax_plus_monotone_GLBr_response",
        "source_sha256":sorted(r["sha256"] for r in rows),
        "training_glbs":720,"android_deployable":False,
        "no_pretrained_geometry_generator":True
    }


def predict_class(model:dict,features:list[float])->tuple[str,float]:
    x=[(v-m)/s for v,m,s in zip(features,model["mean"],model["std"])]+[1.]
    logits=[sum(a*b for a,b in zip(weights,x)) for weights in model["weights"]]
    top=max(logits)
    probs=[math.exp(z-top) for z in logits]
    best=max(range(len(logits)),key=lambda i:logits[i])
    return OPERATIONS[best],probs[best]/sum(probs)


def train_response_curves(rows:list[dict])->dict:
    if len(rows)!=720 or any(row["phase"]!="train" for row in rows):
        raise ValueError("Original training rows only")
    curves={}
    for op in OPERATIONS:
        idx=SIGNAL_FOR[op]
        samples=[]
        for strength in TRAIN_LEVELS:
            family_samples=[r for r in rows if r["class"]==op and
                            abs(r["strength"]-strength)<1e-6]
            if len(family_samples)!=12:
                raise ValueError("Missing independent native family response")
            values=[r["features"][idx] for r in family_samples]
            samples.append([strength,sum(values)/len(values)])
        if any(b[1]-a[1]<=.00001 for a,b in zip(samples,samples[1:])):
            raise ValueError("Non-invertible or saturated native shape response: "+op)
        for family in PHASES["train"][0]:
            own=sorted(
                (r for r in rows if r["class"]==op and r["family"]==family),
                key=lambda r:r["strength"])
            if any(b["features"][idx]-a["features"][idx]<=.000005
                   for a,b in zip(own,own[1:])):
                raise ValueError("Source-family nonmonotonic response: "+op)
        curves[op]={"feature":FEATURES[idx],"signal_index":idx,
                    "measured_strength_curve":samples}
    return curves


def inverse_strength(curves:dict,op:str,features:list[float])->float:
    if op not in curves:
        raise ValueError("Unknown native advanced operation")
    curve=curves[op]
    signal=features[curve["signal_index"]]
    points=curve["measured_strength_curve"]
    if signal<=points[0][1]:return points[0][0]
    if signal>=points[-1][1]:return points[-1][0]
    for a,b in zip(points,points[1:]):
        if a[1]<=signal<=b[1]:
            fraction=(signal-a[1])/(b[1]-a[1])
            return a[0]+fraction*(b[0]-a[0])
    raise ValueError("Uninvertible native response curve")


def evaluate(model:dict,curves:dict,rows:list[dict],phase:str)->dict:
    if not rows or any(r["phase"]!=phase for r in rows):
        raise ValueError("Cannot mix geometry source partitions")
    correct=0;oracle_err=0;end_err=0;majority_err=0
    per=Counter();matrix=defaultdict(Counter)
    samples=[]
    for row in rows:
        predicted,confidence=predict_class(model,row["features"])
        expected=row["class"]
        good=predicted==expected
        per[expected]+=int(good)
        matrix[expected][predicted]+=1
        target=row["strength"]
        oracle=inverse_strength(curves,expected,row["features"])
        owned=inverse_strength(curves,predicted,row["features"])
        oracle_err+=abs(oracle-target)
        end_err+=abs(owned-target) if good else 1.0
        majority_err+=abs(.5-target)
        correct+=int(good)
        samples.append({
            "source_sha256":row["sha256"],"expected":expected,
            "predicted":predicted,"confidence":round(confidence,6),
            "target_strength":target,
            "oracle_strength":round(oracle,6),
            "predicted_strength":round(owned,6),
            "operation_correct":good
        })
    n=len(rows)
    return {"phase":phase,"examples":n,"accuracy":correct/n,
            "per_class_correct":{k:per[k] for k in OPERATIONS},
            "confusion":{k:dict(matrix[k]) for k in OPERATIONS},
            "oracle_strength_mae":oracle_err/n,
            "end_to_end_strength_mae":end_err/n,
            "constant_strength_baseline_mae":majority_err/n,
            "cases":samples}


def gates(validation:dict,shift:dict)->dict:
    return {
        "validation_operation_accuracy":validation["accuracy"]>=.90,
        "validation_all_classes":all(x>=13 for x in validation["per_class_correct"].values()),
        "shift_operation_accuracy":shift["accuracy"]>=.82,
        "shift_all_classes":all(x>=11 for x in shift["per_class_correct"].values()),
        "validation_oracle_inverse_mae":validation["oracle_strength_mae"]<=.085,
        "shift_oracle_inverse_mae":shift["oracle_strength_mae"]<=.12,
        "validation_end_to_end_inverse_mae":validation["end_to_end_strength_mae"]<=.15,
        "shift_end_to_end_inverse_mae":shift["end_to_end_strength_mae"]<=.22,
        "beats_constant_strength_by_at_least_point_one":(
            validation["constant_strength_baseline_mae"]-
            validation["oracle_strength_mae"]>=.10 and
            shift["constant_strength_baseline_mae"]-
            shift["oracle_strength_mae"]>=.08),
    }


def run(source:Path,out:Path)->dict:
    rows=load_dataset(source)
    train=[row for row in rows if row["phase"]=="train"]
    val=[row for row in rows if row["phase"]=="validation"]
    shift=[row for row in rows if row["phase"]=="aspect_shift"]
    if (len(train),len(val),len(shift))!=(720,96,96):
        raise ValueError("Wrong advanced curriculum class balance")
    model=train_classifier(train)
    curves=train_response_curves(train)
    val_score=evaluate(model,curves,val,"validation")
    shift_score=evaluate(model,curves,shift,"aspect_shift")
    checks=gates(val_score,shift_score)
    passed=all(checks.values())
    result={
        "schema":"assetwright-native-advanced-geometry-study-v1",
        "status":"verified_development_study" if passed else "rejected_development_study",
        "source":"912 original source-hashed Kotlin AdvancedFormLab GLBs",
        "train_glbs":len(train),"validation_glbs":len(val),
        "aspect_shift_glbs":len(shift),
        "source_hash_uniqueness":len({r["sha256"] for r in rows})==EXPECTED,
        "closed_meshes_audited":EXPECTED,
        "train_hashes_sha256":hashlib.sha256(
            "\n".join(model["source_sha256"]).encode()).hexdigest(),
        "validation_source_sha256":sorted(r["sha256"] for r in val),
        "shift_source_sha256":sorted(r["sha256"] for r in shift),
        "validation_metrics":{k:v for k,v in val_score.items() if k!="cases"},
        "aspect_shift_metrics":{k:v for k,v in shift_score.items() if k!="cases"},
        "checks":checks,
        "generation_authority":"AssetWright native Kotlin geometry only",
        "limits":"Same procedural source engine; dimension/aspect transfer only, not real-world asset-category transfer; no Boolean cutout or true G2 continuity.",
        "prior_native_student_unchanged":True,"android_deployed":False,
        "independent_human_visual_approval":False
    }
    model["response_curves"]=curves
    out.mkdir(parents=True,exist_ok=True)
    (out/"advanced_evaluation.json").write_text(json.dumps(result,indent=2)+"\n")
    (out/"advanced_candidate.json").write_text(json.dumps(model,indent=2)+"\n")
    (out/"heldout_predictions.json").write_text(json.dumps(
        {"validation":val_score["cases"],"aspect_shift":shift_score["cases"]},
        indent=2)+"\n")
    print(json.dumps({
        "status":result["status"],"train":len(train),"validation":len(val),
        "shift":len(shift),"validation_accuracy":val_score["accuracy"],
        "shift_accuracy":shift_score["accuracy"],
        "val_inverse_mae":val_score["oracle_strength_mae"],
        "shift_inverse_mae":shift_score["oracle_strength_mae"],
        "checks":checks
    },indent=2))
    if not passed:
        raise SystemExit("Advanced morphology candidate failed strict development gates")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.source,a.out)
