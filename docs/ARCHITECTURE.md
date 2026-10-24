# Assetwright architecture

## Product target

Assetwright creates real-time game assets. It targets usable silhouettes, predictable triangle and texture budgets, mobile-friendly performance, and engine-ready exports. It does not target watertight geometry, wall thickness, or other 3D-print requirements.

## Planned flow

1. The Android client collects a text prompt and/or one reference image, plus a game-performance preset.
2. A single cloud generation job runs at a time. The Android device uploads inputs and polls job status; heavy inference stays on the server.
3. The result passes through a cleanup stage for mesh validation, texture checks, triangle budgets, and optional LOD/collision generation.
4. The client previews the result and lets the user save or export a GLB package for Godot. Additional engine presets can follow.

## Boundaries

- Android UI and asset library live under app/.
- The initial Android-to-service job contract is documented in [Generation API](GENERATION_API.md).
- Asset generation uses an Assetwright-owned Blender Python pipeline on a bounded worker. The first release focuses on supported asset families with procedural geometry; uploaded or generated images guide their appearance. See [Generation API](GENERATION_API.md).
- Signing secrets belong in GitHub Actions secrets only; never commit keystores or credentials.

The current starter build contains the creation screen and reference-image picker. It does not yet call a generation endpoint or display a generated mesh.
