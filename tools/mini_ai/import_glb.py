#!/usr/bin/env python3
"""Inspect and register an explicitly approved GLB for later Mini AI training.

No network access or third-party packages. This tool does not copy meshes,
invent semantic labels, alter training weights, or claim inferred topology.
Use only files whose licenses explicitly permit the intended use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from datetime import datetime, timezone


def inspect_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("Not a binary glTF file (.glb).")
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2 or length != len(data):
        raise ValueError("Invalid glTF 2.0 header or file length.")
    offset = 12
    payload = None
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated chunk header.")
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if offset + chunk_length > len(data) or chunk_length % 4:
            raise ValueError("Truncated or misaligned glTF chunk.")
        if chunk_type == 0x4E4F534A:
            if payload is not None:
                raise ValueError("Multiple JSON chunks found.")
            payload = json.loads(data[offset:offset + chunk_length].decode("utf-8"))
        offset += chunk_length
    if payload is None or payload.get("asset", {}).get("version") != "2.0":
        raise ValueError("Missing glTF 2.0 JSON asset.")
    accessors = payload.get("accessors", [])
    total_triangles = 0
    primitive_count = 0
    unknown_primitives = 0
    for mesh in payload.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            primitive_count += 1
            if primitive.get("mode", 4) != 4:
                unknown_primitives += 1
                continue
            index = primitive.get("indices")
            if index is None:
                index = primitive.get("attributes", {}).get("POSITION")
            if not isinstance(index, int) or index < 0 or index >= len(accessors):
                unknown_primitives += 1
                continue
            total_triangles += accessors[index].get("count", 0) // 3

    return {
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "file_bytes": len(data),
        "mesh_count": len(payload.get("meshes", [])),
        "node_count": len(payload.get("nodes", [])),
        "material_count": len(payload.get("materials", [])),
        "triangle_count": total_triangles,
        "primitive_count": primitive_count,
        "unmeasured_primitive_count": unknown_primitives,
        "mesh_names": [m.get("name", "unnamed") for m in payload.get("meshes", [])][:100]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--source-url", required=True, help="Page documenting the original asset and its license.")
    parser.add_argument("--license", required=True, choices=["CC0-1.0"],
                        help="Only clearly CC0 training examples are accepted in v0.1.")
    parser.add_argument("--label", required=True, help="Human-verified asset family, e.g. 'vehicle'.")
    parser.add_argument("--description", required=True, help="Human-authored description of this asset.")
    parser.add_argument("--approved", action="store_true",
                        help="Confirm you verified the license and permission to use this asset.")
    parser.add_argument("--output", type=Path, default=Path("local-data/mini-ai/candidates.jsonl"))
    args = parser.parse_args()
    if not args.approved:
        parser.error("Supply --approved only after checking the asset's license and training permission.")
    if not args.source_url.startswith(("https://", "http://")):
        parser.error("Provide the actual original source URL.")
    if not args.glb.is_file():
        parser.error("Input GLB file does not exist.")
    metadata = inspect_glb(args.glb)
    record = {
        "schema": "assetwright-training-candidate-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": args.source_url,
        "license": args.license,
        "manual_approval": True,
        "asset_family": args.label,
        "description": args.description,
        "input_filename": args.glb.name,
        **metadata,
        "status": "candidate_not_trained",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
