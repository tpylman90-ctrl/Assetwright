"""Train AssetWright-owned operation-sequence model on official CAD splits.

This is next-operation learning, not executable arbitrary CAD generation.
Outside meshes are never imported into the native generator.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
from zero_to_cad_ingest import DATASET,SCHEMA,LICENSE,OPS

MODEL="assetwright-owned-cad-grammar-student-v1"
START="<START>"
END="<END>"
MIN_TRAIN=24
MIN_HOLDOUT=8

def read_rows(doc:dict,expected_split:str)->list[dict]:
    if doc.get("schema")!=SCHEMA or doc.get("dataset")!=DATASET or doc.get("license")!=LICENSE:
        raise ValueError("Unapproved dataset or license")
    if doc.get("split")!=expected_split or not isinstance(doc.get("records"),list):
        raise ValueError("Wrong official source split")
    seen=set();hashes=set();out=[]
    for row in doc["records"]:
        sid=row.get("source_id");fingerprint=row.get("code_sha256")
        ops=row.get("operations")
        if not isinstance(sid,str) or not isinstance(fingerprint,str) or len(fingerprint)!=64:
            raise ValueError("Missing source identity")
        if sid in seen or fingerprint in hashes: raise ValueError("Duplicated CAD source")
        if not isinstance(ops,list) or not 3<=len(ops)<=128 or any(x not in OPS for x in ops):
            raise ValueError("Malformed source operation sequence")
        if row.get("split")!=expected_split: raise ValueError("Mixed official source split")
        seen.add(sid);hashes.add(fingerprint);out.append(row)
    return out

def train_markov(rows:list[dict])->dict:
    one=Counter();two=defaultdict(Counter);three=defaultdict(Counter)
    for row in rows:
        previous=[START,START]
        for item in [*row["operations"],END]:
            one[item]+=1
            two[previous[-1]][item]+=1
            three[tuple(previous)][item]+=1
            previous=[previous[-1],item]
    return {"schema":MODEL,"vocab":sorted(set(OPS)|{END}),
            "unigram":dict(one),"bigram":{k:dict(v) for k,v in two.items()},
            "trigram":{"|".join(k):dict(v) for k,v in three.items()},
            "training_sources":len(rows),
            "generator_authority":"assetwright-native-construction-operators",
            "third_party_geometry_imported":False,"android_deployable":False}

def probability(model:dict,history:list[str],candidate:str,method:str)->float:
    vocab=model["vocab"]
    if candidate not in vocab: raise ValueError("Unknown next operation")
    base=(model["unigram"].get(candidate,0)+1)/(sum(model["unigram"].values())+len(vocab))
    if method=="unigram": return base
    previous=history[-1] if history else START
    pair=model["bigram"].get(previous,{})
    bigram=(pair.get(candidate,0)+2*base)/(sum(pair.values())+2)
    if method=="bigram": return bigram
    if method!="trigram": raise ValueError("Unsupported operation model")
    prior=history[-2] if len(history)>=2 else START
    triple=model["trigram"].get(prior+"|"+previous,{})
    return (triple.get(candidate,0)+3*bigram)/(sum(triple.values())+3)

def evaluate(model:dict,rows:list[dict],method:str)->dict:
    total=0.;n=0;correct=0
    for row in rows:
        history=[START,START]
        for answer in [*row["operations"],END]:
            probs={word:probability(model,history,word,method) for word in model["vocab"]}
            total-=math.log(max(probs[answer],1e-16))
            correct+=max(probs,key=probs.get)==answer
            n+=1
            history=[history[-1],answer]
    mean=total/n
    return {"cross_entropy":round(mean,6),"perplexity":round(math.exp(mean),6),
            "top1_accuracy":round(correct/n,6),"tokens":n}

def fit(train:dict,validation:dict)->tuple[dict,dict|None]:
    rows=read_rows(train,"train");heldout=read_rows(validation,"validation")
    summary={"schema":"assetwright-zero-to-cad-student-evaluation-v1",
             "train_sources":len(rows),"heldout_sources":len(heldout),
             "model_scope":"CAD operation prior; not production mesh generation",
             "external_ai_produces_final_models":False}
    ids={x["source_id"] for x in rows}; hashes={x["code_sha256"] for x in rows}
    if any(x["source_id"] in ids or x["code_sha256"] in hashes for x in heldout):
        raise ValueError("Train/validation source overlap")
    if len(rows)<MIN_TRAIN or len(heldout)<MIN_HOLDOUT:
        return {**summary,"status":"insufficient_official_split_examples",
                "required_train":MIN_TRAIN,"required_heldout":MIN_HOLDOUT},None
    student=train_markov(rows)
    metrics={name:evaluate(student,heldout,name)
             for name in ("unigram","bigram","trigram")}
    chosen=min(("bigram","trigram"),key=lambda x:metrics[x]["cross_entropy"])
    gain=1-metrics[chosen]["cross_entropy"]/metrics["unigram"]["cross_entropy"]
    accepted=gain>=.02
    student["selected_method"]=chosen
    student["validated_on_official_split"]=accepted
    return {**summary,
            "status":"validated_research_grammar" if accepted else "grammar_failed_holdout_gate",
            "baseline":"unigram","candidate":chosen,"heldout_metrics":metrics,
            "gain_fraction":round(gain,6),"allowed_to_modify_android_geometry":False},student

def run(train_file:Path,valid_file:Path,out:Path)->dict:
    report,model=fit(json.loads(train_file.read_text()),
                     json.loads(valid_file.read_text()))
    out.mkdir(parents=True,exist_ok=True)
    (out/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"validated_grammar.json").unlink(missing_ok=True)
    if model is not None:
        (out/"candidate_grammar.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
        if report["status"]=="validated_research_grammar":
            (out/"validated_grammar.json").write_text(json.dumps(model,separators=(",",":"))+"\n")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train",type=Path,required=True)
    p.add_argument("--validation",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(run(a.train,a.validation,a.out),indent=2))
if __name__=="__main__": main()
