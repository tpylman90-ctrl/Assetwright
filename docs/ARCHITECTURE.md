# Assetwright architecture

## Product target

Assetwright creates real-time game assets. It targets usable silhouettes, predictable triangle and texture budgets, mobile-friendly performance, and engine-ready exports. It does not target watertight geometry, wall thickness, or other 3D-print requirements.

## Planned flow

1. The Android client collects a text prompt and/or one reference image, plus a game-performance preset.
2. For now, the public repository's hosted Ubuntu workflow runs the procedural Blender demo and uploads a short-lived GLB and preview artifact.
3. A private self-hosted Windows runner can be reactivated later for higher-detail work. Selected approved assets can then be admitted to the public project and optimized for Godot.
4. The client previews the result and lets the user save or export the asset. A hosted service can follow when generation volume and operating cost are understood.

## Boundaries

- Android UI and asset library live under app/.
- The initial Android-to-service job contract is documented in [Generation API](GENERATION_API.md).
- Asset generation uses an Assetwright-owned Blender Python pipeline. The current hosted demo keeps generated files out of Git and stores them temporarily as Actions artifacts. See [the Blender CI demo](BLENDER_CI.md), [Private Blender workbench](PRIVATE_BLENDER_WORKBENCH.md), and [Generation API](GENERATION_API.md).
- Record prompts, asset specs, generator versions, turntable renders, and user corrections after every run. Improve templates from the records first; promote trained updates only after validation. Details are in [the learning loop](GENERATION_API.md#learning-loop).
- Keep reviewed examples only with the user's permission; promote generator changes after validation. See [the learning loop](GENERATION_API.md#learning-loop).
- Signing secrets belong in GitHub Actions secrets only; never commit keystores or credentials.

The current starter build contains the creation screen and reference-image picker. It does not yet call a generation endpoint or display a generated mesh.
