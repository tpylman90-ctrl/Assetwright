#!/usr/bin/env python3
"""Offline gate for public Forge-authored shape lessons, safe for GitHub Actions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEED = ROOT / "app/src/main/assets/mini_ai/forge_lessons.json"
BOUNDS = {
    "length": (3.4, 7.0),
    "width": (1.45, 3.2),
    "roofHeight": (1.05, 2.30),
    "canopyLength": (0.85, 3.1),
    "noseTaper": (0.25, .9),
    "rearHaunch": (.9, 1.3),
}


def validate(raw: dict) -> int:
    import math
    if raw.get("schema") != "assetwright-forge-lessons-v1":
        raise ValueError("Wrong feed schema")
    if raw.get("model_type") != "reviewed-shape-lessons":
        raise ValueError("Wrong feed type")
    if not isinstance(raw.get("version"), int) or raw["version"] < 1:
        raise ValueError("Version must be a positive integer")
    lessons = raw.get("lessons")
    if not isinstance(lessons, list) or not 1 <= len(lessons) <= 200:
        raise ValueError("Expected 1..200 lessons")
    seen = set()
    for lesson in lessons:
        prompt = lesson.get("prompt")
        if not isinstance(prompt, str) or not 5 <= len(prompt) <= 1000:
            raise ValueError("Invalid prompt")
        if not any(word in prompt.lower() for word in
                   ("hover", "hoover", "suv", "racer", "coupe", "vehicle", "car")):
            raise ValueError("Out-of-scope vehicle lesson")
        if prompt.casefold() in seen:
            raise ValueError("Duplicate lesson prompt")
        seen.add(prompt.casefold())
        if not isinstance(lesson.get("provenance"), str) or not lesson["provenance"]:
            raise ValueError("Provenance required")
        params = lesson.get("parameters")
        if not isinstance(params, dict) or set(params) != set(BOUNDS):
            raise ValueError("Invalid parameter keys")
        for name, (low, high) in BOUNDS.items():
            value = params[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Invalid parameter number: " + name)
            if not low <= value <= high:
                raise ValueError("Out-of-bounds parameter: " + name)
    return len(lessons)


if __name__ == "__main__":
    print("Verified Forge shape lessons:", validate(json.loads(FEED.read_text(encoding="utf-8"))))
