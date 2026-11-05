"""AssetWright CAD school: learn from real licensed construction PROGRAMS.

This is the second, enlarged Zero-to-CAD lesson after 96/40 examples.
Inputs are safely parsed operation records and face-count metadata from a
pinned Apache-2.0 Autodesk dataset revision. Never execute source scripts or
load STEP/STL meshes as native output. Never claim program statistics prove
professional CAD geometry generation.

Two separate independently evaluated owned students:
  1) next substantive CAD-concept transitions (profile, volume, cut,
     edge/finish, pattern, transform);
  2) final B-Rep face-count complexity from operation descriptions only.
"Why?" cards distinguish educational geometric rationale from correlation.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from zero_to_cad_ingest import DATASET,LICENSE,OPS,SCHEMA
from zero_to_cad_operation_student import read_rows

MODEL="assetwright-owned-cad-shape-school-v2"
REPORT="assetwright-cad-shape-school-evaluation-v2"
GROUPS=("profile","volume","cut","finish","pattern","transform")
VOCAB=GROUPS
FAMILY = {
    "profile": {"box","rect","circle","ellipse","polygon","polyline",
                "spline","slot2D","threePointArc","tangentArcPoint"},
    "volume": {"extrude","revolve","loft","sweep"},
    "cut": {"cut","cutBlind","cutThruAll","hole","cskHole","cboreHole",
            "intersect"},
    "finish": {"fillet","chamfer","shell"},
    "pattern": {"polarArray","rarray","mirror","pushPoints"},
    "transform": {"rotate","translate"},
}
assert all(not set(FAMILY[a])&set(FAMILY[b]) for a in GROUPS for b in GROUPS if a!=b)
OP_TO_GROUP={op:name for name in GROUPS for op in FAMILY[name]}
WHY={
    "profile":"The profile defines a cross-section or sketch to be shaped, cut, or revolved.",
    "volume":"A solid-making operation adds material or carries a profile through space.",
    "cut":"A subtractive feature changes solid topology or forms a cavity; validate remaining walls.",
    "finish":"An edge/skin operation changes transitions or wall behavior; inspect radii and normals.",
    "pattern":"Repeated features preserve a relation across positions; check spacing and interference.",
    "transform":"A frame change affects feature placement; check datum and orientation."
}
NATIVE_TRANSFER={
    "profile":{"status":"partial","implemented":"NativeFormLab cross-sections; NativeInterfaceLab concentric profiles",
        "missing":"arbitrary sketch constraints, multiwire profiles and profiles with islands"},
    "volume":{"status":"partial","implemented":"AdvancedFormLab loft/sweep; NativeCompositionLab composed hull",
        "missing":"arbitrary rail/spline sweep and face-patch continuity"},
    "cut":{"status":"partial","implemented":"NativeInterfaceLab fixed through-bore; NativeBranchLab fixed blind socket",
        "missing":"general position-independent Boolean CSG and true T-branch passage"},
    "finish":{"status":"missing_general","implemented":"sampled flange ease; ring blend controls",
        "missing":"true constant-radius multi-edge fillet, chamfer solver and G2 continuity"},
    "pattern":{"status":"not_implemented","implemented":"no general native feature-array operator",
        "missing":"connected polar/linear patterned CAD features"},
    "transform":{"status":"partial","implemented":"bounded axial and 20-position native branch placement",
        "missing":"free continuous placement of arbitrary joined components"}
}

def verify_manifests(train:dict,valid:dict)->tuple[list[dict],list[dict]]:
    a=read_rows(train,"train")
    b=read_rows(valid,"validation")
    if len(a)<300 or len(b)<80:
        raise ValueError("Large CAD curriculum requires >=300 train and >=80 official validation records")
    source_revisions=(train.get("dataset_revision"),valid.get("dataset_revision"))
    if not all(isinstance(x,str) and len(x)==40 and
               all(c in "0123456789abcdef" for c in x) for x in source_revisions):
        raise ValueError("Immutable licensed dataset revision missing")
    if source_revisions[0]!=source_revisions[1]:
        raise ValueError("Train and validation used different dataset revisions")
    train_ids={x["source_id"] for x in a}
    train_hashes={x["code_sha256"] for x in a}
    if any(x["source_id"] in train_ids or x["code_sha256"] in train_hashes for x in b):
        raise ValueError("Official train/validation source hash leakage")
    return a,b

def concepts(ops:list[str])->list[str]:
    return [OP_TO_GROUP[x] for x in ops if x in OP_TO_GROUP]

def quizzes(rows:list[dict])->list[tuple[tuple[str,...],str]]:
    result=[]
    for row in rows:
        sequence=concepts(row["operations"])
        # Predict the NEXT concept from ONLY the prior observed features.
        # Ignore setup/workplane/face-selection syntax, and never expose
        # the answer token as a feature in this quiz.
        for at in range(1,len(sequence)):
            result.append((tuple(sequence[:at]),sequence[at]))
    return result

def fit_concepts(rows:list[dict])->dict:
    sample=quizzes(rows)
    if len(sample)<500:
        raise ValueError("Insufficient substantive operation transitions")
    uni=Counter()
    bi=defaultdict(Counter)
    tri=defaultdict(Counter)
    for history,label in sample:
        uni[label]+=1
        bi[history[-1]][label]+=1
        context=(history[-2] if len(history)>1 else "<START>",history[-1])
        tri["|".join(context)][label]+=1
    if len([x for x in uni if uni[x]>10])<4:
        raise ValueError("Too few independent CAD concept families represented")
    return {
        "groups":list(GROUPS),
        "unigram":dict(uni),
        "bigram":{k:dict(v) for k,v in bi.items()},
        "trigram":{k:dict(v) for k,v in tri.items()},
        "source_train_transitions":len(sample),
        "context_smoothing":{"bigram":8,"trigram":5},
    }

def probabilities(model:dict,history:tuple[str,...],kind:str)->dict[str,float]:
    counts=model["unigram"]
    n=sum(counts.values())
    base={k:(counts.get(k,0)+1)/(n+len(GROUPS)) for k in GROUPS}
    if kind=="unigram":return base
    if not history:raise ValueError("Study requires observed profile history")
    prev=model["bigram"].get(history[-1],{})
    size=sum(prev.values())
    big={k:(prev.get(k,0)+8*base[k])/(size+8) for k in GROUPS}
    if kind=="bigram":return big
    if kind!="trigram":raise ValueError("Unsupported owned CAD grammar")
    key=(history[-2] if len(history)>1 else "<START>")+"|"+history[-1]
    triple=model["trigram"].get(key,{})
    size=sum(triple.values())
    return {k:(triple.get(k,0)+5*big[k])/(size+5) for k in GROUPS}

def evaluate_concepts(model:dict,rows:list[dict],kind:str)->dict:
    samples=quizzes(rows)
    if len(samples)<100:
        raise ValueError("Insufficient held-out CAD transitions")
    nll=0.;top1=0
    group_hits=Counter();group_totals=Counter()
    for history,answer in samples:
        scores=probabilities(model,history,kind)
        nll-=math.log(max(scores[answer],1e-15))
        right=max(scores,key=scores.get)==answer
        top1+=right
        group_hits[answer]+=int(right)
        group_totals[answer]+=1
    return {
        "transitions":len(samples),"cross_entropy":nll/len(samples),
        "perplexity":math.exp(nll/len(samples)),
        "top1_accuracy":top1/len(samples),
        "per_target_accuracy":{g:(group_hits[g]/group_totals[g] if group_totals[g] else None)
                               for g in GROUPS},
        "heldout_group_counts":{g:group_totals[g] for g in GROUPS}
    }

def complexity_features(row:dict)->list[float]:
    """NUM_FACE target never appears in X. Only CAD source operation names."""
    ops=row["operations"]
    counts=Counter(ops)
    groups=Counter(concepts(ops))
    total=max(1,len(ops))
    return [
        math.log1p(total),
        math.log1p(len(counts)),
        *[math.log1p(groups[g]) for g in GROUPS],
        *[math.log1p(counts[op]) for op in
          ("extrude","loft","sweep","revolve","cut","cutBlind","hole",
           "fillet","chamfer","shell","union","mirror","polarArray","rarray")],
        *[groups[g]/total for g in GROUPS]
    ]

def face_rows(rows:list[dict])->list[dict]:
    return [r for r in rows if isinstance(r.get("num_faces"),int)
            and not isinstance(r["num_faces"],bool) and 1<=r["num_faces"]<=100000]

def fit_faces(rows:list[dict])->dict:
    """Trained self-owned regularized linear face-complexity response."""
    import numpy as np
    selected=face_rows(rows)
    if len(selected)<200:
        raise ValueError("Too few original source face-count labels")
    matrix=np.asarray([complexity_features(r) for r in selected],dtype=np.float64)
    labels=np.log1p(np.asarray([r["num_faces"] for r in selected],dtype=np.float64))
    mean=matrix.mean(axis=0)
    std=np.maximum(matrix.std(axis=0),.05)
    X=np.column_stack((np.ones(len(matrix)),(matrix-mean)/std))
    ridge=np.diag([0.]+[3.]*(X.shape[1]-1))
    weights=np.linalg.solve(X.T@X+ridge,X.T@labels)
    median_face=float(np.median(labels))
    # Stronger baseline predicts via observed operation count ONLY, fitted
    # on training rows. Compare this against the full semantic features.
    length=np.asarray([math.log1p(len(r["operations"])) for r in selected])
    B=np.column_stack((np.ones(len(length)),length))
    baseline_weights=np.linalg.solve(
        B.T@B+np.diag([0.,1.]),B.T@labels)
    return {
        "train_labels":len(selected),
        "mean":mean.tolist(),"std":std.tolist(),
        "coefficients":weights.tolist(),
        "median_log_faces":median_face,
        "length_only_weights":baseline_weights.tolist(),
        "ridge_regularization":3.,
        "target":"log1p(original BRep num_faces); no STEP/STL input"
    }

def evaluate_faces(model:dict,rows:list[dict])->dict:
    import numpy as np
    selected=face_rows(rows)
    if len(selected)<70:
        raise ValueError("Too few independent held-out BRep face-count targets")
    X=np.asarray([complexity_features(r) for r in selected])
    y=np.log1p(np.asarray([r["num_faces"] for r in selected],dtype=np.float64))
    z=(X-np.asarray(model["mean"]))/np.asarray(model["std"])
    A=np.column_stack((np.ones(len(z)),z))
    pred=A@np.asarray(model["coefficients"])
    lengths=np.log1p(np.asarray([len(r["operations"]) for r in selected]))
    size=np.column_stack((np.ones(len(lengths)),lengths))
    prior=size@np.asarray(model["length_only_weights"])
    constant=np.full(len(selected),model["median_log_faces"])
    # Three actual held-out baselines, not made-up CAD geometry measurements.
    return {
        "heldout_labeled_sources":len(selected),
        "semantic_log_face_mae":float(np.mean(np.abs(pred-y))),
        "sequence_length_only_log_face_mae":float(np.mean(np.abs(prior-y))),
        "train_median_constant_log_face_mae":float(np.mean(np.abs(constant-y))),
        "semantic_log_face_rmse":float(np.sqrt(np.mean((pred-y)**2))),
        "heldout_actual_num_faces_p50":float(np.median(np.expm1(y))),
    }

def cards(model:dict,train_rows:list[dict])->list[dict]:
    entries=[]
    unique=Counter(op for row in train_rows for op in row["operations"])
    for prior in GROUPS:
        if sum(model["bigram"].get(prior,{}).values())<15: continue
        post=probabilities(model,(prior,),"bigram")
        ordered=sorted(GROUPS,key=lambda x:post[x],reverse=True)
        for choice in ordered[:2]:
            support=model["bigram"].get(prior,{}).get(choice,0)
            if support<8:continue
            base=probabilities(model,(prior,),"unigram")[choice]
            entries.append({
                "lesson_type":"observed_construction_transition",
                "observed_previous_concept":prior,
                "likely_next_concept":choice,
                "observed_transition_count":support,
                "learned_conditional_probability":round(post[choice],5),
                "unconditional_probability":round(base,5),
                "relative_to_base":round(post[choice]/base,3),
                "geometry_rationale_educational_not_causal":WHY[choice],
                "native_transfer":NATIVE_TRANSFER[choice],
                "source":"licensed Zero-to-CAD 100K training split only"
            })
    return sorted(entries,key=lambda r:(-r["observed_transition_count"],
               -r["relative_to_base"]))[:12]

def run(train_manifest:Path,val_manifest:Path,out:Path)->dict:
    train_doc=json.loads(train_manifest.read_text())
    valid_doc=json.loads(val_manifest.read_text())
    train,valid=verify_manifests(train_doc,valid_doc)
    learner=fit_concepts(train)
    baseline=evaluate_concepts(learner,valid,"unigram")
    candidate=evaluate_concepts(learner,valid,"trigram")
    sizes=fit_faces(train)
    face_result=evaluate_faces(sizes,valid)
    xentropy_gain=1-candidate["cross_entropy"]/baseline["cross_entropy"]
    accuracy_gain=candidate["top1_accuracy"]-baseline["top1_accuracy"]
    face_gain=1-face_result["semantic_log_face_mae"]/face_result[
        "train_median_constant_log_face_mae"]
    # Fixed gates, chosen before reading official larger validation.
    checks={
        "official_source_disjoint":True,
        "train_at_least_1000":len(train)>=1000,
        "validation_at_least_250":len(valid)>=250,
        "concept_crossentropy_improvement":xentropy_gain>=.075,
        "concept_top1_absolute_gain":accuracy_gain>=.035,
        "face_prediction_better_than_constant":face_gain>=.05,
        "face_model_beats_length_only":face_result["semantic_log_face_mae"] <=
            face_result["sequence_length_only_log_face_mae"]*.985
    }
    ok=all(checks.values())
    model={
        "schema":MODEL,"source":"ADSKAILab/Zero-To-CAD-100k",
        "license":"Apache-2.0",
        "dataset_revision":train_doc["dataset_revision"],
        "training_code_hash_digest":hashlib.sha256("\n".join(
            sorted(r["code_sha256"] for r in train)).encode()).hexdigest(),
        "training_sources":len(train),
        "concept_student":learner,"face_complexity_student":sizes,
        "transfer_registry":NATIVE_TRANSFER,
        "third_party_scripts_executed":False,
        "external_meshes_used_for_final_geometry":False,
        "native_generator_authority":"AssetWright Kotlin only",
        "production_deployable":False
    }
    report={
        "schema":REPORT,
        "status":"passed_research_only" if ok else "rejected_research_candidate",
        "official_licensed_dataset":"ADSKAILab/Zero-To-CAD-100k",
        "dataset_revision":train_doc["dataset_revision"],
        "train_sources":len(train),"official_validation_sources":len(valid),
        "learned_transition_samples":learner["source_train_transitions"],
        "train_unique_op_names":len(set(op for row in train for op in row["operations"])),
        "train_group_counts":dict(Counter(g for row in train for g in concepts(row["operations"]))),
        "concept_majority_baseline":baseline,
        "concept_contextual_student":candidate,
        "concept_cross_entropy_relative_gain":xentropy_gain,
        "concept_top1_absolute_gain":accuracy_gain,
        "face_complexity":face_result,
        "face_constant_baseline_relative_gain":face_gain,
        "learning_checks":checks,
        "separately_verified_native_GLBS_in_this_study":0,
        "geometry_generated_by_licensed_source":False,
        "new_cad_script_executions":0,
        "human_visual_approval":False,
        "android_deployed":False,
        "limitations":"Learns CAD operation relationships and BRep face-count proxy from licensed synthetic programs, not actual surface geometry, CAD program execution, independent semantic design, accurate fillets, or arbitrary 3D assets."
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"candidate_shape_school.json").write_text(json.dumps(model,indent=2)+"\n")
    (out/"cad_concept_lessons.json").write_text(json.dumps({
        "schema":"assetwright-cad-observed-transition-lessons-v1",
        "source_revision":train_doc["dataset_revision"],
        "examples_are_observational_not_causes":True,
        "native_skill_coverage":NATIVE_TRANSFER,
        "lessons":cards(learner,train)
    },indent=2)+"\n")
    print(json.dumps({
        "status":report["status"],"train":len(train),"valid":len(valid),
        "xentropy_gain":xentropy_gain,"accuracy_gain":accuracy_gain,
        "face_mae":face_result["semantic_log_face_mae"],
        "face_baseline":face_result["train_median_constant_log_face_mae"],
        "checks":checks
    },indent=2))
    if not ok:
        raise SystemExit("Large CAD shape school rejected without weakening thresholds")
    return report

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--train",type=Path,required=True)
    cli.add_argument("--validation",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    a=cli.parse_args()
    run(a.train,a.validation,a.out)
