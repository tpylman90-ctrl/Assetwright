# Assetwright

**AI game asset builder** — create real-time game assets from text prompts or reference images, inspect them in 3D, and export engine-ready GLB files.

## Project status

The Android starter app and signed APK workflow are being established. The first version is designed around one cloud generation job at a time, game performance budgets, and Godot-friendly GLB output. It is not a 3D-printing workflow.

The Android creation screen is not connected to generation yet. The first Blender-owned asset build now runs in GitHub Actions and produces a downloadable GLB plus preview render. It is a procedural prototype that establishes the export path; prompt-driven generation and the Android-to-worker connection come next. See [Blender on GitHub](docs/BLENDER_CI.md) for how to run it.

## Android app

- Package: `com.assetwright.app`
- Minimum Android: 8.0 (API 26)
- Debug APK: build with `gradle :app:assembleDebug`
- Signed release APK: build with `gradle :app:assembleRelease` after configuring the repository Actions secrets described in [Android signing](docs/ANDROID_SIGNING.md).

See [the architecture notes](docs/ARCHITECTURE.md) and [generation API contract](docs/GENERATION_API.md) for the service design and provider boundary.