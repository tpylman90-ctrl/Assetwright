# Assetwright v0.6 — supervised semantic construction planner

## What the mini AI learns

The original six-dimensional body predictor is now accompanied by a small
**supervised text-to-construction classifier** written in Kotlin. It trains
Laplace-smoothed Naive Bayes word statistics using approved **original
developer-authored construction labels**, rather than pretending to derive
component identity from unannotated CC0 meshes.

For hover vehicles, this first constrained task predicts:
- lift-unit count: 2, 4, or 6;
- mounting: tucked under the body, or exposed/outboard.

User-specified counts and explicit mounting requests override statistical
predictions. Missing or invalid training data falls back to four tucked
lift cells. The earlier 1/2/3-engine logic is unaffected.

### Real geometry integration

MiniGeometry now builds the chosen number of closed underside repulsor
meshes and matching emissive fields. Every lift unit also gets a bounded
support-bracket mesh physically spanning toward the underbody. Exposed
mounts extend farther outboard; tucked layouts sit below the body.
The exported ShapeProgram records:
- `attach_repulsor_mounts`: mount count, outboard code, depends on undercarriage
- `attach_repulsors`: lift-unit count, depends on mount brackets

The native app displays the chosen lift-unit layout and counts. No
third-party GLB is copied, embedded, or used as an Android runtime asset.

## Training and evaluation

Training data:
`app/src/main/assets/mini_ai/construction_labels.json`

- 72 original, labeled training prompts, balanced across six class combinations.
- 24 held-out, separately phrased validation prompts.
- No external model-derived semantic labels in this dataset.
- The app checks both label accuracies; only a candidate with at least
  80% held-out accuracy on both targets becomes active.
- The held-out dataset uses controlled synthetic word variants, and
  must not be described as independent real-world validation. High scores
  are expected for clear, explicit words and do not imply general language
  understanding.

Future reviewed construction lessons can be added by Forge to the opt-in
public `forge_lessons.json` feed as `semantic_lessons`.
Android validates each new lesson and retrains on its local copy after an
enabled download, keeping the existing model if held-out performance regresses.

**GitHub-fed semantic lessons are public original descriptions**, not private
user prompts, unapproved CC0 copies, or arbitrary executable modeling scripts.
The Android source code still defines which operations are permitted; this
learning feed cannot introduce unchecked new geometry operations.

## CC0 research vs semantic training

The Poly Haven research workflow still extracts anonymous part bounding
boxes and geometric-island proximity graphs. Cycle 5 used four multi-part
models to train a two-prototype geometric-layout prior. Cycle 6 completed,
but did not increase the number of unique source descriptors. Those
experimental CC0 priors have **not** been treated as verified semantic
attachments, and are not mixed into the new supervised planner.

Real mesh-part identities, joining surfaces, topological connectivity,
mounting constraints and modeling-operation histories require reviewed labels.
The next useful iteration is to build a more varied and independently labeled
reference corpus and train predictions for additional native modeling operations.

## Testing and deployment

- Android JVM tests validate explicit overrides, learned categories, actual
  mesh counts, support bracket extents and exported dependencies.
- Python tests validate corpus balance, holdout separation and feed schemas.
- GitHub Actions must pass `:app:testDebugUnitTest` and `:app:assembleDebug`.
- A successful APK build still needs physical-phone visual inspection.

Future semantic lesson feed updates do not require another APK, **but
new geometry primitives, code or 3D construction operations do**.
