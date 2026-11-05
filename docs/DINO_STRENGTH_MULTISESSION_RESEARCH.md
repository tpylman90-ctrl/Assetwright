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


## Verified first 16-session results — November 5, 2026

[Successful GitHub Actions run 42051616384](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/42051616384)
passed source-integrity tests, 974 original Kotlin GLB exports, 1,948
fixed-camera renders, frozen DINOv2 numerical extraction, ALL 16
independent training sessions, 192 real Kotlin GLB reconstructions and
the independent source-hash/topology/forward-vertex audit.

[Complete research evidence artifact 13426857968](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/42051616384/artifacts/13426857968)
contains source meshes, rendered examples, numerical frozen teacher
features, eight-session histories, held-out per-operation metrics,
candidate research weights, 192 independent reconstruction GLBs and
the combined reject/pass decision.

| Fresh 96-case heldout measure | Eight-session teacher-free | Eight-session DINO-guided |
|---|---:|---:|
| Correct original native modeling operator | 82/96 = 85.42% | **86/96 = 89.58%** |
| Continuous native strength MAE (0–1) | **0.142133** | 0.146586 |
| Actual source-vs-new-GLB normalized vertex RMSE | **0.00497249** | 0.00497336 |

The true unchanged-original native shape has mean normalized vertex
RMSE 0.01432141. The guided student reduces that error by **65.27%**,
with 192 independently generated GLBs passing the source hash and
structural topology gates. This improvement belongs to the OVERALL
paired shape-training methodology, not to DINO alone.

The frozen DINO teacher improves operator classification by 4 additional
correct cases on the identical source benchmark, but it does NOT improve
strength estimation or final mesh distance over the equivalent
eight-session teacher-free student. Its strength MAE was 3.13% WORSE
than the teacher-free control, and its normalized vertex RMSE was
approximately 0.017% WORSE. Six of 72 monotonic ordered-strength
comparisons remained reversed, versus the strict limit of four.

**Final disposition: research_candidate_not_approved.** The
classification, overall strength-MAE and unchanged-original-GLB
improvement gates passed. However teacher-specific strength improvement,
teacher-specific native vertex improvement, and monotonicity gates
FAILED. No Android weights were updated and no validated combined
research checkpoint was emitted.

Development-only session selection chose seed 5419 for the teacher-free
student and seed 4027 for the DINO-guided student, both at **epoch 20**
of a maximum 260-epoch curriculum. This is useful evidence that simply
increasing epochs is not necessarily helpful; the best independent
development checkpoints were earlier. The first historical 54-case
study had strength MAE about 0.242, but because the holdouts and
curriculum both changed it is NOT scientifically valid to attribute
the new 0.147 result to more sessions alone.

The final bs_blind01…04 validation families and four held-out strength
values are now exposed. Do NOT use them as an unseen validation
cohort for any subsequent adjustment. The next scientific experiment
needs new holdout families and should investigate ordinal calibration,
class-specific response sensitivity and why frozen DINO features
improve class recognition but not physical effect size.

All external generators remain research-only; only OWN Kotlin
AdvancedFormLab constructs the source and reconstructed meshes.
