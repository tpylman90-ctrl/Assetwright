# Assetwright

**AI game asset builder** — create real-time game assets from text prompts or reference images, inspect them in 3D, and export engine-ready GLB files.

## Project status

Assetwright targets game-ready assets with mobile-friendly mesh budgets and Godot-ready GLB output. It is not a 3D-printing workflow.

The detailed Blender workflow is being prepared for a private GitHub Actions runner on the creator's PC, so Blender can use local hardware without a ChatGPT MCP bridge. Trial outputs are temporary: one job at a time, 250 MiB per run, and three-day artifact retention. The current generator is a procedural cargo-drone demo; prompt-driven geometry and Android integration are future steps. See [Private Blender workbench](docs/PRIVATE_BLENDER_WORKBENCH.md) and [the hosted CI demo](docs/BLENDER_CI.md).

## Android app

- Package: `com.assetwright.app`
- Minimum Android: 8.0 (API 26)
- Debug APK: build with `gradle :app:assembleDebug`
- Signed release APK: build with `gradle :app:assembleRelease` after configuring the repository Actions secrets described in [Android signing](docs/ANDROID_SIGNING.md).

See [the architecture notes](docs/ARCHITECTURE.md) and [generation API contract](docs/GENERATION_API.md) for the service design and provider boundary.