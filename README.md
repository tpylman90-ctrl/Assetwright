# Assetwright

**AI game asset builder** — create real-time game assets from text prompts or reference images, inspect them in 3D, and export engine-ready GLB files.

## Project status

Assetwright targets game-ready assets with mobile-friendly mesh budgets and Godot-ready GLB output. It is not a 3D-printing workflow.

The active Blender path is the hosted GitHub Actions workflow, which runs on GitHub's Ubuntu runner and stores the GLB and preview as a three-day artifact. This keeps generation moving without the creator's PC. The current generator is a procedural cargo-drone demo; prompt-driven geometry and Android integration are future steps. A private Windows runner remains an optional higher-detail path for later. See [the hosted Blender demo](docs/BLENDER_CI.md) and [the private workbench notes](docs/PRIVATE_BLENDER_WORKBENCH.md).

## Android app

- Package: `com.assetwright.app`
- Minimum Android: 8.0 (API 26)
- Debug APK: build with `gradle :app:assembleDebug`
- Signed release APK: build with `gradle :app:assembleRelease` after configuring the repository Actions secrets described in [Android signing](docs/ANDROID_SIGNING.md).

See [the architecture notes](docs/ARCHITECTURE.md) and [generation API contract](docs/GENERATION_API.md) for the service design and provider boundary.