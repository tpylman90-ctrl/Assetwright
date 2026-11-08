# Forge Mini v10 — Continue Physical Geometry Learning

## Goal

Forge Mini v9 improved recognition of original 3D archetypes on a held-out
source set, but the reconstructed meshes were still physically less
accurate than simply leaving the correct original source form unchanged.
The next research milestone is not another shape-label classifier. It is
better prediction of original native modeling operations and continuous
deformation strengths **on actual original geometry**, without undoing
earlier neural learning.

## What is actually reused

V10 initializes the EXACT 26,668-parameter v8 `hard_physical` native
operation/strength adapter from:
`training/learning_runs/form_fidelity_v8_42396471403/`.

This v8 adapter was the winner selected on v8 development data, **but
it failed research promotion**, so v10 treats it explicitly as a
research-only warm start. It is not represented as an approved mobile
model. V10 also freezes the original v6 6-operation neural model, the
v7 hard-form feature network used by the v8 adapter, and the v9
development-selected `replay_continuation` form recognizer.

Those source weights are checked against permanent SHA256
`learning_history.json` records; the exact v7/v9 normalization is
verified. All newly trained adapter weights are saved separately.
**None of the prior checkpoints is overwritten or installed on Android.**

## New original 3D sources, not recycled validation

V10's Kotlin `DinoGeometryMasteryBatchTest` generates 1,808 original
source GLBs with eight true NativeDiverseFormLab archetypes and different
native tessellation. The training, dev and blind groups never share
families or strengths:

- 48 new training families × 6 operations × 4 strengths = 1,152
  original before/after geometry lessons;
- 16 novel development families × 6 operations × 3 strengths = 288
  development-only comparisons;
- 16 **unseen blind** families × 6 operations × 3 other strengths = 288
  final checks;
- 80 unmodified source-form baseline meshes.

Within each dimensional template, all eight shapes receive exactly the
same length, width, height and topology so a form cannot be identified
by proportions or tessellation alone. Every original GLB and its
rendered source views is tied to SHA256 provenance. Another 1,152
**old v8 training-only** transformations are replayed to protect
previously learned geometry; previously exposed v8 dev/blind examples
are excluded from optimization.

## Three fair 30-minute real neural experiments

Each recipe starts from the SAME original retained v8 adapter weights
and sees the SAME source curriculum, with independent seeded
300-second active CPU-gradient sessions:

1. `warm_replay` — source-labeled operation and strength learning,
   with retained v8 predictions rehearsed to prevent forgetting.
2. `vertex_geometry` — same, plus a differentiable, original Kotlin
   mesh-displacement objective on 64 corresponding native 3D surface
   samples, using the true operation and measured form-specific
   deformation basis.
3. `geometry_rank` — source-labeled 3D loss plus a monotonicity loss
   enforcing progressive deformation response within the SAME
   original source form and operation. It prioritizes hard original
   geometry cases without suppressing basic forms.

All three methods use 1,800 total seconds of measured active
optimization, not a sequence of ephemeral tests or arbitrary
run-time claims. Every condition's checkpoints and exact seeds are
recorded; the preferred recipe and seed are chosen on newly generated
**development** forms only. No v10 blind-case feedback can be used to
change weights, pick checkpoints, or retroactively switch recipes.

## Physical GLB gate

The frozen v9 model alone selects the geometric form, and the
baseline/new adapters choose the operation and deformation strength.
A separate Kotlin test generates 1,152 real GLBs for the same 288
original blind transformations (four model conditions). Its 3D audit
uses actual normalized bidirectional surface Chamfer distance between
the independent GLB triangle surfaces, not 2D or training loss.

Evaluation also reports form diversity across eight native
archetypes, real output triangle topologies, operation accuracy,
strength MAE, strength-order reversals, 3D error against the
unchanged correct source mesh, and old-skill retention. Research
eligibility requires a predeclared improvement over the exact
warm-started v8/v9 model while meeting those constraints.

**A green GitHub workflow is not evidence of model improvement.**
All honest failures preserve original learned weights, lineage and
evaluation. No experimental weights are automatically deployed.

## Entry points

- `app/src/test/java/com/assetwright/app/mini/DinoGeometryMasteryBatchTest.kt`
- `tools/mini_ai/native_geometry_mastery_v10.py`
- `app/src/test/java/com/assetwright/app/mini/DinoGeometryMasteryReconstructionTest.kt`
- `tools/mini_ai/native_geometry_mastery_forward_audit.py`
- `tools/mini_ai/native_geometry_mastery_acceptance.py`
- `tools/mini_ai/retain_geometry_mastery_v10.py`
- `.github/workflows/forge-mini-v10-native-source-school.yml`
- `.github/workflows/forge-mini-v10-continued-geometry-learning.yml`

Only the public `tpylman90-ctrl/Assetwright` repository has been changed.
