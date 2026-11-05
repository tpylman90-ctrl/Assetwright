# AssetWright — Eight-seed native strength calibration curriculum

## Research question

Earlier frozen-DINOv2 before/after teaching raised held-out native
operator recognition to 79.63% on the first 54-case cohort, but
continuous strength error remained 0.24163 on a 0–1 scale.
This fresh experiment asks whether independent sessions, more strength
levels, and operation-specific strength heads improve both numerical
predictions AND the actual original Kotlin reconstructed GLBs.

## New original, source-disjoint dataset

DinoStrengthGeometryBatchTest.kt creates:
- 18 original training families × six native operations × seven
  strength values = 756 training transformations.
- Four new development families × six operations × four strength
  values = 96 independent development examples.
- Four new blind families × six operations × four OTHER strength
  values = 96 independent validation examples.
- 26 untouched baseline GLBs, one per family.

That totals **974 original Kotlin native GLBs** (948 transformed and
26 unchanged baselines) and 1,948 source-hashed, camera-aligned views.
Previously inspected bdhold families are not reused, and none of the
training, development and blind strength levels coincide.

Set ASSETWRIGHT_DINO_STUDY=strength_v2 explicitly; historical
delta_v1 remains the default. DINOv2 Small is frozen and supplies only
teacher feature differences. The own student never requires DINO at
inference and only AssetWright's original Kotlin generator builds
final mesh geometry.

## Sixteen complete research training sessions

dino_strength_student.py trains **eight independent seeds for each of
two matched groups**, for 16 actual sessions total. Each session runs
a bounded maximum of 260 CPU training epochs:

1. Eight entirely owned original image students, without frozen DINO.
2. Eight identically initialized counterparts, with additional frozen
   DINO visual-difference teaching.

All sessions learn six operation-specific continuous strength heads,
with a three-stage curriculum: geometry operation recognition,
continuous control calibration, and monotonic-effect refinement.
A physical strength-ordering constraint penalizes predictions whose
estimated strength falls as an actual source modification increases
within the same family and native modeling operation.

Only independent development families select the winning seed and
epoch for each group. Then both models are frozen and evaluated ONCE
on never-inspected validation source families. No trial or
hyperparameter selection is permitted on the final blind cohort.
After inspection, the blind cohort is retired for future tuning.

## Actual native shape reconstruction

DinoStrengthReconstructionTest.kt makes 192 original Kotlin GLBs
from the two independently predicted native operators and strengths,
without copying the true operation/strength from validation.
dino_delta_forward_audit.py independently audits source hashes,
indexed vertices, topology and normalized vertex error.

The strict combined research gate additionally requires:
- at least 65% native-operation prediction accuracy;
- overall strength MAE at most 0.18 and per-operation MAE at most 0.30;
- at least 0.008 absolute strength MAE improvement versus the eight-
  session teacher-free comparison;
- at least 10% better original vertex error than leaving the source
  shape unchanged, and 2% better than the teacher-free student;
- no more than four wrong-way transitions among 72 ordered, held-out
  strength comparisons;
- identical source GLB SHA hashes and all real meshes structurally valid.

These are research gates, never production deployment permissions.
Even if all pass, a candidate awaits a separate human multi-view
approval. No Android weights or accepted older checkpoints change.

## Review

Workflow: .github/workflows/dino-strength-multisession.yml.
It stores all source-owned GLBs, frozen teacher signatures, source
camera renders, 16 training-session development results, blind
metrics, candidate weights, 192 forward reconstructions and
release-blocking disposition in a 30-day GitHub Actions artifact.

A green workflow means execution and integrity passed. See the
final_research_disposition.json to check whether actual learning
quality passed. The student is not an arbitrary image-to-3D model.

All edits are confined to the public AssetWright repository; no
SceneForge, Forge-Core, Shattered Realms or private repo changes.
