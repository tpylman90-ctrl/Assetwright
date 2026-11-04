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
