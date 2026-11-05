# AssetWright Mini AI — source-native before/after geometry curriculum

## Objective and previous benchmark

The prior 252-GLB DINOv2 study showed a small increase in heldout operator
recognition from 22.2% to 25.0% and a 1.95% improvement in native mesh
reconstruction error versus an unchanged constant. It was correctly
rejected. Better image embeddings alone are not a proof of geometry learning.

The new study holds the original *before* shape fixed, applies one genuine
Kotlin transformation at an exact strength, and teaches our Mini AI:
**what changed, where it changed and which construction operator caused it.**

Frozen DINOv2 Small supplies numeric difference supervision, not geometry.
The original AssetWright AdvancedFormLab generates ALL native target and
student-predicted GLBs, with no third-party 3D generative model.

## Independent original source batch

The Kotlin test DinoDeltaGeometryBatchTest.kt exports **486 original indexed,
closed, source-hashed GLBs**:
- 18 baseline forms (one per source family)
- 360 training changes (12 families × 6 operations × 5 strengths)
- 54 independent development changes (3 different families × 6 × 3)
- 54 untouched validation changes (3 new families × 6 × 3)

Operations: SECTION_LOFT, TANGENT_SWEEP, SECTION_TWIST,
SUPERELLIPSE_PROFILE, LOWER_RECESS, RIBBED_FAIRING. These are native,
single connected-shell operations, not real Boolean cutouts, CAD-grade
NURBS, or complete cars. Strength levels and family dimensions are
disjoint between all three partitions. Validation examples become exposed
development evidence after this experiment and must not be reused
as pristine future benchmarks.

## Real source-verified morphology and camera-aligned images

dino_delta_school.py audits original mesh SHA256, manifoldness, triangle
budget, signed volume and physical source values. It calculates six native
shape descriptors directly from actual indexed GLB coordinates and the
before-to-after vertex displacement. These descriptors are auxiliary
supervision, never supplied as inference input.

Every shape within one source family uses the EXACT same orthographic
camera position and scale, bounded by the union of its source meshes.
Each before and after image receives the same lighting and neutral
material with no text labels embedded in pixels. The 486 GLBs produce
972 two-view images. Every PNG is SHA256-aligned to its original source
GLB and camera role.

DINOv2 encodes both source and target views; the *difference* of these
frozen embeddings becomes a training-only visual teacher for the
original Mini AI.

## Three original student comparisons

dino_delta_student.py trains three separate, randomly initialized CPU
models using the same architecture, labels, seeds, and original native
training examples:
1. After-only image student, with before/after delta channels masked.
2. Paired before/after student with measured geometry-change supervision,
   but no DINO.
3. Paired before/after student with identical native geometry supervision
   PLUS the frozen DINOv2 difference teacher.

Student inference accepts only pixels, not filenames, source construction
metadata, original GLB vertices, or the teacher model. It outputs
a native operation and 0–1 strength. Model selection uses only 54
development-family examples; the 54 new validation examples are scored
once after freezing the models.

Visual research gates: at least 60% operator accuracy, strength error
no more than 0.18, paired inputs improve joint loss by 5% versus
after-only, and frozen DINO improves by 2.5% versus the paired-only
model without material prediction regression.

## Independent native geometry proof

DinoDeltaReconstructionTest.kt executes our students' own frozen
native operator and strength proposals using actual Kotlin
AdvancedFormLab. It reconstructs 54 teacher-free and 54 DINO-guided
original GLBs, without using the target operation or target strength
as generation inputs.

dino_delta_forward_audit.py independently measures original target
versus real student and unchanged-baseline indexed vertex buffers,
source hashes and topology. A successful native reconstruction must
beat an unchanged source by 10% and the paired teacher-free model by 2%
on mean normalized vertex error, with the same strict operator and
strength limits.

dino_delta_acceptance.py cross-checks original validation source GLB
hashes, independent operation/strength scores and real GLB geometry.
Both visual and 3D geometry gates MUST pass before a research checkpoint
is eligible for HUMAN visual review. Nothing is automatically deployed
to Android or accepted as a broad shape generator.

## Operation and evidence limits

A passing result proves only a narrow, controlled ability to recover
six already implemented single-shell transformations on heldout
parametric families. It is not a claim about arbitrary image-to-3D,
detailed game objects, multi-operation creativity, accurate NURBS,
real-world topology or aesthetic quality.

Research stays in the public AssetWright repository. Existing signed
Android production behavior, accepted research checkpoints, and all
unrelated repositories remain untouched.

Workflow: .github/workflows/dino-before-after-native-learning.yml.
The run preserves source GLBs, 972 camera images, source hashes,
teacher features, student candidates, actual student GLBs and independent
reports for 30 days via GitHub Actions artifacts.


## First complete experiment — verified November 5, 2026

The initial source-protected study completed successfully in
[GitHub Actions run 42040669117](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/42040669117).
The exported original meshes, camera-aligned images, frozen teacher,
candidate weights and independent native GLB reports are archived as
[research artifact 13421515288](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/42040669117/artifacts/13421515288).

All 486 source GLBs, 972 source-aligned render images, and 108 student
reconstructed GLBs passed the recorded source hash and topology checks.
The initial before/after curriculum showed a clear benefit over
single-image recognition, measured once on 54 disjoint original
validation examples.

| Held-out metric | After-only | Before/after without DINO | Before/after with DINO |
|---|---:|---:|---:|
| Operation accuracy | 44.44% | 79.63% | 79.63% |
| Strength MAE (0–1) | 0.26796 | 0.24162 | 0.24163 |
| Classification + strength joint loss | 2.58037 | 1.30149 | 1.27600 |
| Mean native normalized vertex RMSE | Not reconstructed | 0.009883 | 0.009787 |

An actual unchanged-original-native baseline had normalized target
vertex RMSE 0.014969. The guided student reduced that by **34.62%**
on actual, independently audited source-owned GLBs. DINO supervision
improved the paired student's joint prediction loss by **1.96%**
and native reconstruction error by **0.97%**. These improvements are
real but small compared with the strong paired non-DINO baseline.

**Promotion decision: rejected.** Native operator accuracy surpassed
the 60% gate, and before/after input improved prediction by 49.56%
relative to after-only. However strength MAE was 0.24163 rather than
the required ≤0.18, DINO-specific joint improvement was 1.96% rather
than ≥2.5%, and DINO-specific geometric improvement was 0.97% rather
than ≥2%. No thresholds were weakened and no Android weights were
modified. This is validated *evidence of visual-change learning*, not
a production-ready 3D generation model.

The 54 originally fresh validation source cases (bdhold01..03) are now
**inspected, exposed and retired** from independent generalization
claims. Any subsequent strength-calibration, teacher-loss or model
change must reserve genuinely new source families and strength
values for its final blinded comparison. Historical reruns of the
same first experiment may verify reproducibility, not provide new
unseen-test evidence.
