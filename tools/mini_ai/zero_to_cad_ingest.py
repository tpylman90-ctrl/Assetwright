"""Safely extract bounded construction lessons from Autodesk Zero-to-CAD 100K.

Never execute downloaded CadQuery scripts, use downloaded STL/STEP to produce
AssetWright assets, or put unreviewed code into the native modeling engine.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

DATASET="ADSKAILab/Zero-To-CAD-100k"
SCHEMA="assetwright-zero-to-cad-operations-v1"
LICENSE="Apache-2.0"
OPS=frozenset({
    "box","rect","circle","ellipse","polygon","polyline","spline","slot2D",
    "extrude","cutBlind","cutThruAll","revolve","loft","sweep","fillet",
    "chamfer","shell","offset2D","union","cut","intersect","hole","cskHole",
    "cboreHole","mirror","translate","rotate","polarArray","rarray",
    "pushPoints","workplane","faces","edges","vertices","lineTo",
    "threePointArc","tangentArcPoint","close","moveTo","center","hLine","vLine"})
CANON={name.lower():name for name in sorted(OPS)}
CANON.update({"rectangle":"rect","extrusion":"extrude","filleting":"fillet",
              "chamfering":"chamfer","boolean_union":"union","boolean_cut":"cut",
              "subtract":"cut","intersection":"intersect","revolution":"revolve"})
MAX_SOURCE=200000
MAX_OPS=128
MAX_TEXT=160000

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def canonical(name:object)->str|None:
    if not isinstance(name,str) or len(name)>100: return None
    value=name.strip()
    if value.startswith("cq."): value=value[3:]
    if "." in value: value=value.rsplit(".",1)[-1]
    if "(" in value: value=value.split("(",1)[0]
    return CANON.get(value.strip().lower())

def structured_ops(value:object)->list[str]:
    if isinstance(value,bytes): value=value.decode("utf-8",errors="replace")
    if isinstance(value,str):
        if len(value)>MAX_TEXT: return []
        try: value=json.loads(value)
        except (ValueError,TypeError): return []
    if isinstance(value,dict):
        value=next((value[k] for k in ("operations","ops","sequence")
                    if isinstance(value.get(k),list)),[])
    if not isinstance(value,list) or len(value)>MAX_OPS: return []
    result=[]
    for item in value:
        if isinstance(item,dict):
            item=next((item[k] for k in ("operation","op","method","name","type")
                       if isinstance(item.get(k),str)),None)
        op=canonical(item)
        if op: result.append(op)
    return result

class _Collector(ast.NodeVisitor):
    def __init__(self): self.ops=[]
    def visit_Call(self,node:ast.Call)->None:
        self.generic_visit(node)
        if isinstance(node.func,ast.Attribute):
            op=canonical(node.func.attr)
            if op: self.ops.append(op)

def source_ops(source:object)->tuple[list[str],str]:
    if isinstance(source,bytes):
        raw=source; source=source.decode("utf-8",errors="replace")
    elif isinstance(source,str):
        raw=source.encode("utf-8")
    else: return [],""
    if not 0<len(raw)<=MAX_SOURCE: return [],""
    fingerprint=sha(raw)
    try: tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError): return [],fingerprint
    visitor=_Collector()
    visitor.visit(tree)  # Deliberately never executes imported CadQuery programs.
    return visitor.ops[:MAX_OPS],fingerprint

def parse_row(raw:dict,split:str)->tuple[dict|None,str]:
    if split not in ("train","validation","test"):
        raise ValueError("Unknown official dataset split")
    if not isinstance(raw,dict): return None,"bad_record"
    methods,fingerprint=source_ops(raw.get("cadquery_file"))
    if not fingerprint: return None,"missing_source"
    operations=structured_ops(raw.get("cadquery_ops_json"))
    origin="structured_cadquery_ops_json" if len(operations)>=2 else "safe_ast_method_calls"
    if len(operations)<2: operations=methods
    if len(operations)<3: return None,"insufficient_supported_operations"
    uid=raw.get("uuid")
    if not isinstance(uid,str) or not re.fullmatch(r"[a-zA-Z0-9_-]{6,100}",uid):
        return None,"invalid_uuid"
    faces=raw.get("num_faces")
    if not isinstance(faces,int) or isinstance(faces,bool) or not 0<faces<100000:
        faces=None
    return {"source_id":uid,"code_sha256":fingerprint,"split":split,
            "operations":operations[:MAX_OPS],"operations_source":origin,
            "num_faces":faces},"accepted"

def dataset_iterator(split:str):
    from datasets import load_dataset
    return iter(load_dataset(DATASET,split=split,streaming=True))

def capture_images(raw:dict,item:dict,image_root:Path)->None:
    for key in ("image_0","image_4"):
        image=raw.get(key)
        if image is None: continue
        destination=image_root/(item["source_id"]+"__"+key+".png")
        if isinstance(image,dict) and "bytes" in image:
            from io import BytesIO
            from PIL import Image
            image=Image.open(BytesIO(image["bytes"]))
        if hasattr(image,"convert"):
            image.convert("RGB").save(destination,format="PNG")
            item.setdefault("view_sha256",{})[key]=sha(destination.read_bytes())
            item.setdefault("view_files",{})[key]=destination.name

def collect(split:str,*,max_records:int,max_scan:int,image_root:Path|None=None)->dict:
    if not 1<=max_records<=400 or not max_records<=max_scan<=1600:
        raise ValueError("Unbounded streaming request")
    if image_root is not None: image_root.mkdir(parents=True,exist_ok=True)
    rows=[];ids=set();hashes=set();rejected=Counter();scanned=0
    for record in dataset_iterator(split):
        if scanned>=max_scan or len(rows)>=max_records: break
        if scanned==0:
            print("ZERO_TO_CAD_COLUMN_TYPES",json.dumps({
                k:{"type":type(v).__name__,
                   "keys":list(v.keys())[:12] if isinstance(v,dict) else None,
                   "items":len(v) if isinstance(v,(list,tuple)) else None}
                for k,v in record.items() if k.startswith("image_")
            },sort_keys=True))
        scanned+=1
        parsed,reason=parse_row(record,split)
        if parsed is None:
            rejected[reason]+=1;continue
        if parsed["source_id"] in ids or parsed["code_sha256"] in hashes:
            rejected["duplicate_source"]+=1;continue
        if image_root is not None: capture_images(record,parsed,image_root)
        ids.add(parsed["source_id"]);hashes.add(parsed["code_sha256"])
        rows.append(parsed)
    return {"schema":SCHEMA,"dataset":DATASET,"license":LICENSE,
            "split":split,"records":rows,"scanned":scanned,"accepted":len(rows),
            "rejections":dict(rejected),"raw_python_executed":False,
            "external_meshes_exported":False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split",choices=("train","validation","test"),required=True)
    parser.add_argument("--max-records",type=int,default=96)
    parser.add_argument("--max-scan",type=int,default=384)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--images",type=Path)
    args=parser.parse_args()
    result=collect(args.split,max_records=args.max_records,max_scan=args.max_scan,
                   image_root=args.images)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="records"},indent=2))
    if len(result["records"])<max(8,args.max_records//3):
        raise SystemExit("Insufficient audited source examples")

if __name__=="__main__": main()
