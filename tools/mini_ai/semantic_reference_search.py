"""Local BM25 retriever over CC0 publisher captions and catalog descriptions.

Text retrieval finds relevant examples; it does not establish that any model
contains particular components, learned joints, or new construction methods.
"""
from __future__ import annotations
from collections import Counter
import json
import math
from pathlib import Path
import re

STOP={"with","this","that","from","have","over","your","each","into","they",
      "their","there","which","made","model","models","free","high",
      "asset","assets","very","object","objects","view","download","poly",
      "haven","the","and","for","are","has","its","was","can","you"}
SYNONYMS={"hoover":"hover","wheels":"wheel","tires":"tire","tyres":"tire",
          "automobile":"car","vehicles":"vehicle","motors":"motor",
          "engines":"engine","cabin":"cockpit","greenhouse":"canopy",
          "thrusters":"thruster","boosters":"booster","mechanisms":"mechanical",
          "exterior":"body","sci":"scifi","fi":"scifi"}


def words(text:str)->list[str]:
    return [
        SYNONYMS.get(w,w) for w in re.findall("[a-z0-9]+",text.lower())
        if len(w)>2 and w not in STOP
    ]


def record_text(row:dict)->str:
    return " ".join([
        row.get("name",""),row.get("name",""),
        row.get("publisher_description",""),row.get("caption_text",""),
        row.get("category","")," ".join(row.get("tags",[]) or []),
        " ".join(" ".join(str(v) for v in (value if isinstance(value,list) else [value]))
                 for value in (row.get("facets") or {}).values())
    ])


def index(records:list[dict])->dict:
    n=len(records)
    if n<1:
        raise ValueError("No catalog records")
    df=Counter()
    docs=[]
    for row in records:
        tokens=words(record_text(row))
        counts=Counter(tokens)
        docs.append((row,counts,len(tokens)))
        df.update(counts.keys())
    average=sum(length for _,_,length in docs)/n
    return {"documents":docs,"document_frequency":df,"avg_length":max(1.0,average)}


def search(idx:dict,query:str,top:int=5)->list[dict]:
    q=set(words(query))
    if not q or not 1<=top<=20:
        return []
    docs=idx["documents"]
    df=idx["document_frequency"]
    n=len(docs)
    avg=idx["avg_length"]
    results=[]
    for row,tf,length in docs:
        score=0.
        for term in q:
            count=tf.get(term,0)
            if not count:
                continue
            idf=math.log(1+(n-df[term]+.5)/(df[term]+.5))
            denom=count+1.2*(.25+.75*length/avg)
            score+=idf*(count*2.2)/denom
        if score>0:
            results.append({
                "id":row["id"],"name":row["name"],
                "category":row["category"],"source_page":row["source_page"],
                "description":(row.get("publisher_description") or row.get("caption_text",""))[:360],
                "description_origin":row.get("caption_origin") if row.get("caption_text") else row.get("description_origin","publisher_metadata"),
                "geometry_verified":bool(row.get("verified_blender_geometry")),
                "score":round(score,5)})
    results.sort(key=lambda r:(-r["score"],r["id"]))
    return results[:top]


def demo(source:Path,out:Path,queries:list[str])->dict:
    corpus=json.loads(source.read_text(encoding="utf-8"))
    if corpus.get("schema")!="assetwright-description-geometry-catalog-v1":
        raise ValueError("Wrong caption corpus")
    i=index(corpus["records"])
    data={"schema":"assetwright-reference-retrieval-demo-v1",
          "source":corpus.get("source","CC0 catalog"),
          "total_indexed":len(corpus["records"]),
          "disclaimer":"Textual relevance only, not verified matching mesh components",
          "queries":[{"prompt":query,"matches":search(i,query)}
                     for query in queries]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return data


if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--catalog",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    args=cli.parse_args()
    data=demo(args.catalog,args.out,[
        "mechanical car engine motor vehicle",
        "smooth sports car wheel and tire",
        "industrial turbine engine housing",
        "curved metal body panels machinery"
    ])
    print(json.dumps({"total_indexed":data["total_indexed"],
        "top_matches":[{"query":item["prompt"],
                        "top_model":item["matches"][0]["name"] if item["matches"] else None}
                       for item in data["queries"]]},indent=2))
