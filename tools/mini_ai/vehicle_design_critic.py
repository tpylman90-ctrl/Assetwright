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


def _cockpit_shoulder_span(points:list[tuple])->dict:
    """Outer upper-hull breadth near cockpit, not just overall vehicle width."""
    if not points:
        return {"body_cockpit_shoulder_span":0., "body_cockpit_samples":0}
    minz,maxz=min(p[2] for p in points),max(p[2] for p in points)
    miny,maxy=min(p[1] for p in points),max(p[1] for p in points)
    length=maxz-minz
    height=maxy-miny
    if length<=1e-5 or height<=1e-5:
        return {"body_cockpit_shoulder_span":0., "body_cockpit_samples":0}
    center=(minz+maxz)/2
    # Restrict to the upper hull, in the cockpit's longitudinal region.
    # A structural shift in the original hull must broaden THIS portion.
    upper=[abs(p[0]) for p in points
           if abs(p[2]-center)<=length*.19 and
              miny+height*.58<=p[1]<=miny+height*.89]
    return {
        "body_cockpit_shoulder_span":round(max(upper,default=0.),5),
        "body_cockpit_samples":len(upper)
    }


def _rear_nacelle_profile(parts:list[list[tuple]])->dict:
    """Real endpoint/ring radial flare in glTF Z-axis (vehicle longitudinal)."""
    ratios=[]
    counts=[]
    for points in parts:
        by_z={}
        for x,y,z in points:
            by_z.setdefault(round(z,4),[]).append((x,y))
        sections=[by_z[k] for k in sorted(by_z)]
        counts.append(len(sections))
        if len(sections)<2:
            ratios.append(0.)
            continue
        radii=[]
        for ring in sections:
            if len(ring)<4:
                continue
            xvals=[p[0] for p in ring]
            yvals=[p[1] for p in ring]
            radius=math.hypot(
                (max(xvals)-min(xvals))/2,
                (max(yvals)-min(yvals))/2
            )
            radii.append(radius)
        ratios.append(max(radii)/min(radii) if radii and min(radii)>1e-6 else 0.)
    return {
        "engine_housing_flare_ratio":round(min(ratios,default=0.),5),
        "engine_housing_axial_sections":min(counts,default=0),
        "engine_housings_examined":len(parts)
    }


def analyze(path:Path)->dict:
    doc,blob,sha=_read_glb(path)
    canopy=_mesh_points(doc,blob,"Bonded panoramic canopy")
    arms=_mesh_points(doc,blob,"Repulsor mount bracket")
    roof=_canopy_crown(canopy[0]) if len(canopy)==1 else {
        "roof_crown_width_ratio":0., "sample_count":0}
    mounts=_arm_stations(arms)
    hulls=_mesh_points(doc,blob,"Sculpted continuous body")
    shoulder=_cockpit_shoulder_span(hulls[0]) if len(hulls)==1 else {
        "body_cockpit_shoulder_span":0.,"body_cockpit_samples":0}
    nacelles=(_mesh_points(doc,blob,"Rear drive housing")+
              _mesh_points(doc,blob,"Central booster housing"))
    engine_profile=_rear_nacelle_profile(nacelles)
    checks={
        "non_spherical_upper_roof":roof["roof_crown_width_ratio"]>=.55,
        "profiled_mounts_not_two_station_rods":mounts["mount_section_count_min"]>=4,
        "tapered_mount_sections":mounts["mount_root_tip_taper_ratio"]>=1.25,
        # Broadness alone does not prove an elegant cockpit transition or
        # physically unioned nacelle. These are narrow operation effects.
        "cockpit_hull_shoulder_envelope":shoulder["body_cockpit_samples"]>=4,
        "profiled_engine_root":engine_profile["engine_housings_examined"]>=1
            and engine_profile["engine_housing_axial_sections"]>=5
            and engine_profile["engine_housing_flare_ratio"]>=1.25
    }
    return {
        "schema":"assetwright-vehicle-design-proxy-v1",
        "model_sha256":sha,
        "metrics":{**roof,**mounts,**shoulder,**engine_profile},
        "checks":checks,
        "proxy_quality_score":round(sum(checks.values())/len(checks),3),
        "review_state":"requires_human_visual_review",
        "limitations":"Actual vertex measurements of roof crown, upper hull shoulder breadth, mount taper and nacelle flare. No visual beauty, exact seam welding, physical collision-free assembly or copyright originality is proved."
    }
