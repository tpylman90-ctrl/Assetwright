"""Own text-to-native-geometry student trained with optional FROZEN vision features.

DINOv2 encodes original AssetWright renders for auxiliary training supervision.
At inference this learner only accepts text and predicts six editable native
parameters. It never imports or generates third-party GLB geometry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re

MANIFEST="assetwright-original-visual-pairs-v1"
EMBEDDINGS="assetwright-frozen-dinov2-features-v1"
MODEL="assetwright-owned-text-construction-student-v1"
PARAMS={"length":(3.4,7.0),"width":(1.45,3.2),"roof_height":(1.05,2.3),
        "canopy_length":(.85,3.1),"nose_taper":(.25,.9),"rear_haunch":(.9,1.3)}
BUCKETS=256
HIDDEN=24
TEACHER=24
MIN_SOURCES=24
SYNONYMS={"elongated":"long","stretched":"long","shorter":"short","broad":"wide",
          "wider":"wide","slim":"narrow","greenhouse":"canopy",
          "windshield":"canopy","sporty":"racer","racing":"racer",
          "haunches":"haunch","fenders":"haunch","hoover":"hover"}

def text_features(prompt:str)->list[int]:
    tokens={SYNONYMS.get(t,t) for t in re.findall(r"[a-z]+",prompt.lower())}
    tokens={t for t in tokens if len(t)>2}
    return sorted({int.from_bytes(hashlib.blake2s(t.encode(),digest_size=4).digest(),"big")%BUCKETS for t in tokens})

def valid_sha(value:object)->bool:
    return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value) is not None

def normalize_parameters(values:dict)->list[float]:
    if not isinstance(values,dict): raise ValueError("Missing source-native recipe")
    output=[]
    for key,(low,high) in PARAMS.items():
        value=values.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError("Invalid native parameter: "+key)
        output.append((float(value)-low)/(high-low))
    return output

def project_teacher(vector:list[float])->list[float]:
    """Fixed label-free 384->24 projection; it never constructs meshes."""
    if not isinstance(vector,list) or len(vector)!=384 or any(
        type(v) not in (int,float) or not math.isfinite(v) for v in vector
    ): raise ValueError("Expected finite DINOv2-small [CLS] vector of size 384")
    length=math.sqrt(sum(v*v for v in vector))
    if length<1e-9: raise ValueError("Zero teacher features")
    result=[0.0]*TEACHER
    for i,value in enumerate(vector):
        bucket=i%TEACHER
        sign=1 if hashlib.sha256(f"assetwright-v1:{i}".encode()).digest()[0]&1 else -1
        result[bucket]+=sign*value/length
    return [math.tanh(2.0*v) for v in result]

def parse_rows(manifest:dict,embeddings:dict)->list[dict]:
    if manifest.get("schema")!=MANIFEST or embeddings.get("schema")!=EMBEDDINGS:
        raise ValueError("Unexpected training or teacher schema")
    if embeddings.get("model_id")!="facebook/dinov2-small":
        raise ValueError("Only frozen DINOv2-small teacher permitted")
    features={}
    for record in embeddings.get("features",[]):
        name=record.get("sample_id")
        if not isinstance(name,str) or name in features:
            raise ValueError("Invalid or repeated visual feature entry")
        if not valid_sha(record.get("source_glb_sha256")):
            raise ValueError("Missing image/mesh provenance")
        features[name]=record
    rows=[]; source_hashes=set(); ids=set()
    for item in manifest.get("examples",[]):
        ident=item.get("sample_id"); sha=item.get("source_glb_sha256")
        group=item.get("source_group")
        if not isinstance(ident,str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}",ident) or ident in ids:
            raise ValueError("Duplicate or invalid sample ID")
        if not valid_sha(sha) or sha in source_hashes:
            raise ValueError("Duplicate or invalid source mesh")
        if item.get("original_procedural_asset") is not True or item.get("expected_engine")!="android-native-MiniGeometry":
            raise ValueError("Refusing external/generated-teacher geometry as construction truth")
        if not isinstance(group,str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}",group):
            raise ValueError("Missing held-out design family")
        prompt=item.get("prompt")
        if not isinstance(prompt,str) or len(prompt.strip())<20:
            raise ValueError("Missing original recipe description")
        expected=item.get("view_sha256")
        if not isinstance(expected,dict) or set(expected)!={"front","side","top","three_quarter"} or not all(valid_sha(v) for v in expected.values()):
            raise ValueError("Missing hash-grounded multi-view evidence")
        record=features.get(ident)
        if not record or record.get("source_glb_sha256")!=sha or record.get("view_sha256")!=expected:
            raise ValueError("Frozen feature source does not match its rendered mesh")
        rows.append({"id":ident,"source_group":group,"sha":sha,
                     "x":text_features(prompt),"y":normalize_parameters(item.get("parameters")),
                     "z":project_teacher(record.get("embedding"))})
        ids.add(ident); source_hashes.add(sha)
    return rows

def sigmoid(x:float)->float:
    return 1.0/(1.0+math.exp(-max(-25.,min(25.,x))))

def initialize(seed:int=191)->dict:
    rng=random.Random(seed)
    return {"w1":[[rng.uniform(-.045,.045) for _ in range(BUCKETS)] for _ in range(HIDDEN)],
            "b1":[0.]*HIDDEN,
            "wg":[[rng.uniform(-.045,.045) for _ in range(HIDDEN)] for _ in PARAMS],
            "bg":[0.]*len(PARAMS),
            "wv":[[rng.uniform(-.045,.045) for _ in range(HIDDEN)] for _ in range(TEACHER)],
            "bv":[0.]*TEACHER}

def forward(model:dict,features:list[int])->tuple[list[float],list[float],list[float]]:
    scale=1/math.sqrt(max(1,len(features)))
    hidden=[math.tanh(b+sum(w[i] for i in features)*scale)
            for w,b in zip(model["w1"],model["b1"])]
    geometry=[sigmoid(b+sum(w*h for w,h in zip(row,hidden)))
              for row,b in zip(model["wg"],model["bg"])]
    teacher=[math.tanh(b+sum(w*h for w,h in zip(row,hidden)))
             for row,b in zip(model["wv"],model["bv"])]
    return hidden,geometry,teacher

def train(rows:list[dict],*,distill:bool,epochs:int=160)->dict:
    model=initialize(); rng=random.Random(2031); samples=rows[:]
    for epoch in range(epochs):
        rng.shuffle(samples); lr=.15/(1+.016*epoch)
        for sample in samples:
            x,target,target_z=sample["x"],sample["y"],sample["z"]
            hidden,geometry,visual=forward(model,x)
            dg=[2*(p-y)*p*(1-p)/len(PARAMS) for p,y in zip(geometry,target)]
            dv=([.30*2*(p-z)*(1-p*p)/TEACHER for p,z in zip(visual,target_z)]
                 if distill else [0.]*TEACHER)
            dh=[((sum(dg[o]*model["wg"][o][h] for o in range(len(PARAMS)))+
                  sum(dv[o]*model["wv"][o][h] for o in range(TEACHER)))*
                 (1-hidden[h]*hidden[h])) for h in range(HIDDEN)]
            for o in range(len(PARAMS)):
                model["bg"][o]-=lr*dg[o]
                for h in range(HIDDEN):
                    model["wg"][o][h]-=lr*(dg[o]*hidden[h]+.0001*model["wg"][o][h])
            if distill:
                for o in range(TEACHER):
                    model["bv"][o]-=lr*dv[o]
                    for h in range(HIDDEN):
                        model["wv"][o][h]-=lr*(dv[o]*hidden[h]+.0001*model["wv"][o][h])
            scale=1/math.sqrt(max(1,len(x)))
            for h in range(HIDDEN):
                model["b1"][h]-=lr*dh[h]
                for j in x:
                    model["w1"][h][j]-=lr*(dh[h]*scale+.0001*model["w1"][h][j])
    return model

def mean_errors(rows:list[dict],model:dict|None,mean:list[float]|None=None)->list[float]:
    total=[0.]*len(PARAMS)
    for row in rows:
        estimate=forward(model,row["x"])[1] if model else mean
        for i,target in enumerate(row["y"]):
            total[i]+=(estimate[i]-target)**2
    return [v/len(rows) for v in total]

def fit(manifest:dict,embeddings:dict)->tuple[dict,dict|None]:
    rows=parse_rows(manifest,embeddings)
    groups=sorted({r["source_group"] for r in rows})
    summary={"schema":"assetwright-visual-transfer-evaluation-v1",
             "source":"original android-native MiniGeometry GLBs with exact source recipes",
             "teacher":"frozen facebook/dinov2-small visual features; no teacher meshes",
             "original_meshes":len(rows),"independent_design_groups":len(groups),
             "android_deployable":False,"automatic_geometry_mutation":False}
    if len(groups)<MIN_SOURCES:
        return {**summary,"status":"insufficient_independent_designs",
                "required_design_groups":MIN_SOURCES},None
    test_groups={g for g in groups if int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5==0}
    train_rows=[r for r in rows if r["source_group"] not in test_groups]
    holdout=[r for r in rows if r["source_group"] in test_groups]
    if len({r["source_group"] for r in train_rows})<16 or len(test_groups)<4:
        return {**summary,"status":"insufficient_disjoint_holdout",
                "training_groups":len(groups)-len(test_groups),
                "holdout_groups":len(test_groups)},None
    naive=[sum(r["y"][i] for r in train_rows)/len(train_rows) for i in range(len(PARAMS))]
    baseline=train(train_rows,distill=False)
    student=train(train_rows,distill=True)
    naive_errors=mean_errors(holdout,None,naive)
    base_errors=mean_errors(holdout,baseline)
    learned_errors=mean_errors(holdout,student)
    naive_mse=sum(naive_errors)/len(PARAMS)
    base_mse=sum(base_errors)/len(PARAMS)
    distilled_mse=sum(learned_errors)/len(PARAMS)
    passed=(distilled_mse<.97*base_mse and distilled_mse<.97*naive_mse and
            all(n<=b*1.12+.0002 for n,b in zip(learned_errors,base_errors)))
    evaluation={**summary,
                "status":"validated_research_student" if passed else "transfer_failed_to_beat_text_baseline",
                "train_groups":len(groups)-len(test_groups),
                "holdout_groups":len(test_groups),"train_examples":len(train_rows),
                "holdout_examples":len(holdout),
                "constant_mean_mse":round(naive_mse,8),
                "text_only_mse":round(base_mse,8),
                "text_plus_frozen_vision_mse":round(distilled_mse,8),
                "per_dimension_text_only_mse":dict(zip(PARAMS,[round(v,8) for v in base_errors])),
                "per_dimension_distilled_mse":dict(zip(PARAMS,[round(v,8) for v in learned_errors])),
                "improvement_vs_text_only":round((base_mse-distilled_mse)/base_mse,6) if base_mse else 0,
                "external_model_generates_meshes":False,
                "student_runtime_requires_teacher":False,
                "note":"Research-only parameter learner; not a 3D mesh generator or approved visual artist."}
    package={"schema":MODEL,"generator_authority":"android-native-MiniGeometry",
             "inference_input":"text_only",
             "training_teacher":"frozen_dinov2_small_embeddings",
             "parameter_order":list(PARAMS),"parameter_bounds":list(PARAMS.values()),
             "weight_buckets":BUCKETS,"hidden_units":HIDDEN,"weights":student,
             "android_deployable":False,"source_groups":len(groups),
             "approved_for_training":False,"validated_on_heldout":passed}
    return evaluation,package

def predict(package:dict,prompt:str)->dict:
    if package.get("schema")!=MODEL or package.get("generator_authority")!="android-native-MiniGeometry":
        raise ValueError("Incompatible AssetWright student model")
    if not prompt.strip() or len(prompt)>2000:
        raise ValueError("Invalid vehicle prompt")
    _,estimates,_=forward(package["weights"],text_features(prompt))
    return {"schema":"assetwright-native-recipe-proposal-v1",
            "generator":"android-native-MiniGeometry","uses_external_mesh":False,
            "research_only":True,"prompt":prompt,
            "parameters":{key:round(low+v*(high-low),6)
                          for (key,(low,high)),v in zip(PARAMS.items(),estimates)}}

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--features",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    report,student=fit(json.loads(args.manifest.read_text()),
                       json.loads(args.features.read_text()))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (args.out/"validated_research_student.json").unlink(missing_ok=True)
    if student is not None:
        (args.out/"candidate_student.json").write_text(json.dumps(student,separators=(",",":"))+"\n")
        if report["status"]=="validated_research_student":
            (args.out/"validated_research_student.json").write_text(json.dumps(student,separators=(",",":"))+"\n")
    print(json.dumps({k:v for k,v in report.items() if not k.startswith("per_dimension")},indent=2))

if __name__=="__main__":
    main()
