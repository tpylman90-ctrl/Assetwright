# Assetwright v0.5 — On-device learning and Forge contribution channel

## Direct on-phone training

The small AdaptiveShapeModel now implements an actual trainable supervised
regressor in Kotlin. Forty fixed text features predict residual corrections
for six numeric vehicle parameters, using 240 learned floating-point weights.
The input is user-approved prompt/shape examples, not full GLB files.

When the user approves a corrected asset, DeviceShapeTrainer queues a
WorkManager job (requires battery not low). It trains locally, compares against
a baseline, and writes a compact weights checkpoint if the candidate passes.
The previous weights remain when training fails. Exact user-approved designs
take priority. The six shape parameters always stay within safe limits.

This is **small on-device model training**, but NOT a neural text-to-mesh
generator. It only learns how prompt concepts affect the existing procedural
geometry. New topology and shape-construction tools still require code.

## Learning construction processes

ShapeProgram.kt can record an editable procedural recipe: loft hull, fit
canopy, add keel, attach propulsion and repulsors, attach lights. Recipes
are small JSON descriptors and contain no full vertex meshes. The Forge
review ZIP now includes shape_program.json as well as model.glb, so an
assistant can inspect both the construction process and its actual output.

The current sequence is handcrafted, **not learned by a model**. A later
operation-prediction network can be trained after we build a sufficiently
large labeled collection of construction sequences.

## Direct Forge training through GitHub

Forge can update generator code and publicly shareable learning recipes in
the existing Assetwright repository, notably:

  app/src/main/assets/mini_ai/forge_lessons.json

Android users can opt into Forge lesson updates. An enabled device downloads
only this original JSON over HTTPS from the fixed public GitHub URL, validates
the shape bounds and increasing version, then uses it for future inference.
The app never embeds a GitHub token, never writes to the repo directly, and
never uploads user prompts or GLBs. Updates can be disabled, and generation
works fully offline without them.

The initial 8 lessons are original authored shape specifications, not
learned from GLBs or visually validated vehicle models. Later lesson versions
can be improved after real rendered model review.

The CI script tools/mini_ai/check_forge_lessons.py rejects missing schema,
invalid parameter ranges, duplicates and absent provenance. Both public
lesson packs and geometry code improvements should undergo testing before
becoming recommended training material.

## How to use the new features

1. Generate an offline hover vehicle, inspect its preview, adjust sliders,
   and tap Approve design / Teach Mini AI.
2. WorkManager fits numeric weights in the background, subject to Android
   scheduling and battery constraints.
3. Optionally enable Forge training lessons once in the Android app. It
   checks the public repository periodically and uses valid new lessons.
4. Send a Forge review ZIP here for real-geometry analysis or ask me to
   improve a particular generator. I can commit code and lesson updates
   through the connected GitHub tool. No home computer is required for
   basic parameter training.
5. When the next APK is verified, test whether corrections influence new
   prompts; do not infer improved geometry solely from training loss.

## Separate model repository

A new separate GitHub repository has NOT been created. This working
prototype uses an isolated lesson file within the existing public
Assetwright repository. A dedicated private training repository could be
created later with its own permission grant, model versioning and releases.
Do not publish private prompts, third-party unlicensed GLBs or model weights
containing sensitive content into this public repository. Larger raw
datasets should use Git LFS, releases or appropriate dataset storage.

## Limitations

The current model cannot invent arbitrary complex meshes, infer topology
from raw GLBs, recognize unlabeled object parts, or choose new construction
operations on its own. Those require labeled geometric descriptors,
a separate mesh/operation model, and measurable held-out evaluations.
The Android APK and background behavior still need successful CI and
physical phone validation.
