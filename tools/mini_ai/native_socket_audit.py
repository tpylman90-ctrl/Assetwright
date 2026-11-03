"""Independent actual-GLB audit of an original connected rear hull socket.

Unlike a bounding-box change this measures an interior ring in the same
closed hull mesh, with no new floating decorative part and no invalid edges.
This does not verify perfect shrouding/welding to separately modeled engines.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from generated_glb_critic import inspect, _read_glb, _accessor

SCHEMA="assetwright-native-rear-socket-audit-v1"

def near_well(points:list[tuple[float,float,float]],rear:float,center_z:float)->int:
    # glTF X,Y,Z corresponds to native x,z,-y; aft is -Z.
    return sum(.07 < p[2] - rear < .33 and
               p[0]*p[0]+(p[1]-center_z)**2 < .19*.19 for p in points)

def compare(base_audit:dict,new_audit:dict,before:list[tuple],after:list[tuple])->dict:
    def hull(audit:dict)->dict:
        matches=[p for p in audit["parts"] if p["name"]=="Sculpted continuous body"]
        if len(matches)!=1: raise ValueError("Missing unique original hull")
        return matches[0]
    old,new=hull(base_audit),hull(new_audit)
    rear=min(p[2] for p in before)
    if abs(rear-min(p[2] for p in after))>.0001:
        raise ValueError("Hull rear cap moved unexpectedly")
    # Known controlled original source roof: 1.27 m -> hull centerZ 0.80m.
    baseline=near_well(before,rear,.80)
    cavity=near_well(after,rear,.80)
    checks={
        "baseline_had_no_blind_well":baseline==0,
        "real_inward_well_vertices":cavity>=16,
        "hull_single_connected_surface":new["boundary_edges"]==0 and
            new["nonmanifold_edges"]==0,
        "hull_outward_normals":new["signed_volume"]>0,
        "no_degenerate_mesh_faces":new["invalid_triangles"]==0,
        "more_actual_hull_triangles":new["triangles"]>old["triangles"]+20,
        "same_number_of_components":base_audit["mesh_parts"]==new_audit["mesh_parts"],
        "whole_model_has_no_new_nonmanifold_edges":
            new_audit["nonmanifold_edges"]==0 and base_audit["nonmanifold_edges"]==0,
        "mobile_triangle_budget":new_audit["triangles"]<=12000
    }
    return {"schema":SCHEMA,"passed":all(checks.values()),"checks":checks,
            "baseline_hull_triangles":old["triangles"],
            "recessed_hull_triangles":new["triangles"],
            "baseline_well_vertices":baseline,"recessed_well_vertices":cavity,
            "baseline_mesh_parts":base_audit["mesh_parts"],
            "socket_mesh_parts":new_audit["mesh_parts"],
            "limitations":"Actual native hull blind recess topology, not Boolean shell/engine welding or professional visual approval."}

def points_of(glb:Path)->list[tuple]:
    doc,blob,_=_read_glb(glb)
    parts=[m for m in doc.get("meshes",[]) if m.get("name")=="Sculpted continuous body"]
    if len(parts)!=1: raise ValueError("Missing original hull mesh")
    output=[]
    for primitive in parts[0].get("primitives",[]):
        output.extend(_accessor(doc,blob,primitive["attributes"]["POSITION"],"positions"))
    return output

def run(folder:Path,out:Path)->dict:
    checks=[]
    for variant in ("baseline","socket_recess"):
        stem="native_socket__"+variant
        target=json.loads((folder/(stem+".json")).read_text())
        glb=folder/(stem+".glb")
        if (target.get("schema")!="assetwright-native-socket-target-v1" or
            target.get("case")!="native_socket" or
            target.get("variant")!=variant or
            target.get("original_procedural_asset") is not True or
            target.get("expected_engine")!="android-native-MiniGeometry" or
            target.get("drive_count")!=1 or
            target.get("rear_socket_depth")!=(0 if variant=="baseline" else 1)):
            raise ValueError("Mismatched original native socket target")
        actual=hashlib.sha256(glb.read_bytes()).hexdigest()
        if actual!=target.get("source_glb_sha256"): raise ValueError("Source GLB hash mismatch")
        checks.append((inspect(glb),points_of(glb),actual))
    result=compare(checks[0][0],checks[1][0],checks[0][1],checks[1][1])
    result["source_sha256"]={"baseline":checks[0][2],"socket_recess":checks[1][2]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]: raise SystemExit(2)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.source,a.out)
