# Native three-operation composition — research milestone

This is the stage following the frozen 912-source, six-isolated-operation
study. The accepted model and Android generator remain untouched.

## What is implemented

The original Kotlin NativeCompositionLab generates a SINGLE joined,
closed hull using 3 distinct modeling commands selected from the six
known operations, in a fixed dependency order:

1. Width/haunch lofting and ribbed surface fairing
2. Rounded superellipse profile and lower-side recessed sculpt
3. Cross-section twisting and tangent-aligned curved sweep

This dependency ordering is engineering-defined: the learner selects which
three operations are active, and their continuous strengths, not arbitrary
permutations or user-described new techniques. The six operations generate
the real indexed source geometry; no foreign pretrained model emits meshes.

The new source batch has 1,120 original GLBs: 800 train examples
(10 independent dimension sets x 20 unique 3-of-6 combinations x four
strength variants), 160 new dimension-family evaluation GLBs and 160
different aspect-ratio-stress GLBs. Each is source-hashed. Every mesh must
pass the independent closed manifold / nondegenerate / outward-winding
and 2,112 triangle requirements.

## Owned constrained planning student

The small original CPU learner measures intrinsic geometry from actual
GLB ring vertices: cross-sectional radii, longitudinal profile variation,
centerline bend, local cross-section rotation, rounded diagonals, lower
surface asymmetry and second derivatives. It trains a regularized quadratic
inverse of these physical signals to six continuous control strengths.

The model then selects the 3 predicted operations with the largest learned
strength responses, under the fixed three-operation construction grammar.
Class/program labels and true control values appear ONLY as supervision,
not as model input features. It must beat a constant-strength baseline.

Evaluation gates, committed before seeing the new synthetic holdouts:

- >=93% exact three-operation set on ordinary new dimensions
- >=86% exact three-operation set on extreme aspect ratios
- <=0.065 / <=0.095 mean absolute active-strength error
- >=90% / >=80% recall for each learned operation
- >=0.12 / >=0.09 improvement versus 0.5-strength constant baseline
- 320 actual reconstructed Kotlin-native GLBs with closed topology
- <=.028 / <=.038 normalized mean source-versus-reconstructed surface RMS,
  with capped worst-case errors
- zero manifold defects, inverted winding, missing files or duplicate hashes

Acceptance is fail-closed, no weakening metrics to fabricate success.
Separate computer render previews contrast native source target and
student-controlled reconstructed shape, not a fake arbitrary CAD result.

### Limits

This is constrained 3-of-6 geometric composition, not general multistep
planning, model-derived cutouts or welded interface design, full G2
continuity, real-world cross-category transfer, or visual production
approval. Synthetic evaluation families become exposed once inspected;
any correction must retire those exact holdouts before a new claim.
Free Kotlin, Python, NumPy, Pillow, GitHub Actions only.

## First study immutability policy

The initial original study was launched under run 41833947043 at source commit bdca0462, with all evaluation families and thresholds frozen. The workflow has been switched to **manual historical reproduction only**, avoiding accidental repeated evaluation when fixing packaging or Android's optional research-test imports. For subsequent training changes, use a new study revision with new, unexposed source families. This does not change the running historical experiment or its metrics.

## First frozen 1,120-GLB composition study — measured result

Original source revision: bdca0462528731f98addf09578a891f697ac46ce
Original successful GitHub Actions:
https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41833947043

The original run generated and independently audited 1,120 connected source
GLBs (800 train + 160 new dimension + 160 new aspect-ratio holdouts).
The owned 3-of-6 inverse-program student selected **160/160 correct exact
three-operation sets** in each of the two synthetic holdouts, with
mean control error 0.001203248983945328 for new dimensions and
0.0005779200866829349 for aspect shifts. Constant 0.5 control baselines
on the same selected controls were 0.16495833377083333 and
0.16311251022916667. All eight frozen learner gates passed.

The student-driven commands were exported through our own Kotlin generator
as 320 fresh GLBs. Independent source-matched validation found zero
nonmanifold or inverted parts. Normalized mean vertex RMS to the original
source hull target was 0.00022382707300711615 for new dimensions and
0.00023969974242545963 for extreme proportions; all five native
forward-geometry acceptance checks passed. This is not an external
human-designed model challenge, but it proves the model can choose and
compose the known operations and recover precise strengths.

Sixty additional source-hashed clay and wire previews compare native
source shapes and Kotlin-built student reconstructions. The hulls still
look like smooth, varied cylinders/lofts, not production-quality hovercars.
No aesthetic acceptance has been claimed. The regular Android generator
and previous validated weights remain unchanged.

### Benchmark integrity

The original evaluation families cval1..4 and cshift1..4 have been
inspected and are retired from future pristine blind evaluations. The
original CI workflow is manual-reproduction only. The accepted weights,
full reports, source-hash provenance, and visual manifest are separately
archived from the exact successful Action artifact, without re-running
evaluation or retuning thresholds.
