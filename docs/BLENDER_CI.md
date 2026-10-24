# Blender asset build on GitHub

Assetwright uses Blender as a free, self-hosted generation step. GitHub Actions provides a temporary Linux runner, installs Blender, runs the procedural asset script in background mode, and stores its outputs as a workflow artifact. Blender is installed for the job; the application binary is not committed to the repository.

## Run it

Open **Actions → Blender asset demo → Run workflow** on the `main` branch. The workflow also runs when files under `tools/blender/` or its own workflow file change.

A successful run publishes the `assetwright-blender-demo` artifact for 14 days. It contains:

- `cargo_drone.glb`: the game prop mesh and materials, ready to inspect in a GLB viewer or import into Godot.
- `cargo_drone_preview.png`: a studio render from Blender.

## Run locally

Install Blender, then from the repository root run:

```sh
blender --background --factory-startup \
  --python tools/blender/generate_cargo_drone.py \
  -- --output-dir generated
```

## What this proves

The sample generator creates a single low-poly style game prop from editable Blender geometry and exports it without a paid model-generation API. The first pass is a procedural prototype, not an AI image-to-3D model. It gives us a working Blender job and export target so we can add prompt parsing, asset recipes, review images, and per-run learning records in small steps.

The GitHub runner is temporary. Artifacts are for review and download; this workflow does not provide a permanent generation API for the Android app. A persistent service can be added later when the generation path and operating cost are understood.
