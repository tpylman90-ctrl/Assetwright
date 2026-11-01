#!/usr/bin/env python3
"""Bounded CC0 model-study job for Forge-led Assetwright training sessions.

This tool does not train the Android six-parameter regressor. It collects
independently authored shape/geometry evidence and emits a compact candidate
report for Forge to inspect before authoring any new generator/shape lessons.

Source: Poly Haven's official public API (CC0 assets). Follow API terms.
No site scraping, paid services, automatic Git commits, or raw-mesh uploads.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
import time
import urllib.parse
import urllib.request

from import_glb import inspect_glb

API = "https://api.polyhaven.com"
SOURCE = "Poly Haven"
AGENT = "Assetwright-ForgeResearch/0.1 (https://github.com/tpylman90-ctrl/Assetwright)"
# Keep a small, purpose-driven mechanical/vehicle vocabulary. Human reviewer
# decides whether a non-vehicle example actually teaches anything relevant.
TOPICS = {
    "vehicle": 14, "car": 10, "truck": 12, "motorcycle": 12, "wheel": 9,
    "engine": 11, "propulsion": 14, "mechanical": 8, "machinery": 8,
    "machine": 7, "industrial": 4, "aircraft": 12, "sci-fi": 9,
    "motor": 8, "tire": 9, "tyre": 9, "robot": 7,
}
VALID_QUERY = re.compile(r"^[a-z0-9 ,/_-]{3,120}$", re.I)
MAX_DOWNLOAD = 12 * 1024 * 1024
MAX_ASSETS = 8
OUTPUT_SCHEMA = "assetwright-cc0-shape-study-v1"


def read_request(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "assetwright-forge-training-request-v1":
        raise ValueError("Unknown Forge training request schema")
    cycle = data.get("cycle")
    if type(cycle) is not int or not 1 <= cycle <= 100000:
        raise ValueError("Invalid cycle number")
    count = data.get("max_assets", 4)
    if type(count) is not int or not 1 <= count <= MAX_ASSETS:
        raise ValueError("max_assets must be between 1 and 8")
    focus = data.get("focus", "mechanical vehicle shape references")
    if not isinstance(focus, str) or not VALID_QUERY.fullmatch(focus):
        raise ValueError("Invalid research focus")
    return {"cycle": cycle, "max_assets": count, "focus": focus.strip()}


def api_json(path: str) -> dict:
    # Only explicitly constructed official API paths; no arbitrary URLs.
    if not re.fullmatch(r"/(?:assets\?t=models|files/[A-Za-z0-9_-]+)", path):
        raise ValueError("Unexpected Poly Haven API path")
    request = urllib.request.Request(
        API + path, headers={"User-Agent": AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=18) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("API response too large")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Unexpected API response")
    return result


def relevance(item: dict, focus: str) -> int:
    words = set(re.findall(
        r"[a-z]+", " ".join(str(x) for x in (
            item.get("name", ""), item.get("category", ""),
            " ".join(item.get("tags", []) if isinstance(item.get("tags"), list) else [])
        )).lower()
    ))
    score = sum(value for key, value in TOPICS.items() if key in words)
    focus_words = set(re.findall(r"[a-z]+", focus.lower()))
    score += 3 * len(focus_words & words)
    return score


def selected_assets(catalog: dict, focus: str, limit: int) -> list[tuple[str, dict]]:
    candidates = []
    for key, item in catalog.items():
        if not re.fullmatch("[A-Za-z0-9_-]{1,100}", key):
            continue
        if not isinstance(item, dict) or item.get("type") != 2:
            continue
        score = relevance(item, focus)
        if score <= 0:
            continue
        candidates.append((score, key, item))
    candidates.sort(key=lambda x: (-x[0], x[1].lower()))
    return [(key, item) for _, key, item in candidates[:limit]]


def normalized_dimensions(raw: object) -> list[float] | None:
    if not isinstance(raw, list) or len(raw) != 3:
        return None
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in raw):
        return None
    maximum = max(raw)
    return [round(v / maximum, 5) for v in raw]


def candidate_glb(file_tree: dict) -> tuple[str, int | None, str | None] | None:
    """Prefer smallest explicitly advertised GLB; don't guess file URLs."""
    found = []
    def walk(item: object) -> None:
        if isinstance(item, dict):
            url = item.get("url")
            if isinstance(url, str):
                parsed = urllib.parse.urlparse(url)
                name = parsed.path.lower()
                if (parsed.scheme == "https" and
                    (parsed.hostname or "").endswith(".polyhaven.org") and
                    name.endswith(".glb")):
                    size = item.get("size")
                    if size is None or (type(size) is int and 0 < size <= MAX_DOWNLOAD):
                        found.append((url, size, item.get("md5")))
            else:
                for value in item.values():
                    walk(value)
        elif isinstance(item, list):
            for value in item:
                walk(value)
    walk(file_tree)
    found.sort(key=lambda x: (x[1] if x[1] is not None else MAX_DOWNLOAD, x[0]))
    return found[0] if found else None


def read_glb(url: str, expected_size: int | None, expected_md5: str | None, destination: Path) -> dict:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ("dl.polyhaven.org", "files.polyhaven.org"):
        raise ValueError("Unapproved model download host")
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    # urllib follows redirects; check final host after opening, before streaming.
    with urllib.request.urlopen(req, timeout=30) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ("dl.polyhaven.org", "files.polyhaven.org"):
            raise ValueError("Redirect to unapproved download host")
        md5 = hashlib.md5()
        total = 0
        with destination.open("wb") as out:
            while True:
                block = response.read(65536)
                if not block:
                    break
                total += len(block)
                if total > MAX_DOWNLOAD:
                    raise ValueError("GLB download exceeded 12 MiB cap")
                md5.update(block)
                out.write(block)
    if expected_size is not None and total != expected_size:
        raise ValueError("Downloaded GLB size differs from official metadata")
    if isinstance(expected_md5, str) and re.fullmatch("[0-9a-fA-F]{32}", expected_md5):
        if md5.hexdigest().lower() != expected_md5.lower():
            raise ValueError("Downloaded GLB checksum mismatch")
    return inspect_glb(destination)


def catalog_asset(asset_id: str, entry: dict, try_geometry: bool) -> dict:
    dimension_ratios = normalized_dimensions(entry.get("dimensions"))
    result = {
        "id": asset_id,
        "source": SOURCE,
        "source_page": f"https://polyhaven.com/a/{asset_id}",
        "license": "CC0-1.0",
        "license_evidence": "https://polyhaven.com/license",
        "api_terms": "https://github.com/Poly-Haven/Public-API/blob/master/ToS.md",
        "name": str(entry.get("name", ""))[:200],
        "category": str(entry.get("category", ""))[:180],
        "tags": entry.get("tags", [])[:30] if isinstance(entry.get("tags"), list) else [],
        "description": str(entry.get("description", ""))[:900],
        "source_polycount": entry.get("polycount"),
        "normalized_dimensions": dimension_ratios,
        "mesh_analysis": "not_analyzed",
    }
    if try_geometry:
        try:
            files = api_json("/files/" + asset_id)
            candidate = candidate_glb(files)
            if candidate is None:
                result["mesh_analysis"] = "no_supported_small_glb"
            else:
                url, size, checksum = candidate
                with tempfile.TemporaryDirectory(prefix="assetwright_study_") as work:
                    glb = Path(work) / "candidate.glb"
                    result["geometry"] = read_glb(url, size, checksum, glb)
                    result["mesh_analysis"] = "glb_structure_inspected"
        except (OSError, ValueError, urllib.error.URLError) as error:
            result["mesh_analysis"] = "glb_unavailable"
            result["error"] = str(error)[:260]
    return result


def run_cycle(request: dict, *, fetch_geometry: bool = True) -> dict:
    catalog = api_json("/assets?t=models")
    matches = selected_assets(catalog, request["focus"], request["max_assets"])
    result = []
    for index, (asset_id, entry) in enumerate(matches):
        result.append(catalog_asset(asset_id, entry, fetch_geometry))
        if index + 1 < len(matches):
            time.sleep(.4)  # avoid bursts on third-party API
    return {
        "schema": OUTPUT_SCHEMA,
        "cycle": request["cycle"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "focus": request["focus"],
        "source": SOURCE,
        "source_credit": "Powered by Poly Haven",
        "license": "CC0-1.0",
        "source_count": len(result),
        "geometry_inspected_count": sum(
            x["mesh_analysis"] == "glb_structure_inspected" for x in result),
        "assets": result,
        "model_training_performed": False,
        "android_model_updated": False,
        "note": "Candidate geometry descriptors for human/Forge review. "
                "No Android learning pack is promoted from unreviewed assets.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    req = read_request(args.request)
    result = run_cycle(req, fetch_geometry=not args.metadata_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Assetwright study cycle", req["cycle"])
    print("Source metadata records:", result["source_count"])
    print("Actual GLBs structurally inspected:", result["geometry_inspected_count"])
    print("Study report:", args.output)
    print("No Android training weights were modified; Forge review is required.")


if __name__ == "__main__":
    main()
