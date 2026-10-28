# Blender asset build on GitHub

This GitHub Actions workflow is a reproducible CI demo, not the main modeling workstation. It installs Blender on a temporary Linux runner, runs the procedural sample generator, and stores the GLB and preview as a workflow artifact. For higher-detail authoring on your PC, see the [private Blender workbench](PRIVATE_BLENDER_WORKBENCH.md). The Blender application binary is not committed to the repository.

## Run it

Open **Actions → Blender asset demo → Run workflow** on the `main` branch. The workflow also runs when files under `tools/blender/` or its own workflow file change.

A successful run publishes the `assetwright-blender-demo` artifact for 3 days. It contains:

- `hovercraft_01.glb`: the first standalone hovercraft mesh and materials, ready to inspect in a GLB viewer or import into Godot.
- `hovercraft_01_preview.png`: a three-view studio sheet of the front, side, and rear.
- `hovercraft_01_front.png`, `hovercraft_01_side.png`, and `hovercraft_01_rear.png`: individual inspection renders.

## Run locally

Install Blender, then from the repository root run:

```sh
blender --background --factory-startup \
  --python tools/blender/generate_cargo_drone.py \
  -- --output-dir generated
```

## What this proves

The sample generator creates the first hovercraft from editable Blender geometry and exports it without a paid model-generation API. The first pass is a procedural prototype, not an AI image-to-3D model. It gives us a working Blender job and export target so we can add prompt parsing, asset recipes, review images, and per-run learning records in small steps.

The GitHub runner is temporary. Artifacts are for review and download; this workflow does not provide a permanent generation API for the Android app. A persistent service can be added later when the generation path and operating cost are understood.
