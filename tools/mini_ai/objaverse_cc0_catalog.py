#!/usr/bin/env python3
"""License-filtered Objaverse object captions for research; no mesh downloads.

Objaverse's metadata has a dataset-level ODC-By license and individual
asset licenses. ONLY exactly verifiable CC0 objects enter this collection.
Generated Cap3D captions are optional and remain separately ODC-By attributed;
never relabel these texts as CC0 or infer physical part connections.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import gzip
import io
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

SHARD_BASE="https://huggingface.co/datasets/allenai/objaverse/resolve/main/metadata/"
CAP3D_URL=("https://huggingface.co/datasets/tiange/Cap3D/resolve/"
           "56571450ddbe0a06beedc41c4260be5acf06374a/"
           "Cap3D_automated_Objaverse.csv")
META_LIMIT=12*1024*1024
RAW_LIMIT=100*1024*1024
CAP_LIMIT=90*1024*1024
UID=re.compile(r"^[a-f0-9]{32}$")
SCHEMA="assetwright-objaverse-verified-cc0-captions-v1"
LICENSES={"cc0","cc0 1.0","cc0-1.0","creativecommons zero 1.0"}
AGENT="Assetwright-ForgeCC0Study/0.1 (https://github.com/tpylman90-ctrl/Assetwright)"


def text(v,limit=1000):
    return re.sub(r"\s+"," ",v.strip())[:limit] if isinstance(v,str) else ""


def tags(raw):
    if not isinstance(raw,list):
        return []
    return [s for s in (text(r.get("name","") if isinstance(r,dict) else r,65)
                         for r in raw[:40]) if s][:25]


def source_row(uid:str,data:dict) -> dict | None:
    if not UID.fullmatch(uid) or not isinstance(data,dict):
        return None
    license_code=text(data.get("license")).lower()
    if license_code not in LICENSES:
        return None
    title=text(data.get("name"),160)
    description=text(data.get("description"),1100)
    tag_values=tags(data.get("tags",[]))
    if not (title or description or tag_values):
        return None
    uri=data.get("uri")
    if not isinstance(uri,str) or not uri.startswith("https://"):
        uri=""
    return {
        "uid":uid,"name":title,"publisher_description":description,
        "tags":tag_values,
        "object_license":"CC0-1.0","license_observation":license_code,
        "metadata_license":"ODC-BY-1.0",
        "metadata_source":"https://huggingface.co/datasets/allenai/objaverse",
        "original_asset_page":uri[:350],
        "caption_quality":"publisher_description" if description else "metadata_only",
        "model_geometry_inspected":False,
    }


def fetch(url:str,cap:int)->bytes:
    allowed_hosts={"huggingface.co"}
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in allowed_hosts:
        raise ValueError("Unexpected metadata source URL")
    req=urllib.request.Request(url,headers={"User-Agent":AGENT})
    with urllib.request.urlopen(req,timeout=35) as response:
        data=response.read(cap+1)
    if len(data)>cap:
        raise ValueError("Source metadata or caption payload exceeds cap")
    return data


def read_shard(data:bytes)->dict:
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
        decompressed=gz.read(RAW_LIMIT+1)
    if len(decompressed)>RAW_LIMIT:
        raise ValueError("Metadata shard is unexpectedly large")
    raw=json.loads(decompressed)
    if not isinstance(raw,dict):
        raise ValueError("Malformed Objaverse metadata shard")
    return raw


def get_records(start:int,count:int,fetcher=fetch)->tuple[list[dict],dict]:
    if not (0<=start<160 and 1<=count<=160 and start+count<=160):
        raise ValueError("Expected 1..160 existing metadata shards")
    rows={}
    stats=Counter()
    for k in range(start,start+count):
        shard=f"000-{k:03d}"
        url=SHARD_BASE+shard+".json.gz"
        metadata=read_shard(fetcher(url,META_LIMIT))
        stats["annotations_read"]+=len(metadata)
        for uid,annotation in metadata.items():
            row=source_row(uid,annotation)
            if row:
                rows[uid]=row
        stats["shards_downloaded"]+=1
        # Be courteous to the dataset host; avoid bursts and scraping.
        if k<start+count-1:
            time.sleep(.2)
    stats["verified_cc0_records"]=len(rows)
    return list(rows.values()),dict(stats)


def add_cap3d(rows:list[dict],csv_bytes:bytes)->dict:
    uid_to_row={r["uid"]:r for r in rows}
    added=0
    # Data owner: ODC-By; descriptions are machine-generated and can be wrong.
    for values in csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))):
        if len(values)<2:
            continue
        uid=values[0].strip().lower()
        if uid not in uid_to_row:
            continue
        caption=text(values[1],1100)
        if len(caption)<20:
            continue
        uid_to_row[uid]["cap3d_generated_caption"]=caption
        uid_to_row[uid]["cap3d_caption_license"]="ODC-BY-1.0"
        uid_to_row[uid]["cap3d_source"]="https://huggingface.co/datasets/tiange/Cap3D"
        uid_to_row[uid]["cap3d_caption_quality"]="unverified_model_generated_caption"
        added+=1
    return {"cc0_rows_matched_with_cap3d":added}


def run(out:Path,report_out:Path,start:int,count:int,with_cap3d:bool)->dict:
    rows,stats=get_records(start,count)
    if with_cap3d and rows:
        # Download only the smaller immutable historical caption CSV.
        stats.update(add_cap3d(rows,fetch(CAP3D_URL,CAP_LIMIT)))
    corpus={"schema":SCHEMA,"shards":[start,start+count],
            "dataset_license":"ODC-BY-1.0",
            "license_note":"Only individually verified CC0 model rights; metadata and Cap3D captions require ODC-By attribution",
            "credits":["Objaverse / Allen Institute for AI", "Cap3D / University of Michigan" if with_cap3d else ""],
            "records":sorted(rows,key=lambda r:r["uid"])}
    out.parent.mkdir(parents=True,exist_ok=True)
    report_out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(corpus,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    report_out.write_text(json.dumps({"schema":"assetwright-objaverse-cc0-catalog-report-v1",**stats,
       "source":"Objaverse 1.0",
       "dataset_license":"ODC-BY-1.0",
       "objects_license":"individually verified CC0 only",
       "note":"Publisher metadata plus unverified automated caption text; no models or learned weights downloaded"},
       indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats,indent=2))
    return stats


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out",type=Path,required=True)
    cli.add_argument("--report",type=Path,required=True)
    cli.add_argument("--shard-start",type=int,default=0)
    cli.add_argument("--shards",type=int,default=8)
    cli.add_argument("--cap3d",action="store_true")
    args=cli.parse_args()
    run(args.out,args.report,args.shard_start,args.shards,args.cap3d)
