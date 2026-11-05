"""Measure safe numeric AST source coverage on TRAIN-ONLY licensed CAD code.

Never scores a held-out geometric target and never executes source Python.
This is a parser readiness test, NOT evidence of learned 3D modeling.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from zero_to_cad_ingest import DATASET,LICENSE,dataset_iterator,parse_row
from cad_surface_profile_features import Collector
from safe_cad_numeric_resolver import collect_static_cad_numbers

PROFILES={"box","rect","circle","ellipse","polygon","slot2D"}

def has_real_numeric_profile(calls):
    for op,args in calls:
        if op in PROFILES and len(args)>=(1 if op=="circle" else 2):
            if all(abs(float(x))>1e-5 for x in args[:1 if op=="circle" else 2]):
                return True
    return False

def run(revision:str,offset:int,count:int,scan:int,out:Path)->dict:
    if not re.fullmatch("[a-f0-9]{40}",revision):
        raise ValueError("Source revision must be immutable")
    if not (3000<=offset<=6000 and 100<=count<=500 and
            count<=scan<=1000 and offset+scan<=8000):
        raise ValueError("Unapproved source-only training cohort")
    ids=set();hashes=set()
    before=0;after=0;assignments=0;collected=0;scanned=0
    for index,raw in enumerate(dataset_iterator("train",revision)):
        if index<offset:continue
        if scanned>=scan or collected>=count:break
        scanned+=1
        row,reason=parse_row(raw,"train")
        if row is None:continue
        source=raw.get("cadquery_file")
        if isinstance(source,bytes):source=source.decode("utf-8",errors="replace")
        if not isinstance(source,str) or len(source)>200_000:continue
        if row["source_id"] in ids or row["code_sha256"] in hashes:continue
        ids.add(row["source_id"]);hashes.add(row["code_sha256"])
        try:
            syntax=ast.parse(source)
        except (SyntaxError,ValueError,RecursionError):
            continue
        direct=Collector();direct.visit(syntax)
        enhanced,info=collect_static_cad_numbers(source)
        before+=int(has_real_numeric_profile(direct.ops if hasattr(direct,"ops") else direct.records))
        after+=int(has_real_numeric_profile(enhanced))
        assignments+=int(info.get("safe_resolved_assignments",0)>0)
        collected+=1
    report={
        "schema":"assetwright-cad-static-parameter-coverage-v1",
        "source":"ADSKAILab/Zero-To-CAD-100k",
        "license":LICENSE,"revision":revision,"split":"train",
        "train_offset":offset,"source_records":collected,
        "old_direct_literal_profile_count":before,
        "new_safe_numeric_assignment_profile_count":after,
        "programs_with_safe_numeric_assignments":assignments,
        "old_profile_coverage":before/max(1,collected),
        "new_profile_coverage":after/max(1,collected),
        "improvement_percentage_points":100*(after-before)/max(1,collected),
        "source_programs_executed":False,
        "reference_STL_or_STEP_used":False,
        "external_generated_geometry":False,
        "source_hash_manifest_sha256":hashlib.sha256(
            "\n".join(sorted(hashes)).encode()).hexdigest(),
        "teacher_only":True,
        "limitations":"Only static scalar assignments and direct numeric arguments; no executed control flow, symbolic variables, true CAD topology or mesh reconstruction."
    }
    # Fixed minimal improvement test; reject if unsafe analysis does not
    # actually recover additional CAD geometry information.
    report["passed_coverage_gate"]=collected==count and after>=before+max(8,count//20)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not report["passed_coverage_gate"]:
        raise SystemExit("Bounded static parameter resolver has not proved useful coverage")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--revision",required=True)
    p.add_argument("--offset",type=int,required=True)
    p.add_argument("--count",type=int,required=True)
    p.add_argument("--scan-limit",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.revision,a.offset,a.count,a.scan_limit,a.out)

if __name__=="__main__":main()
