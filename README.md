# Assetwright

**AI game asset builder** — create real-time game assets from text prompts or reference images, inspect them in 3D, and export engine-ready GLB files.

## Project status

The Android starter app and signed APK workflow are being established. The first version is designed around one cloud generation job at a time, game performance budgets, and Godot-friendly GLB output. It is not a 3D-printing workflow.

The generation service is not connected yet. The creation screen now supports a text prompt, one reference image, a game performance target, and a clear prepared-request state. The next stage is choosing and wiring a model endpoint, then building the 3D preview and export pipeline.

## Android app

- Package: `com.assetwright.app`
- Minimum Android: 8.0 (API 26)
- Debug APK: build with `gradle :app:assembleDebug`
- Signed release APK: build with `gradle :app:assembleRelease` after configuring the repository Actions secrets described in [Android signing](docs/ANDROID_SIGNING.md).

See [the architecture notes](docs/ARCHITECTURE.md) for the planned generation pipeline.