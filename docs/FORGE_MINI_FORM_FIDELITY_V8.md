# Forge Mini v8 — learn form-conditioned physical geometry

## Why v8 is different from another shape-classification run

The full original v7 three-view study completed 1,800 seconds of real
CPU learning and 1,536 native GLB checks. A dev-selected three-view
model recognized 75% of its 16 unseen baseline forms and achieved
6.27% lower true 3D surface error than its previous experimental parent.
It FAILED the research promotion gate.

The previously fixed **hard-form** training method achieved 87.5% shape
recognition and approximately 24.6% lower 3D surface error on the
already-inspected v7 blind cohort, but that arm was not chosen on v7
development data and may not be promoted retrospectively.

v8 treats that hard-form encoder as a clearly labeled EXPERIMENTAL
FROZEN baseline on an entirely new, untouched v8 source cohort. It
does not claim v7 hard-form weights were an approved successor.

Previous old operation/strength network remains frozen too; new learning
occurs in a SMALL original form-conditioned residual correction network,
which is fed representations from both of these existing networks.
The actual 3D mesh is ALWAYS made by the native Kotlin generator.

## Completely new and balanced original 3D form families

The source lab now builds 1,808 new original Kotlin GLBs, containing:
- 48 training form families (6 physical templates x 8 archetypes),
  with 6 native operators x 4 strengths = 1,152 changes;
- 16 new development families (2 templates x 8 archetypes), with
  6 operators x 3 strengths = 288 controlled changes;
- 16 untouched blind families (2 more templates x 8 archetypes),
  with 6 operators x 3 distinct strengths = 288 changes;
- 80 unchanged original baseline form geometries.

Every form gets exactly the SAME length, width, height and tessellation
at a given physical template, so the network cannot cheat using
dimensions as class labels.

The eight original native archetypes are spindle, wedge, box module,
barrel, arch, blade, canopy pod, and truss beam. Train/development/blind
families and strengths are separate from all previously inspected
bd, bs, bm, bc, bg, mf and si holdout sources.

The new data is taught using actual original 16x16 paired
before/after operation views and 32x32 SIDE, FRONT, TOP undeformed
form-identity views, all with original GLB SHA256 provenance.

## Actual continual training — not resetting prior students

The original v6 trained action model, and original v7 hard-form identity
model, load from their immutable source-hashed safetensors research
archives. Both are completely frozen.

A NEW original 2-layer residual adapter takes features from the old
action and form networks and learns shape-conditioned corrections to
operation scores and continuous strengths. Its weight heads initialize
at ZERO so initial outputs match the previous model exactly.

1,200 original v7 TRAINING-only transformation examples provide replay
and preserve the old skills. No old v7 development or blind samples
enter gradient training. 1,152 NEW original v8 Kotlin transformations
teach physical variations among all eight different shapes.

Six independent full CPU optimizer sessions spend 1,800 measured seconds
across three equal-budget research recipes:

1. `supervised_replay` — correct operations/strengths + old-prediction
   retention, without explicit surface supervision.
2. `physical_replay` — above plus 64 matching real original Kotlin
   3D source vertices (192 XYZ coordinates) and differentiable
   operation-specific vertex deformation loss.
3. `hard_physical` — physical loss plus sampling based on correctly
   labeled mistakes, with additional exposure to twist and confusing
   spindle/truss forms. A 40% uniform floor prevents mode collapse.

New development examples and prior TRAINING retention select one
checkpoint per recipe and the preferred method. The truly new blind
cohort cannot choose the model retrospectively.

## True physical 3D evaluation

The original Kotlin NativeDiverseFormLab builds **1,152 actual GLBs**
for 288 new blind transformations, one from each of the frozen parent
and three independently trained residual adapters.

The predicted FORM is supplied by the same frozen research identity
head in all four conditions. Each model predicts its own operation
and continuous strength; the original native Kotlin generator
assembles the GLB. Correct target form/operation/strength labels
are never passed to the inference code.

A separate source-hash and topology checker scores physical surface
difference by normalized symmetric 3D Chamfer distance. Same-index
vertex RMSE would be invalid because different form archetypes and
rendered tessellations legitimately vary in vertex count.

Research eligibility requires: real 3D error improve at least 8%
vs the exact frozen prior, physical error no worse than the unchanged
correct source form, better actual geometry than the equal-budget
replay arm for the physical methods, improved heldout strength
calibration, form and operation preservation, original mesh diversity,
monotonic strengths, 1,152 valid GLBs and exact original source hashes.

A *green workflow* proves code executed; it does not by itself imply
knowledge gain. Rejected candidates are retained honestly with their
actual neural weights, lineage and physical GLB evidence. No weights
are ever automatically promoted into Android.

## Relevant sources

- `app/src/test/java/com/assetwright/app/mini/DinoGeometryFidelityBatchTest.kt`
- `tools/mini_ai/native_form_fidelity_v8.py`
- `tools/mini_ai/native_form_fidelity_forward_audit.py`
- `tools/mini_ai/native_form_fidelity_acceptance.py`
- `tools/mini_ai/retain_form_fidelity_v8.py`
- `.github/workflows/forge-mini-form-fidelity-v8.yml`

Only PUBLIC tpylman90-ctrl/Assetwright has been changed.
Private AssetWright, Forge-Core, SceneForge and Shattered Realms
remain untouched.
