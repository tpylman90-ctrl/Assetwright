# Assetwright Mini AI — offline Android v0.1

This is the **first working foundation**, not a general-purpose learned text-to-3D
model. It deliberately has a narrow supported family: hover SUVs, coupes, racers
and speedsters. No remote services, subscriptions or inference API are used.

## Current implementation

- `MiniAi.kt` selects nearby labeled examples using normalized prompt-token
  similarity and predicts six bounded numeric vehicle parameters. This is a
  small non-parametric example-based learner, not an LLM or diffusion model.
- `training_examples.json` includes 88 **original synthetic** labeled examples
  generated from hand-authored vehicle recipes. The examples are not external
  mesh training data and do not represent independently learned mesh topology.
- `MiniGeometry.kt` constructs an actual Android-side procedural polygon mesh:
  a lofted shell, bonded canopy, central keel, underslung lift units,
  rear propulsion outlets and lights.
- `MiniPreview.kt` paints those same triangles as a touch-rotatable shaded
  preview. It is a lightweight software preview, not a full PBR engine.
- `GlbWriter.kt` exports glTF 2.0 binary files with materials, index buffers,
  positions and normals using Android's document picker.

Try these prompts in the app:

> A wide hover SUV with a panoramic elongated canopy and bulky rear haunch.

> A low hover racer with a long extended nose and a narrow frame.

> A luxury hover coupe with a tall roomy cockpit.

The app ignores the selected reference image for offline generation **in this
version** and clearly notes this in the interface.

## Training data and provenance

The next stage is import and curation of real GLB training examples, beginning
with models under verified CC0 licenses. Do not assume that a model is usable
for training because it is free to download, present in the Godot Asset Library
or BlenderKit, or provided in a game template.

First-pass importer:

```bash
python tools/mini_ai/import_glb.py my_asset.glb \
  --source-url 'https://example.org/original-cc0-asset' \
  --license CC0-1.0 \
  --label vehicle \
  --description 'Compact futuristic vehicle with tapered nose' \
  --approved
```

This analyzes metadata, records the SHA-256 hash, primitive statistics, source,
license and manual description in `local-data/mini-ai/candidates.jsonl`. It
**does not** modify the Android learner, import geometry into app resources,
reverse engineer parameter labels, claim topology is semantically tagged, or
train a neural network. This separation is intentional.

The dataset importer currently counts indexed triangle primitives (mode 4).
Other primitive modes are reported as unmeasured. Some GLBs contain unusual
extensions or transforms; absolute world dimensions and part semantics are not
inferred from the basic statistics.

Run its tests with:

```bash
python -m unittest discover -s tools/mini_ai -p 'test_*.py'
```

## Planned next gates

1. Verify Android compilation, GLB decoding in Godot/Blender, and controls on
   physical Android hardware. Document any incompatibilities.
2. Add editable dimension sliders and regenerate the native mesh interactively.
3. Develop a reference-license and human-label review queue for CC0 GLB models.
4. Build a **separate trained parameter regressor** from geometry and verified
   labels, evaluate held-out accuracy against the current neighbor baseline.
5. Convert the compact validated model into an on-device inference format; add
   new families only after their native geometry templates are reliable.
6. Optionally run the same asset specification through higher-detail Blender
   generators on a home workstation over a private LAN.

The current mesh has simplified topology and no baked textures, LOD switching,
collision export, skeletal animation or arbitrary single-view reconstruction.
Do not treat a successful file write as proof of Godot integration.
