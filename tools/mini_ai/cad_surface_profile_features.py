"""Safely recover dimensionless CAD sketch/feature relationships as data.

Never execute downloaded CadQuery. Literal arguments are physically
suggestive, not a full symbolic CAD interpreter. Unknown variables,
expressions and project-specific helper functions remain unavailable.
"""
from __future__ import annotations

import ast
import math
from deep_dino_curriculum import _literal_numbers
from zero_to_cad_ingest import canonical
from safe_cad_numeric_resolver import collect_static_cad_numbers

SCHEMA="assetwright-safe-cad-relative-profile-features-v1"
NAMES=(
    "base_min_over_major","base_middle_over_major",
    "sketch_second_over_first","sketch_has_three_dimensions",
    "extrude_over_base","cut_depth_over_base",
    "fillet_radius_over_base","chamfer_over_base",
    "shell_wall_over_base","hole_diameter_over_base",
    "pattern_pitch_over_base","pattern_count_scaled",
    "primary_scale_log","primary_sketch_numeric_coverage",
    "volume_numeric_coverage","cut_numeric_coverage",
    "finish_numeric_coverage","layout_numeric_coverage",
    "primary_profile_is_round","primary_profile_is_boxlike",
    "number_of_primary_profiles_scaled","extrusion_sign",
    "cut_depth_sign","angle_rotation_scaled",
    "sketch_largest_over_extrude","sketch_smallest_over_extrude",
)
SIZE=len(NAMES)

class Collector(ast.NodeVisitor):
    def __init__(self):
        self.records=[]
    def visit_Call(self,node:ast.Call):
        # Inner method before its outer chained caller, preserving native
        # sketch->extrude order for Workplane().rect().extrude() examples.
        self.generic_visit(node)
        if not isinstance(node.func,ast.Attribute):
            return
        op=canonical(node.func.attr)
        if op is None or len(self.records)>=128:
            return
        args=[]
        for raw in node.args[:8]:
            args.extend(_literal_numbers(raw))
        for raw in node.keywords[:8]:
            args.extend(_literal_numbers(raw.value))
        self.records.append((op,[v for v in args[:12]
                                if math.isfinite(v) and abs(v)<=1e8]))

def bounded_abs(value:float)->float:
    return min(4.,max(0.,abs(value)))

def scaled(x:float,denominator:float)->float:
    return min(4.,abs(x)/max(1e-4,denominator))

def signed(value:float)->float:
    return 0. if value==0 else (1. if value>0 else -1.)

def extract(source:object)->list[float]:
    if isinstance(source,bytes):
        source=source.decode("utf-8",errors="replace")
    if not isinstance(source,str) or not 0<len(source)<=200_000:
        return [0.]*SIZE
    # Only pure finite arithmetic over simple scalar assignments is
    # statically resolved. No downloaded Python statements are executed.
    calls,_=collect_static_cad_numbers(source)
    if not calls:
        # Unparseable or unsupported input has NO demonstrated CAD profile.
        # Do not fabricate a normalized square/cube as a learning signal.
        return [0.]*SIZE
    base=None
    profiles=[]
    for op,args in calls:
        if op not in ("box","rect","circle","ellipse","polygon","slot2D"):
            continue
        numeric=[abs(v) for v in args if abs(v)>1e-5]
        if op=="circle" and numeric:
            dims=[2*numeric[0],2*numeric[0]]
        elif op in ("box","rect","ellipse","slot2D") and len(numeric)>=2:
            dims=numeric[:3 if op=="box" else 2]
        elif op=="polygon" and len(numeric)>=2:
            # polygon(n_sides, circumscribed_diameter); never use n_sides
            # as a physical box axis.
            dims=[numeric[1],numeric[1]]
        else:
            dims=[]
        if dims:
            profiles.append((op,dims,len(numeric)))
            if base is None:
                base=(op,dims,len(numeric))
    if base is None:
        base=("unknown",[1.,1.],0)
    op,dims,coverage=base
    sorted_dims=sorted(dims)
    reference=max(sorted_dims[-1],1e-5)
    sketch_ratio=(
        dims[1]/dims[0] if len(dims)>=2 and dims[0]>1e-5 else 1.
    )
    def first(names:set[str]):
        for name,values in calls:
            if name in names and values:
                return values[0]
        return 0.
    extrude=first({"extrude"})
    cut=first({"cutBlind","cutThruAll","hole","cskHole","cboreHole"})
    fillet=first({"fillet"})
    chamfer=first({"chamfer"})
    shell=first({"shell"})
    hole=first({"hole","cboreHole","cskHole"})
    pitch=first({"rarray","polarArray"})
    pattern_count=0.
    for name,values in calls:
        if name in ("rarray","polarArray") and len(values)>=2:
            pattern_count=max(pattern_count,min(1.,max(abs(v) for v in values[-2:])/48.))
    rotation=first({"rotate"})
    if len(sorted_dims)==2:
        minor=sorted_dims[0]
        middle=sorted_dims[0]
    else:
        minor,middle=sorted_dims[:2]
    count=lambda names:sum(len(values) for name,values in calls if name in names)
    profile_ops={"box","rect","circle","ellipse","polygon","slot2D",
                 "lineTo","hLine","vLine","spline"}
    volume_ops={"extrude","loft","sweep","revolve"}
    cut_ops={"cut","cutBlind","cutThruAll","hole","cskHole","cboreHole"}
    finish_ops={"fillet","chamfer","shell"}
    layout_ops={"translate","rotate","rarray","polarArray","pushPoints"}
    result=[
        min(1.,minor/reference),
        min(1.,middle/reference),
        min(4.,max(0.,sketch_ratio)),
        float(len(dims)>=3),
        scaled(extrude,reference),
        scaled(cut,reference),
        scaled(fillet,reference),
        scaled(chamfer,reference),
        scaled(shell,reference),
        scaled(hole*2,reference),
        scaled(pitch,reference),
        pattern_count,
        min(1.,math.log1p(reference)/10.),
        min(1.,coverage/8),
        min(1.,count(volume_ops)/24),
        min(1.,count(cut_ops)/24),
        min(1.,count(finish_ops)/24),
        min(1.,count(layout_ops)/24),
        float(op in ("circle","ellipse")),
        float(op in ("box","rect","slot2D")),
        min(1.,len(profiles)/12),
        signed(extrude),
        signed(cut),
        min(1.,abs(rotation)/360.),
        scaled(reference,extrude) if abs(extrude)>1e-5 else 0.,
        scaled(minor,extrude) if abs(extrude)>1e-5 else 0.
    ]
    if len(result)!=SIZE or any(not math.isfinite(v) or not -1<=v<=4 for v in result):
        raise ValueError("Unsafe or mismatched original CAD feature extraction")
    return [round(float(v),8) for v in result]
