"""Local MCP bridge for running approved Assetwright Blender generators.

This service intentionally exposes named generators only. It does not accept
arbitrary shell commands, Blender scripts, or filesystem paths from tool calls.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Image, MCPServer

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "tools" / "blender" / "generate_cargo_drone.py"
OUTPUT_ROOT = ROOT / "generated" / "local"
_GENERATION_LOCK = threading.Lock()
_latest_preview: Path | None = None
_latest_glb: Path | None = None

mcp = MCPServer("Assetwright Local Blender")


def find_blender() -> str | None:
    configured = os.environ.get("ASSETWRIGHT_BLENDER")
    if configured and Path(configured).is_file():
        return configured

    found = shutil.which("blender") or shutil.which("blender.exe")
    if found:
        return found

    if os.name == "nt":
        roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]
        matches: list[str] = []
        for root in roots:
            matches.extend(glob.glob(os.path.join(root, "Blender Foundation", "Blender*", "blender.exe")))
        if matches:
            return sorted(matches)[-1]
    return None


@mcp.tool()
def blender_status() -> dict[str, Any]:
    """Read Blender availability and the local Assetwright output workspace."""
    executable = find_blender()
    version = None
    if executable:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        version = (result.stdout or result.stderr).splitlines()[0:2]
    return {
        "available": executable is not None,
        "blender_executable": executable,
        "version": version,
        "workspace": str(ROOT),
        "output_directory": str(OUTPUT_ROOT),
        "generators": ["cargo_drone_demo"],
    }


@mcp.tool()
def generate_cargo_drone_demo(approved: bool = False) -> dict[str, Any]:
    """Run the allowlisted Blender cargo-drone demo.

    This creates a new GLB and PNG under generated/local/<job_id>. It does not
    modify existing files. Call only after the user has approved this run.
    """
    global _latest_preview, _latest_glb

    if approved is not True:
        raise ValueError("This Blender run writes new files. Set approved=true only after the user explicitly approves this run.")

    executable = find_blender()
    if executable is None:
        raise RuntimeError("Blender was not found. Install Blender or set ASSETWRIGHT_BLENDER to blender.exe.")

    if not GENERATOR.is_file():
        raise RuntimeError("The allowlisted cargo-drone generator is missing from the Assetwright checkout.")

    if not _GENERATION_LOCK.acquire(blocking=False):
        raise RuntimeError("Another Blender generation is running. Wait for it to finish before starting another.")

    job_id = "local_" + uuid.uuid4().hex[:12]
    output_dir = OUTPUT_ROOT / job_id
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
        command = [
            executable,
            "--background",
            "--factory-startup",
            "--python",
            str(GENERATOR),
            "--",
            "--output-dir",
            str(output_dir),
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        glb = output_dir / "cargo_drone.glb"
        preview = output_dir / "cargo_drone_preview.png"
        if result.returncode != 0:
            raise RuntimeError("Blender failed (exit {}). {}".format(result.returncode, (result.stderr or result.stdout)[-4000:]))
        if not glb.is_file() or glb.stat().st_size < 1024:
            raise RuntimeError("Blender did not produce a valid GLB. {}".format((result.stderr or result.stdout)[-4000:]))
        if not preview.is_file() or preview.stat().st_size < 1024:
            raise RuntimeError("Blender did not produce a preview render.")
        _latest_glb = glb
        _latest_preview = preview
        return {
            "job_id": job_id,
            "status": "succeeded",
            "glb_path": str(glb),
            "glb_bytes": glb.stat().st_size,
            "preview_path": str(preview),
            "preview_bytes": preview.stat().st_size,
        }
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Blender exceeded the 15-minute job limit.") from exc
    finally:
        _GENERATION_LOCK.release()


@mcp.tool()
def get_latest_blender_preview() -> Image:
    """Return the rendered preview image from the most recent local Blender run."""
    if _latest_preview is None or not _latest_preview.is_file():
        raise RuntimeError("No local Blender preview is available yet. Run the approved cargo-drone demo first.")
    return Image(path=str(_latest_preview))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("The local bridge must bind to loopback. Use ChatGPT Secure MCP Tunnel for private access.")

    print("Assetwright local Blender MCP server")
    print("Listening on http://{}:{}/mcp".format(args.host, args.port))
    print("Only allowlisted generators are exposed; generation creates new files.")
    mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
