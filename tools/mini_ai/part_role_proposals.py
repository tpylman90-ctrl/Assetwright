"""Weak geometry component-role suggestions from imported Blender mesh names.

The source author may have named a mesh 'Wheel.001', but that is NOT an
independently verified semantic label. Never train Android from these
unreviewed proposals or infer attachments from AABB overlap.
"""
from __future__ import annotations
import re

SCHEMA = "assetwright-weak-part-name-proposal-v1"
ROLES = {
    "canopy": {"canopy", "windscreen", "windshield", "greenhouse"},
    "glass": {"glass", "window", "windows", "glazing"},
    "wheel": {"wheel", "wheels", "rim", "rims"},
    "tire": {"tire", "tires", "tyre", "tyres"},
    "engine": {"engine", "motor", "turbine", "thruster", "booster"},
    "body": {"body", "chassis", "frame", "fuselage", "hull"},
    "panel": {"panel", "fender", "fenders", "fairing", "bonnet", "hood"},
    "mount": {"mount", "mounting", "bracket", "strut", "support"},
    "axle": {"axle", "shaft", "pivot"},
    "intake": {"intake", "duct", "vent", "nozzle"},
}
GENERIC = {"mesh", "object", "cube", "sphere", "cylinder", "torus",
           "plane", "collection", "default", "piece", "part", "model"}
ALLOWED=set(ROLES)


def propose(name:str)->dict|None:
    if not isinstance(name,str) or len(name)>150:
        return None
    tokens=set(re.findall(r"[a-z]+",name.casefold()))
    if not tokens or tokens <= GENERIC:
        return None
    candidates={role for role,keywords in ROLES.items() if tokens&keywords}
    if len(candidates)!=1:
        return None
    role=next(iter(candidates))
    return {
        "schema":SCHEMA,
        "candidate_role":role,
        "evidence":"source_mesh_object_name",
        "status":"requires_visual_verification"
    }


def validate_proposal(entry:object)->bool:
    return isinstance(entry,dict) and entry.get("schema")==SCHEMA and \
        entry.get("candidate_role") in ALLOWED and \
        entry.get("status")=="requires_visual_verification" and \
        entry.get("evidence")=="source_mesh_object_name"
