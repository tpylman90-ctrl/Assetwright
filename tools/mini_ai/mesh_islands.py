"""Discover disconnected vertex islands inside one Blender mesh object.

Topology-only segmentation does NOT establish semantic parts. It provides
candidate spatial subcomponents for independent geometry relationship study.
"""
from __future__ import annotations
import math

MAX_VERTICES = 250_000
MAX_TRIANGLES = 500_000
MAX_RETURNED = 48


def connected_bounds(points: list, edges, triangles,
                     *, minimum_triangles: int = 12) -> list[dict]:
    n = len(points)
    if n < 3 or n > MAX_VERTICES:
        return []
    parent = list(range(n))
    rank = [0] * n
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def join(a,b):
        a,b=root(a),root(b)
        if a==b:
            return
        if rank[a]<rank[b]:
            a,b=b,a
        parent[b]=a
        if rank[a]==rank[b]:
            rank[a]+=1
    for a,b in edges:
        if not 0<=a<n or not 0<=b<n:
            raise ValueError("Invalid mesh edge indices")
        join(a,b)
    bounds={}
    for i,p in enumerate(points):
        xyz=tuple(float(x) for x in p)
        if len(xyz)!=3 or any(not math.isfinite(x) for x in xyz):
            raise ValueError("Invalid vertex coordinate")
        group=root(i)
        if group not in bounds:
            bounds[group]={"min":list(xyz),"max":list(xyz),"triangles":0}
        else:
            item=bounds[group]
            for axis in range(3):
                item["min"][axis]=min(item["min"][axis],xyz[axis])
                item["max"][axis]=max(item["max"][axis],xyz[axis])
    face_count=0
    for a,b,c in triangles:
        face_count+=1
        if face_count>MAX_TRIANGLES:
            return []
        if not (0<=a<n and 0<=b<n and 0<=c<n):
            raise ValueError("Invalid mesh triangle")
        # Malformed disconnected face vertices should not produce a fake joint.
        ga,gb,gc=root(a),root(b),root(c)
        if ga==gb==gc:
            bounds[ga]["triangles"]+=1
    significant=[b for b in bounds.values() if b["triangles"]>=minimum_triangles]
    significant.sort(key=lambda b:(-b["triangles"],-max(
        y-x for x,y in zip(b["min"],b["max"]))))
    return significant[:MAX_RETURNED]
