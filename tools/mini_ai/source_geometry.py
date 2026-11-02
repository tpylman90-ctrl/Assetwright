"""Inspect CC0 models via Blender without storing source meshes.

Poly Haven's official API file tree is the only allowed source. Blender runs
in a short-lived background process with user scripts disabled. Converted
geometry is reduced to a small, bounded, dimensionless descriptor.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile

EXTENSIONS = {".glb", ".blend", ".fbx", ".obj", ".zip"}
MODEL_EXTENSIONS = EXTENSIONS - {".zip"}
MAX_BYTES = 32 * 1024 * 1024
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024
DOWNLOAD_HOSTS = {"dl.polyhaven.org", "files.polyhaven.org"}
BLENDER_TIMEOUT = 120
GEOMETRY_SCHEMA = "assetwright-geometry-descriptor-v1"
FEATURE_COUNT = 8
BLENDER_SCRIPT = Path(__file__).with_name("blender_geometry_features.py")


def valid_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    p = urllib.parse.urlparse(url)
    return p.scheme == "https" and p.hostname in DOWNLOAD_HOSTS and p.port is None \
        and p.username is None and p.password is None \
        and p.path.lower().endswith(tuple(EXTENSIONS))


def file_choices(tree: dict) -> list[dict]:
    """Find real source files from API metadata; never construct download URLs."""
    found = []
    def walk(node: object) -> None:
        if isinstance(node, dict):
            url = node.get("url")
            if isinstance(url, str):
                if not valid_url(url):
                    return
                size = node.get("size")
                if size is not None and (type(size) is not int or size < 1 or size > MAX_BYTES):
                    return
                ext = Path(urllib.parse.urlparse(url).path.lower()).suffix
                checksum = node.get("md5")
                found.append({
                    "url": url,
                    "size": size,
                    "md5": checksum if isinstance(checksum, str) else None,
                    "format": ext[1:],
                })
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)
    walk(tree)
    # Prefer native Blender over FBX. Most official models publish several
    # FBX LODs, and choosing three small FBXs first led to zero native Blender
    # attempts in the initial research cycle.
    rank = {".blend": 0, ".glb": 1, ".obj": 2, ".fbx": 3, ".zip": 4}
    found.sort(key=lambda f: (
        rank["." + f["format"]],
        f["size"] if f["size"] is not None else MAX_BYTES, f["url"]
    ))
    # Try one low-resolution candidate per format before trying higher LODs
    # of any format, so importer failures don't waste all fallback attempts.
    seen_formats = set()
    first_choice = []
    extra = []
    for candidate in found:
        kind = candidate["format"]
        if kind in seen_formats:
            extra.append(candidate)
        else:
            seen_formats.add(kind)
            first_choice.append(candidate)
    return first_choice + extra


def download(candidate: dict, destination: Path) -> dict:
    if not valid_url(candidate["url"]):
        raise ValueError("Unapproved source URL")
    req = urllib.request.Request(
        candidate["url"], headers={
            "User-Agent": "Assetwright-ForgeResearch/0.2 (https://github.com/tpylman90-ctrl/Assetwright)"
        }
    )
    total = 0
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=30) as response:
        target = response.geturl()
        if not valid_url(target):
            raise ValueError("Download redirected outside approved host")
        with destination.open("wb") as file:
            while True:
                block = response.read(65536)
                if not block:
                    break
                total += len(block)
                if total > MAX_BYTES:
                    raise ValueError("Source download exceeded 32 MiB cap")
                md5.update(block)
                sha.update(block)
                file.write(block)
    if candidate["size"] is not None and candidate["size"] != total:
        raise ValueError("Source byte count differs from the published file metadata")
    declared_md5 = candidate.get("md5")
    if (isinstance(declared_md5, str)
        and re.fullmatch("[0-9a-fA-F]{32}", declared_md5)
        and md5.hexdigest().lower() != declared_md5.lower()):
        raise ValueError("Source checksum mismatch")
    return {"source_sha256": sha.hexdigest(), "source_bytes": total}


def unpack_source(archive: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive, "r") as zipfile_obj:
        members = zipfile_obj.infolist()
        if len(members) > 500:
            raise ValueError("Too many files in source archive")
        total = 0
        valid = []
        for info in members:
            name = info.filename.replace("\\", "/")
            components = name.split("/")
            if (info.is_dir() or not name or name.startswith("/") or
                any(s in ("", ".", "..") for s in components) or
                info.flag_bits & 0x1 or
                stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)):
                continue
            if info.file_size > MAX_EXTRACTED_BYTES:
                continue
            if Path(name).suffix.lower() not in MODEL_EXTENSIONS:
                continue
            total += info.file_size
            if total > MAX_EXTRACTED_BYTES:
                raise ValueError("Source archive exceeds safe extracted size")
            valid.append(info)
        if not valid:
            raise ValueError("Source ZIP has no supported editable mesh")
        # Avoid long traversal or file collisions by extracting exactly one
        # mesh source to a fixed, randomized temporary directory.
        preferred = sorted(valid, key=lambda x: (
            {".glb": 0, ".blend": 1, ".fbx": 2, ".obj": 3}[Path(x.filename).suffix.lower()],
            x.file_size, x.filename
        ))[0]
        source = destination / ("source" + Path(preferred.filename).suffix.lower())
        with zipfile_obj.open(preferred) as inp, source.open("wb") as out:
            while True:
                chunk = inp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                if out.tell() > MAX_EXTRACTED_BYTES:
                    raise ValueError("ZIP member exceeded decompressed size cap")
        return source


def inspect_with_blender(candidate: dict, *, blender: str = "blender",
                         preview_dir: Path | None = None) -> dict:
    """Only descriptor leaves the ephemeral workdir. No model is persisted."""
    with tempfile.TemporaryDirectory(prefix="assetwright_source_") as tmp:
        folder = Path(tmp)
        source = folder / ("download." + candidate["format"])
        provenance = download(candidate, source)
        if candidate["format"] == "zip":
            source = unpack_source(source, folder)
        output = folder / "geometry.json"
        preview_tmp = folder / "review_previews"
        args = [blender, "--background", "--threads", "2", "--factory-startup",
                "--disable-autoexec", "--python", str(BLENDER_SCRIPT),
                "--", str(source), str(output)]
        if preview_dir is not None:
            args.append(str(preview_tmp))
        result = subprocess.run(
            args,
            capture_output=True, text=True, timeout=BLENDER_TIMEOUT,
            check=False
        )
        if result.returncode != 0 or not output.exists():
            raise ValueError("Blender geometry extraction failed: " +
                             (result.stderr or result.stdout)[-350:].replace("\n", " "))
        data = json.loads(output.read_text(encoding="utf-8"))
        if data.get("schema") != GEOMETRY_SCHEMA:
            raise ValueError("Unexpected Blender descriptor schema")
        features = data.get("features")
        if (not isinstance(features, list) or len(features) != FEATURE_COUNT
            or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in features)):
            raise ValueError("Invalid Blender feature vector")
        previews = []
        component_previews = {}
        if preview_dir is not None:
            requests = {name: name+".png" for name in ("three_quarter", "side", "top")}
            manifest = preview_tmp / "component_views.json"
            if manifest.is_file() and manifest.stat().st_size < 2048:
                declared = json.loads(manifest.read_text(encoding="utf-8"))
                if isinstance(declared,dict):
                    for node_id,basename in declared.items():
                        if (not isinstance(node_id,str) or not node_id.isdigit() or
                            not isinstance(basename,str) or
                            basename != "component_"+node_id+"_three_quarter" or
                            int(node_id) not in range(24)):
                            continue
                        if len(component_previews)>=3:
                            break
                        requests[basename] = basename+".png"
                        component_previews[node_id] = basename
            successful = set()
            for key, filename in requests.items():
                img = preview_tmp / filename
                if not img.is_file() or not 100 <= img.stat().st_size <= 2*1024*1024:
                    continue
                with img.open("rb") as src:
                    if src.read(8) != b"\x89PNG\r\n\x1a\n":
                        continue
                preview_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(img, preview_dir / img.name)
                successful.add(key)
            previews = [name for name in ("three_quarter", "side", "top")
                        if name in successful]
            component_previews = {k:v for k,v in component_previews.items()
                                  if v in successful}
        return {**data, **provenance, "source_format": source.suffix[1:],
                "geometry_method": "blender-headless-v1",
                "review_preview_views": previews,
                "component_review_views": component_previews}
