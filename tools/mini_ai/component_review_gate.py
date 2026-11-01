"""Review queue and approval gate for mesh component-role training labels.

A geometrically grounded component label requires a human/Forge-reviewed
source-object + mesh hash + graph node, plus a documented independent evidence
artifact. Source mesh names are suggestions only, never accepted training labels.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from part_role_proposals import ALLOWED, validate_proposal

HEX64=re.compile(r"^[0-9a-f]{64}$")
SCHEMA="assetwright-reviewed-component-roles-v1"
QUEUE="assetwright-component-role-review-queue-v1"


def pending_pairs(pairs:dict)->tuple[dict,dict]:
    if pairs.get("schema")!="assetwright-grounded-text-mesh-pairs-v1":
        raise ValueError("Unknown grounded geometry pair schema")
    tasks=[]
    mesh_count=0
    for source in pairs.get("pairs",[]):
        graph=source.get("component_graph")
        if not isinstance(graph,dict):
            continue
        mesh_count+=1
        for node in graph.get("nodes",[]):
            role=node.get("weak_role_proposal")
            if not validate_proposal(role):
                continue
            tasks.append({
                "source_object_id":source["source_object_id"],
                "source_page":source["source_page"],
                "source_mesh_sha256":source["source_mesh_sha256"],
                "graph_component_id":node["id"],
                "suggested_role":role["candidate_role"],
                "suggestion_origin":"unverified source mesh object name",
                "review_state":"needs_multiview_or_author_verified_metadata",
                "caption":source["caption"][:240],
                "geometry_extent_ratios":node["extent_ratios"],
                "review_preview_artifacts":source.get("review_preview_artifacts",[])
            })
    result={"schema":QUEUE,"tasks":tasks,"provenance":"CC0 mesh descriptions and name-only suggestions"}
    return result,{"schema":"assetwright-component-role-queue-report-v1",
                   "grounded_model_graphs":mesh_count,
                   "weak_role_candidates":len(tasks),
                   "approved_semantic_labels":0,
                   "note":"No semantic labels approved from mesh names or bounding-box overlap alone"}


def approve(pairs:dict,manifest:dict)->tuple[dict,dict]:
    if pairs.get("schema")!="assetwright-grounded-text-mesh-pairs-v1":
        raise ValueError("Unknown text/mesh pairs")
    if manifest.get("schema")!=SCHEMA:
        raise ValueError("Invalid reviewed label manifest")
    by_id={p["source_object_id"]:p for p in pairs.get("pairs",[])}
    accepted=[]
    seen=set()
    rejected=[]
    for i,record in enumerate(manifest.get("reviews",[])):
        try:
            id=record["source_object_id"]
            sha=record["source_mesh_sha256"]
            component=record["graph_component_id"]
            role=record["approved_role"]
            method=record["verification_method"]
            proof=record["evidence_sha256"]
            reviewer=record["reviewer"]
            if not (isinstance(sha,str) and HEX64.fullmatch(sha) and
                    isinstance(proof,str) and HEX64.fullmatch(proof) and proof!=sha):
                raise ValueError("Missing distinct source and review-evidence hashes")
            if not (isinstance(id,str) and id in by_id and
                    by_id[id]["source_mesh_sha256"]==sha):
                raise ValueError("Source object or mesh hash mismatch")
            if type(component) is not int:
                raise ValueError("Invalid graph component ID")
            nodes=by_id[id].get("component_graph",{}).get("nodes",[])
            if not any(node.get("id")==component for node in nodes):
                raise ValueError("No matching node in the inspected mesh")
            if role not in ALLOWED:
                raise ValueError("Unsupported semantic component role")
            if method not in {"reviewed_multiview_render","author_verified_component_metadata"}:
                raise ValueError("Review method not verified")
            if not (isinstance(reviewer,str) and 4<=len(reviewer)<=100):
                raise ValueError("Reviewer name or method missing")
            key=(sha,component)
            if key in seen:
                raise ValueError("Duplicate node approval")
            seen.add(key)
            accepted.append({
                "source_object_id":id,"source_mesh_sha256":sha,
                "graph_component_id":component,"approved_role":role,
                "verification_method":method,"evidence_sha256":proof,
                "reviewer":reviewer,"status":"review_asserted_with_evidence"
            })
        except (TypeError,ValueError,KeyError) as error:
            rejected.append({"index":i,"reason":str(error)[:160]})
    # A JSON review is an assertion, not cryptographic proof of a visual
    # inspection. Its evidence hash must be auditable separately.
    return {"schema":"assetwright-reviewed-component-training-rows-v1",
            "records":accepted,"android_deployable":False}, {
        "schema":"assetwright-component-approval-report-v1",
        "approved_review_assertions":len(accepted),
        "rejected_reviews":rejected,
        "note":"Review assertions need independent evidence audit; not automatically deployed to Android"
    }


def run(source:Path,out:Path,report:Path,manifest:Path|None=None)->dict:
    pairs=json.loads(source.read_text(encoding="utf-8"))
    if manifest is None:
        data,info=pending_pairs(pairs)
    else:
        annotations=json.loads(manifest.read_text(encoding="utf-8"))
        data,info=approve(pairs,annotations)
    out.parent.mkdir(parents=True,exist_ok=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    report.write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(info,indent=2))
    return info


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pairs",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    cli.add_argument("--report",type=Path,required=True)
    cli.add_argument("--reviews",type=Path)
    args=cli.parse_args()
    run(args.pairs,args.out,args.report,args.reviews)
