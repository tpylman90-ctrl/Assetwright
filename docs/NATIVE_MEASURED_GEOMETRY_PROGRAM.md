# AssetWright native measured geometry and multi-operation construction v1

## Goal and strict limits

Extend the research-only AssetWright-owned Mini AI from operation selection
and text-based strength labels to *actual measured native geometry targets*.
This is a controlled CPU experiment in inverse procedural modeling and
composition, not a pretrained image-to-3D generator, not a Class-A surfacing
system, and not Android production deployment.

Everything is **original AssetWright native geometry**, executed inside
MiniGeometry/GlbWriter from allowlisted typed operations. No external model
produces, supplies, imports, or copies the final mesh. Zero-to-CAD CAD
operations and DINOv2 remain independently verified earlier teachers; their
pretrained geometry/visual knowledge is not directly fused into this inverse
parameter model.

## Two genuine learning stages

1. The saved validated AssetWright text-intent student selects modeling
   *operation names*. Its three known categories are cockpit shoulder sculpt,
   connected rear-hull socket, and tapered rear engine shroud. Confidence
   failure rejects the proposal; there is no handcrafted fallback.
2. A new, tiny original **monotone procedural response learner** receives
   source-verified GLBs at controlled strengths. It measures the physical
   response of each operation from actual vertex positions, instead of
   re-learning which adjective means which numerical strength. It learns
   response curves and inverts them to determine control settings for a
   specified *measured geometric target*. Inference uses no outside
   pretrained model and requires no direct 3D mesh generator from another AI.

The parser uses only native source GLBs from the Android Kotlin JVM exporter.
Original provenance hashes and topology checks are required before metrics
are used. No downloaded executable CAD scripts are evaluated.

## Procedural dataset and evaluation

- Train families: one-engine original hover *coupe* and *utility*, with
  original hull/engine geometry at native strengths 0.25, 0.50, and 0.90
  for each operation, plus original baseline GLBs. **20 training GLBs**.
- Unseen third geometry family: original *newfamily* hover vehicle with
  different body dimensions, source-hashed target GLBs at 0.375 and 0.725,
  plus its baseline and one three-operation target. **8 target/reference GLBs**.
  This geometry is never included in the response-curve fit.
- The actual target measurements are the aft blind well depth (meters), upper
  hull cockpit shoulder span (meters), and rear engine-housing flare ratio.
  These are limited physical shape proxies, not aesthetics or seam welding.
- Compare inferred strengths to true heldout reference strengths and a
  constant .60 baseline. The inverse model must beat the baseline by at least
  .025 MAE and achieve mean strength error below .12. No benchmark
  improvement alone is considered proof of a usable 3D model.
- Construct four *new* original GLBs: three individually inferred operations
  and one composed program. Compare each to withheld real-GLB geometric
  targets and reject invalid topology, out-of-budget geometry, duplicated
  operations, unknown commands, and wrong dependency order.
- For the **combined program**, the typed executor requires upper hull
  shoulder sculpt, rear blind recess, then rear nacelle shroud. The combined
  source mesh is audited for all three effects in the same real GLB. Engine
  shrouds remain distinct meshes and are NOT topologically welded to hulls.

## Long-term efficiency plan

- Preserve source/checkpoint hashes, response curves, and independent
  evaluation results in a research prerelease after all gates pass.
- Do not download external 3D models to use as native targets without
  verifying licensing and ownership.
- If this experiment fails, reject its measured response learner and
  retain the last validated classifier/strength checkpoint unchanged.
- The source and test generator are deterministic and bounded; no
  never-ending GitHub CPU training jobs or unsupported use of public CI.
- Future stages: more operations, learned step dependencies, stronger
  global geometric targets, independent object-category transfer,
  visually reviewed surfaces, and eventual model-driven construction
  parameter planning rather than a hand-authored three-step vocabulary.

## Key files

- `NativeCadOperationBridge.kt`: applyProgram allowlist, bounded control
  parameters, and no repeat/out-of-order program execution.
- `MeasuredNativeConstructionProgramTest.kt`: exact source-hashed native
  GLB export and construction-program execution.
- `native_measured_inverse.py`: source-only response-curve fitting,
  inversion, evaluation on untouched third-family reference targets.
- `native_measured_program_audit.py`: actual forward execution proof for
  three isolated operations and a single composed GLB.
- `.github/workflows/native-measured-geometry.yml`: free bounded CPU/JVM
  experiment with research-only artifacts.

A release is valid only after the independent full forward geometry audit.
