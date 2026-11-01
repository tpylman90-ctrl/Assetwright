# Assetwright

**AI game asset builder** — create real-time game assets from text prompts or reference images, inspect them in 3D, and export engine-ready GLB files.

## Project status

Assetwright targets game-ready assets with mobile-friendly mesh budgets and Godot-ready GLB output. It is not a 3D-printing workflow.

**Offline Mini AI v0.1** is now wired into the Android generation screen: it predicts hover-vehicle shape parameters from 88 original labeled examples, constructs native 3D geometry, provides a touch-rotatable preview, and saves binary GLB. The first version covers hover SUVs, coupes and racers; it is an example-based predictor plus a procedural mesher, **not** a general neural text-to-3D generator. Reference images are not processed yet. See [Mini AI](docs/MINI_AI.md) for design and validation limits. New in v0.3: [Forge-assisted training](docs/FORGE_TRAINING.md) lets a user export the actual generated GLB and structured feedback as a private review ZIP, then import a bounded, SHA-verified parameter correction for preview and explicit approval. **Opt-in on-device corrections and a private home training worker** are available. Version 0.4 adds a Windows sign-in task and an explicitly paired Android learning folder for automatic LAN-only transfers of approved training data. See [background training setup](docs/BACKGROUND_TRAINING.md) and [automatic training details](docs/MINI_AI_TRAINING.md).

The existing Blender workflows remain available through GitHub Actions for Mantis, Parallax and other higher-detail procedural models. They are distinct from the Android generator. See [hosted Blender demo](docs/BLENDER_CI.md) and [private workbench notes](docs/PRIVATE_BLENDER_WORKBENCH.md).

## Android app

- Package: `com.assetwright.app`
- Minimum Android: 8.0 (API 26)
- Debug APK: build with `gradle :app:assembleDebug`
- Signed release APK: build with `gradle :app:assembleRelease` after configuring the repository Actions secrets described in [Android signing](docs/ANDROID_SIGNING.md).

See [the architecture notes](docs/ARCHITECTURE.md) and [generation API contract](docs/GENERATION_API.md) for the service design and provider boundary.