# Forge Mini v12 — Original-geometry resolution and physically evaluated learning

## Verified predecessor

v11 ran six genuine sequential 900-second gradient sessions (5,400 seconds)
and saved all six learned neural checkpoints. On its untouched 288-case native
blind set, the dev-selected `replay_curriculum_stage1` model was **worse**
than the frozen v10 parent: 3D Chamfer 0.0156694 vs 0.0156230. The
exploratory `surface_curriculum_stage1` learned 0.0154443 but was not
selected on development and cannot be promoted retrospectively.

The other important problem was the mesh reconstruction program. For
example, a reference spindle was generated with **2,640 triangles**, but
the student arbitrarily generated its output with **1,200 triangles**,
because the decoder hard-coded per-form mesh-resolution presets. Source and
prediction were therefore compared at different sampling densities even
when the shape form and operation matched.

## v12 hypothesis: don't train against an artificial topology mismatch

The resolution of the undeformed INPUT is actually known. The new
`rows_from` logic verifies the mesh's `segments` and `stations` against
the SOURCE's independently SHA-hashed **baseline.json**, not the target
deformed model. The neural proposals pass through those two input topology
fields unchanged. Kotlin reconstructs with exactly that original
subdivision resolution; the independent 3D auditor rejects mismatched
triangle counts or any subdivisions not authenticated by the undeformed
input and original source. Form, operator, strength, and true target
geometry are NEVER read into inference from the heldout test.

This changes the *physical evaluation conditions*, not the experimental
neural baseline. Therefore, do not compare unadjusted v11 Chamfer values
with resolution-matched v12 Chamfer values as though the improvement
came from learned weights. Within v12, every arm, including the frozen v10
parent, is measured on the same new Kotlin GLBs and input topology.

## Three short but genuine neural training runs

The independent v12 original Kotlin source school creates 1,808 new GLBs:
48 training families x 6 ops x 4 strengths (1,152 learned examples),
16 unseen development families x 6 ops x 3 strengths (288),
16 never-used blind families x 6 ops x 3 strengths (288), and
80 original undeformed input meshes. Every original form template shares
the same proportions and tessellation across eight different archetypes.
No previous v10/v11 blind family enters gradient learning.

The frozen original v6 operation model, v7 form features, and v9
form recognizer are SHA-checked. Three original 26,668-parameter
residual networks each warm-start from the **same archived v10**
`warm_replay.safetensors` and receive identical old v10 TRAIN-only
replay plus fresh v12 TRAIN-only sources. Each receives **300 seconds
of active CPU-gradient training**, under one of:

- `replay_control_stage1`: classification, real strengths, and old weights
  distillation, without explicit 3D vertex loss;
- `vertex_loss_stage1`: as above, plus directly grounded original Kotlin
  64-vertex physical deformation supervision;
- `ranking_loss_stage1`: vertex supervision plus ordered strengths within
  the same original source geometry/operation.

## Development selection MUST use actual native GLBs

The previous development objective measured an approximate displacement
proxy, which picked the wrong v11 candidate. New model selection requires
1,152 independent, exact-input-topology **development** Kotlin GLBs
(288 examples x 4 frozen model variants), real bidirectional 3D
surface Chamfer, preserved operation recognition and strength MAE.

A separate script `select_native_resolution_aware_v12.py` selects the
candidate based on those **actual development meshes** before any final
blind 3D evaluation. It cannot accept a validation-split audit. The final
1,152 **blind** Kotlin GLBs are then separately reconstructed and scored.
A strong selection on development is not enough to claim generalization:
the blind gate must also verify improvement, shape diversity, old skills,
per-form native topology, input segment/station integrity, strength
monotonicity and real physical error relative to undeformed input.

A completed GitHub workflow is not automatic acceptance. All genuine
experimental weights, original source SHA digests, development and blind
physical GLB evaluations are kept immutably for future training. Neither
experiments nor a gate pass alone install a neural model in Android.

## Reproducible source paths

- `app/src/test/java/com/assetwright/app/mini/DinoResolutionAwareBatchTest.kt`
- `app/src/test/java/com/assetwright/app/mini/DinoResolutionAwareDevelopmentTest.kt`
- `app/src/test/java/com/assetwright/app/mini/DinoResolutionAwareReconstructionTest.kt`
- `tools/mini_ai/native_resolution_aware_v12.py`
- `tools/mini_ai/native_resolution_aware_forward_audit.py`
- `tools/mini_ai/select_native_resolution_aware_v12.py`
- `tools/mini_ai/native_resolution_aware_acceptance.py`
- `tools/mini_ai/retain_resolution_aware_v12.py`
- `.github/workflows/forge-mini-v12-resolution-aware-source.yml`
- `.github/workflows/forge-mini-v12-three-physical-training-trials.yml`

All changes are in PUBLIC `tpylman90-ctrl/Assetwright`. Other user
repositories and previous saved experimental neural weights are untouched.
