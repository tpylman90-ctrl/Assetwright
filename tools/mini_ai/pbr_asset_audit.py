"""Audit high-fidelity PBR glTF 2.0 assets without using them as training data.

Standard-library only; no external mesh or texture assets are stored by this
tool. Geometry checks are technical indicators, NOT scores for visual quality.
Example: python tools/mini_ai/pbr_asset_audit.py input.glb --output report.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct


class GlbFormatError(ValueError):
    pass


def _parse(path: Path):
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("rb") as fh:
        head = fh.read(12)
        if len(head) != 12:
            raise GlbFormatError("Truncated GLB header")
        magic, version, size = struct.unpack("<4sII", head)
        if magic != b"glTF" or version != 2:
            raise GlbFormatError("Expected binary glTF 2.0")
        if size != path.stat().st_size:
            raise GlbFormatError("GLB byte length mismatch")
        chunks = []
        while fh.tell() < size:
            header = fh.read(8)
            if len(header) != 8:
                raise GlbFormatError("Truncated GLB chunk header")
            length, typ = struct.unpack("<I4s", header)
            if length > size - fh.tell():
                raise GlbFormatError("Chunk exceeds file bounds")
            chunks.append((typ, fh.read(length)))
    if not chunks or chunks[0][0] != b"JSON":
        raise GlbFormatError("Missing glTF JSON chunk")
    try:
        doc = json.loads(chunks[0][1].decode("utf-8").strip(" \x00"))
    except (ValueError, UnicodeError) as exc:
        raise GlbFormatError("Invalid glTF JSON") from exc
    return doc, next((data for kind, data in chunks if kind == b"BIN\x00"), b"")


def inspect(path: str | Path) -> dict:
    """Read a physically exported GLB; do not assign any aesthetic score."""
    path = Path(path)
    doc, binary = _parse(path)
    accessors = doc.get("accessors", [])
    buffer_views = doc.get("bufferViews", [])
    images = doc.get("images", [])
    textures = doc.get("textures", [])
    materials = doc.get("materials", [])

    def accessor(index):
        if not isinstance(index, int) or index < 0 or index >= len(accessors):
            raise GlbFormatError(f"Accessor index {index!r} out of range")
        return accessors[index]

    mesh_rows = []
    bounds = None
    tris = 0
    uv_primitives = 0
    normals_primitives = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            mode = prim.get("mode", 4)
            attr = prim.get("attributes", {})
            if mode != 4 or "POSITION" not in attr:
                raise GlbFormatError("Expected indexed or unindexed triangle mesh")
            positions = accessor(attr["POSITION"])
            count = accessor(prim["indices"])["count"] if "indices" in prim else positions["count"]
            if count % 3:
                raise GlbFormatError("Triangle primitive indices not divisible by three")
            tri_count = count // 3
            tris += tri_count
            if "TEXCOORD_0" in attr:
                if accessor(attr["TEXCOORD_0"])["count"] != positions["count"]:
                    raise GlbFormatError("UV and vertex counts do not match")
                uv_primitives += 1
            if "NORMAL" in attr:
                if accessor(attr["NORMAL"])["count"] != positions["count"]:
                    raise GlbFormatError("Normal and vertex counts do not match")
                normals_primitives += 1
            b = [positions.get("min"), positions.get("max")]
            if b[0] is not None and b[1] is not None:
                if bounds is None:
                    bounds = [list(b[0]), list(b[1])]
                else:
                    for i in range(3):
                        bounds[0][i] = min(bounds[0][i], b[0][i])
                        bounds[1][i] = max(bounds[1][i], b[1][i])
            mesh_rows.append({
                "mesh": mesh.get("name", "unnamed"),
                "vertices": positions["count"],
                "triangles": tri_count,
                "has_uv": "TEXCOORD_0" in attr,
                "has_normals": "NORMAL" in attr,
                "material": prim.get("material")
            })

    if not mesh_rows:
        raise GlbFormatError("No triangle mesh in GLB")
    if doc.get("extensionsRequired"):
        raise GlbFormatError("Required glTF extensions cannot be audited safely")

    def valid_texture(index):
        if index is None:
            return False
        if not isinstance(index, int) or not 0 <= index < len(textures):
            raise GlbFormatError("Invalid texture index")
        source = textures[index].get("source")
        return isinstance(source, int) and 0 <= source < len(images)

    pbr = []
    for material in materials:
        props = material.get("pbrMetallicRoughness", {})
        base = props.get("baseColorTexture", {}).get("index")
        orm = props.get("metallicRoughnessTexture", {}).get("index")
        normal = material.get("normalTexture", {}).get("index")
        emissive = material.get("emissiveTexture", {}).get("index")
        for index in [base, orm, normal, emissive]:
            if index is not None:
                valid_texture(index)
        pbr.append({
            "material": material.get("name", "unnamed"),
            "base_color_texture": valid_texture(base),
            "metallic_roughness_texture": valid_texture(orm),
            "normal_texture": valid_texture(normal),
            "emission_texture": valid_texture(emissive),
            "alpha_mode": material.get("alphaMode", "OPAQUE")
        })

    image_rows = []
    for image in images:
        view = image.get("bufferView")
        byte_len = None
        if view is not None:
            if not isinstance(view, int) or not 0 <= view < len(buffer_views):
                raise GlbFormatError("Invalid embedded image view")
            info = buffer_views[view]
            offset = info.get("byteOffset", 0)
            byte_len = info["byteLength"]
            if offset < 0 or offset + byte_len > len(binary):
                raise GlbFormatError("Embedded image outside binary chunk")
        image_rows.append({
            "name": image.get("name", "unnamed"),
            "mime_type": image.get("mimeType"),
            "bytes": byte_len,
            "external_uri": bool(image.get("uri"))
        })
    extent = ([round(bounds[1][i] - bounds[0][i], 4) for i in range(3)]
              if bounds is not None else None)
    return {
        "schema": "assetwright-pbr-asset-audit-v1",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "mesh_primitives": len(mesh_rows),
        "triangles": tris,
        "bounds_xyz_m": extent,
        "mesh_details": mesh_rows,
        "materials": pbr,
        "textures": image_rows,
        "geometry_has_uvs": uv_primitives == len(mesh_rows),
        "geometry_has_normals": normals_primitives == len(mesh_rows),
        "has_pbr_textures": bool(pbr) and any(
            m["base_color_texture"] and m["metallic_roughness_texture"]
            and m["normal_texture"] for m in pbr
        ),
        "visual_quality_verified": False,
        "note": "UVs and PBR maps do not prove good modeling, valid silhouettes, "
                "material realism, licensing, or game performance. Human render "
                "review and native-engine profiling are mandatory."
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("glb", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    report = inspect(a.glb)
    result = json.dumps(report, indent=2) + "\n"
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
