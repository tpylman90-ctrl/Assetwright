"""Measurable design proxies from real GLB vertex geometry.

This is *not* an aesthetic-vision model. Scores check a wider, less spherical
roof crown and profiled mounting fairings, problems observed in the four-view
Forge Review benchmark. They cannot establish good artistic design.
"""
from __future__ import annotations
import math
from pathlib import Path

from generated_glb_critic import _read_glb, _accessor


def _mesh_points(doc:dict,blob:bytes,name:str)->list[list[tuple]]:
    result=[]
    for mesh in doc.get("meshes",[]):
        if mesh.get("name")!=name:
            continue
        points=[]
        for primitive in mesh.get("primitives",[]):
            points.extend(_accessor(doc,blob,primitive.get("attributes",{}).get("POSITION"),"positions"))
        if points:
            result.append(points)
    return result


def _canopy_crown(points:list[tuple])->dict:
    if not points:
        return {"roof_crown_width_ratio":0., "sample_count":0}
    # Native GLB Y is up, -Z is fore/aft. Measure broadness of upper
    # cross sections near the greenhouse center, not only top height.
    length=max(p[2] for p in points)-min(p[2] for p in points)
    center=(max(p[2] for p in points)+min(p[2] for p in points))/2
    middle=[p for p in points if abs(p[2]-center)<=length*.23]
    if len(middle)<12:
        return {"roof_crown_width_ratio":0., "sample_count":len(middle)}
    low=min(p[1] for p in middle)
    high=max(p[1] for p in middle)
    height=high-low
    widest=max(abs(p[0]) for p in middle)
    if height<1e-5 or widest<1e-5:
        return {"roof_crown_width_ratio":0., "sample_count":len(middle)}
    crown=[abs(p[0]) for p in middle if p[1]>=low+.80*height]
    ratio=max(crown,default=0.)/widest
    return {"roof_crown_width_ratio":round(ratio,5),
            "sample_count":len(middle)}


def _arm_stations(parts:list[list[tuple]])->dict:
    stations=[]
    tapers=[]
    for points in parts:
        # Group real GLB vertices at longitudinal mount stations (X-axis).
        # A plain pipe has 2 stations with equal radial dimensions.
        # An authored loft has multiple sections and a broader root.
        sections={}
        for x,y,z in points:
            sections.setdefault(round(x,4),[]).append((y,z))
        keys=sorted(sections)
        stations.append(len(keys))
        if len(keys)<2:
            tapers.append(0.)
            continue
        def radius(section):
            ys=[p[0] for p in section]
            zs=[p[1] for p in section]
            return math.hypot((max(ys)-min(ys))/2,(max(zs)-min(zs))/2)
        ends=[radius(sections[keys[0]]), radius(sections[keys[-1]])]
        small=min(ends)
        tapers.append((max(ends)/small) if small>1e-6 else 0.)
    return {
        "mount_section_count_min":min(stations,default=0),
        "mount_section_count_average":round(sum(stations)/len(stations),3) if stations else 0.,
        "mount_root_tip_taper_ratio":round(min(tapers,default=0.),5),
        "mount_parts_analyzed":len(stations)
    }


def analyze(path:Path)->dict:
    doc,blob,sha=_read_glb(path)
    canopy=_mesh_points(doc,blob,"Bonded panoramic canopy")
    arms=_mesh_points(doc,blob,"Repulsor mount bracket")
    roof=_canopy_crown(canopy[0]) if len(canopy)==1 else {
        "roof_crown_width_ratio":0., "sample_count":0}
    mounts=_arm_stations(arms)
    checks={
        "non_spherical_upper_roof":roof["roof_crown_width_ratio"]>=.55,
        "profiled_mounts_not_two_station_rods":mounts["mount_section_count_min"]>=4,
        "tapered_mount_sections":mounts["mount_root_tip_taper_ratio"]>=1.25
    }
    return {
        "schema":"assetwright-vehicle-design-proxy-v1",
        "model_sha256":sha,
        "metrics":{**roof,**mounts},
        "checks":checks,
        "proxy_quality_score":round(sum(checks.values())/len(checks),3),
        "review_state":"requires_human_visual_review",
        "limitations":"Roof-crown profile, mount section count and end taper measured from actual vertices; cannot score beauty, seams, real connectivity, production topology or source similarity."
    }
