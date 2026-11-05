"""Source-hashed, multi-view CAD lessons for AssetWright's frozen DINOv2 teacher.

Downloaded CAD scripts are parsed as data, NEVER executed. No external geometry
is imported into the Android app or used to produce production models.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from zero_to_cad_ingest import DATASET, LICENSE, SCHEMA, dataset_iterator, parse_row
from zero_to_cad_dinov2_teacher import MODEL, SCHEMA as TEACHER_SCHEMA

VIEWS = ("image_0", "image_2", "image_4", "image_6")
MAX_PIXELS = 4096 * 4096


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_views(source: dict, row: dict, directory: Path) -> None:
    from PIL import Image, ImageOps
    files, hashes = {}, {}
    for key in VIEWS:
        raw = source.get(key)
        if isinstance(raw, (bytes, bytearray)):
            payload = bytes(raw)
            if not 0 < len(payload) <= 4_000_000:
                raise ValueError("Missing or excessive licensed image bytes")
            picture = Image.open(BytesIO(payload))
        elif isinstance(raw, dict) and isinstance(raw.get("bytes"), bytes):
            payload = raw["bytes"]
            if not 0 < len(payload) <= 4_000_000:
                raise ValueError("Missing or excessive licensed image bytes")
            picture = Image.open(BytesIO(payload))
        elif hasattr(raw, "convert"):
            picture = raw
        else:
            raise ValueError("Missing required source camera view " + key)
        if picture.width * picture.height > MAX_PIXELS or min(picture.size) < 32:
            raise ValueError("Untrusted source image dimensions")
        filename = row["source_id"] + "__" + key + ".png"
        if not re.fullmatch(r"[A-Za-z0-9_-]+__image_[0246]\.png", filename):
            raise ValueError("Unsafe source filename")
        destination = directory / filename
        ImageOps.exif_transpose(picture).convert("RGB").save(destination, format="PNG")
        files[key] = filename
        hashes[key] = digest(destination)
    row["view_files"], row["view_sha256"] = files, hashes


def ingest(split: str, revision: str, *, offset: int, count: int,
           scan_limit: int, images: Path, output: Path) -> dict:
    if split not in ("train", "validation"):
        raise ValueError("Unknown official split")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Freeze source dataset at a 40-character revision")
    if not (0 <= offset <= 4000 and 32 <= count <= 500 and
            count <= scan_limit <= 1600 and offset + scan_limit <= 6000):
        raise ValueError("Unbounded multi-view teaching request")
    images.mkdir(parents=True, exist_ok=True)
    accepted, ids, hashes, rejected = [], set(), set(), Counter()
    scanned = 0
    for index, raw in enumerate(dataset_iterator(split, revision)):
        if index < offset:
            continue
        if scanned >= scan_limit or len(accepted) >= count:
            break
        scanned += 1
        row, reason = parse_row(raw, split)
        if row is None:
            rejected[reason] += 1
            continue
        if row["source_id"] in ids or row["code_sha256"] in hashes:
            rejected["duplicate_cad_source"] += 1
            continue
        save_views(raw, row, images)
        accepted.append(row)
        ids.add(row["source_id"])
        hashes.add(row["code_sha256"])
    if len(accepted) < count:
        raise ValueError("Insufficient genuine, four-view licensed CAD examples")
    document = {"schema": SCHEMA, "dataset": DATASET, "license": LICENSE,
                "dataset_revision": revision, "split": split, "records": accepted,
                "offset": offset, "scanned": scanned, "accepted": len(accepted),
                "teacher_views": list(VIEWS), "rejections": dict(rejected),
                "raw_python_executed": False, "external_meshes_exported": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + "\n")
    return document


def verified_views(document: dict, directory: Path):
    if (document.get("schema") != SCHEMA or
            document.get("license") != LICENSE or
            document.get("teacher_views") != list(VIEWS) or
            not re.fullmatch(r"[0-9a-f]{40}", document.get("dataset_revision", ""))):
        raise ValueError("Unverified, unpinned training curriculum")
    for row in document["records"]:
        names, hashes = row.get("view_files"), row.get("view_sha256")
        if not isinstance(names, dict) or set(names) != set(VIEWS) or not isinstance(hashes, dict) or set(hashes) != set(VIEWS):
            raise ValueError("Incomplete four-view source record")
        paths = []
        for key in VIEWS:
            name = names[key]
            if not isinstance(name, str) or Path(name).name != name or not name.endswith(".png"):
                raise ValueError("Unsafe camera-view path")
            path = directory / name
            if not path.is_file() or digest(path) != hashes[key]:
                raise ValueError("Source image hash mismatch")
            paths.append(path)
        yield row, paths


def teach(manifest: Path, images: Path, output: Path) -> dict:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, Dinov2Model
    doc = json.loads(manifest.read_text())
    pairs = list(verified_views(doc, images))
    if len(pairs) < 32:
        raise ValueError("Insufficient image/source-aligned CAD geometry")
    torch.set_num_threads(min(2, torch.get_num_threads()))
    processor = AutoImageProcessor.from_pretrained(MODEL, trust_remote_code=False)
    encoder = Dinov2Model.from_pretrained(
        MODEL, trust_remote_code=False, use_safetensors=True).eval().to("cpu")
    results = []
    for row, paths in pairs:
        vectors = []
        for start in range(0, len(paths), 2):
            batch = []
            for path in paths[start:start + 2]:
                with Image.open(path) as image:
                    batch.append(image.convert("RGB"))
            arguments = processor(images=batch, return_tensors="pt")
            with torch.inference_mode():
                vectors.extend(encoder(**arguments).last_hidden_state[:, 0, :].cpu().tolist())
        if len(vectors) != len(VIEWS) or any(len(vec) != 384 for vec in vectors):
            raise ValueError("Invalid DINOv2 feature dimensions")
        mean = [sum(vec[i] for vec in vectors) / len(vectors) for i in range(384)]
        spread = sum((vec[i] - mean[i]) ** 2 for vec in vectors for i in range(384)) / (len(vectors) * 384)
        results.append({"source_id": row["source_id"],
                        "code_sha256": row["code_sha256"],
                        "split": row["split"], "view_sha256": row["view_sha256"],
                        "view_count": len(VIEWS),
                        "cross_view_disagreement_mse": round(spread, 8),
                        "frozen_visual_embedding": [round(float(v), 8) for v in mean]})
    package = {"schema": TEACHER_SCHEMA, "model_id": MODEL,
               "teacher_frozen": True, "teacher_generates_3d": False,
               "source_dataset": doc["dataset"], "source_split": doc["split"],
               "source_license": LICENSE, "dataset_revision": doc["dataset_revision"],
               "view_count": len(VIEWS), "records": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(package, separators=(",", ":")) + "\n")
    return package


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    source = sub.add_parser("ingest")
    source.add_argument("--split", choices=("train", "validation"), required=True)
    source.add_argument("--revision", required=True)
    source.add_argument("--offset", type=int, required=True)
    source.add_argument("--count", type=int, required=True)
    source.add_argument("--scan-limit", type=int, default=1200)
    source.add_argument("--images", type=Path, required=True)
    source.add_argument("--output", type=Path, required=True)
    teacher = sub.add_parser("teach")
    teacher.add_argument("--manifest", type=Path, required=True)
    teacher.add_argument("--images", type=Path, required=True)
    teacher.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "ingest":
        doc = ingest(args.split, args.revision, offset=args.offset, count=args.count,
                     scan_limit=args.scan_limit, images=args.images, output=args.output)
        print(json.dumps({"split": args.split, "accepted": doc["accepted"],
                          "view_count": len(VIEWS), "source_revision": args.revision}))
    else:
        package = teach(args.manifest, args.images, args.output)
        print(json.dumps({"teacher": MODEL, "examples": len(package["records"]),
                          "camera_views_per_example": len(VIEWS),
                          "external_mesh_generation": False}))


if __name__ == "__main__":
    main()
