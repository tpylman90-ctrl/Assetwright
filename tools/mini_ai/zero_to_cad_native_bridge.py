"""Research-only bridge from verified learned CAD signals to a typed native operation.

The CAD dataset teaches operation sequencing and DINOv2 teaches visual
signatures. The *controlled, safe* operation map is authored and reviewed,
not an imaginary learned arbitrary text-to-geometry policy. AssetWright's
Kotlin NativeCadOperationBridge and MiniGeometry build all final triangles.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from zero_to_cad_operation_student import MODEL as GRAMMAR,probability
from zero_to_cad_visual_student import MODEL as VISUAL,input_features,predict

SCHEMA="assetwright-owned-native-operator-proposal-v1"
REQUEST="assetwright-reviewed-native-operation-request-v1"
# Only the actual, implemented native operation, not arbitrary CadQuery code.
SUPPORTED={"circle+cutBlind":"recess_rear_socket"}

def propose(grammar:dict,visual:dict)->dict:
    if (grammar.get("schema")!=GRAMMAR or
        grammar.get("validated_on_official_split") is not True or
        grammar.get("third_party_geometry_imported") is not False or
        grammar.get("generator_authority")!="assetwright-native-construction-operators"):
        raise ValueError("CAD grammar not independently validated")
    if (visual.get("schema")!=VISUAL or
        visual.get("validated_on_official_split") is not True or
        visual.get("approved_for_geometry_generation") is not False or
        visual.get("inference_needs_teacher") is not False):
        raise ValueError("Frozen-feature distillation not independently validated")
    if not {"circle","cutBlind"}.issubset(set(grammar.get("vocab",[]))):
        raise ValueError("No source evidence for circular blind-cut curriculum")
    method=grammar.get("selected_method")
    if method not in ("bigram","trigram"):
        raise ValueError("Unrecognized research grammar")
    # Learned conditional prior supplies a measurable sequencing signal.
    conditional=probability(grammar,["workplane","circle"],"cutBlind",method)
    unconditional=probability(grammar,[],"cutBlind","unigram")
    if any(not math.isfinite(v) or v<=0 for v in (conditional,unconditional)):
        raise ValueError("Invalid learned CAD operation prior")
    sequence=["workplane","circle","extrude","cutBlind"]
    signature=predict(visual["weights"],visual["bias"],input_features(sequence,None))
    if len(signature)!=24 or any(not math.isfinite(v) for v in signature):
        raise ValueError("Invalid native student's distilled visual signature")
    return {"schema":SCHEMA,"status":"review_only_native_operator_candidate",
            "source_cad_concept":"circular blind cut",
            "source_ops":sequence,
            "learnt_conditional_cutblind_probability":round(conditional,7),
            "unconditional_cutblind_probability":round(unconditional,7),
            "distilled_visual_signature": [round(x,7) for x in signature],
            "visual_signature_source":"AssetWright owned student, teacher absent at inference",
            "mapping_evidence":"Explicitly engineered equivalent rear socket primitive, not arbitrary CadQuery interpreter",
            "native_operation":SUPPORTED["circle+cutBlind"],
            "native_parameters":{"depth":1.0,"drive_count":1},
            "external_mesh_used":False,
            "automatically_deployable":False,
            "note":"The prior/visual student supply research evidence; a bounded reviewed native operation makes geometry. No automated text-to-mesh learning is claimed."}

def run(grammar_file:Path,visual_file:Path,out:Path)->dict:
    proposal=propose(json.loads(grammar_file.read_text()),
                     json.loads(visual_file.read_text()))
    out.mkdir(parents=True,exist_ok=True)
    (out/"proposal.json").write_text(json.dumps(proposal,indent=2)+"\n")
    (out/"operation.properties").write_text(
        "schema="+REQUEST+"\n"+
        "operation="+proposal["native_operation"]+"\n"+
        "depth=1.0\n"+
        "external_mesh_used=false\n")
    print(json.dumps({k:v for k,v in proposal.items() if k!="distilled_visual_signature"},indent=2))
    return proposal

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--grammar",type=Path,required=True)
    p.add_argument("--visual",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.grammar,a.visual,a.out)
