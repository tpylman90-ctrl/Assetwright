# Assetwright architecture

## Product target

Assetwright creates real-time game assets. It targets usable silhouettes, predictable triangle and texture budgets, mobile-friendly performance, and engine-ready exports. It does not target watertight geometry, wall thickness, or other 3D-print requirements.

## Planned flow

1. The Android client collects a text prompt and/or one reference image, plus a game-performance preset.
2. During development, a local MCP worker on the creator's PC starts an allowlisted Blender generator. Blender runs on that PC and saves an editable source asset, GLB, and preview.
3. GitHub Actions provides reproducible build and validation jobs, then prepares a mobile-friendly GLB for Godot.
4. The client previews the result and lets the user save or export the asset. A hosted service can follow when generation volume and operating cost are understood.

## Boundaries

- Android UI and asset library live under app/.
- The initial Android-to-service job contract is documented in [Generation API](GENERATION_API.md).
- Asset generation uses an Assetwright-owned Blender Python pipeline. The local MCP worker is in `tools/blender/local_mcp_server.py`; it binds only to loopback and exposes named generators, not arbitrary commands. ChatGPT reaches it through a private Secure MCP Tunnel. See [Local Blender bridge](LOCAL_BLENDER_BRIDGE.md) and [Generation API](GENERATION_API.md).
- Record prompts, asset specs, generator versions, turntable renders, and user corrections after every run. Improve templates from the records first; promote trained updates only after validation. Details are in [the learning loop](GENERATION_API.md#learning-loop).
- A private MCP bridge lets ChatGPT inspect runs, propose constrained Blender corrections, and help curate training examples. Run changes and training promotions require user confirmation; see [the ChatGPT training bridge](GENERATION_API.md#chatgpt-training-bridge).
- Signing secrets belong in GitHub Actions secrets only; never commit keystores or credentials.

The current starter build contains the creation screen and reference-image picker. It does not yet call a generation endpoint or display a generated mesh.
