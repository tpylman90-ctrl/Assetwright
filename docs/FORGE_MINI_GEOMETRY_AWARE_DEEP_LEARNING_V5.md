# Forge Mini — Geometry-Aware Deep Learning v5

## Evidence that motivated this stage

The first REAL continual-training run completed 32 minutes of active CPU
optimization and retained all new weights permanently. The preserved
v4 results are archived at
training/learning_runs/strength_continual_v4_42122117108/ .

The source-disjoint 96-shape blind result was:

| Test | Retained original v3 | Continued v4 |
| --- | ---: | ---: |
| Operation recognition | 87.50% | 88.54% |
| Continuous operation strength MAE | 0.138326 | 0.123813 |
| ACTUAL Kotlin GLB vertex RMSE | **0.00499627** | 0.00509933 |

That is 10.49% less strength MAE but 2.06% WORSE real geometry.
The v4 candidate was correctly marked as rejected, and its weights
remain in research storage. Crucially, its **504 correct original
training labels and meshes remain usable as OLD TRAINING REPLAY DATA**.
These are not its previously exposed 96 blind shapes.

## What is different in v5

Each candidate starts from the exact source-hashed retained ORIGINAL
160,938-parameter native neural student saved under
training/knowledge/native_strength_teacher_free_42080318206/ .
The first layer is mathematically rebased to preserve initial
predictions under updated image statistics.

The images have no operation names or geometry labels. They are
16x16 paired before/after fixed-camera image features from original
Kotlin GLBs. No pretrained DINO model or outside mesh generator is
used in this study.

The real native physical supervision samples **64 corresponding
indexed vertices × 3 coordinates** on each training source pair.
For each training family and operation, a native full-strength
displacement basis is measured directly on original GLB vertices,
relative to the same original baseline. The six operation-specific
vector fields are **only training targets/loss surfaces**. A small
original PyTorch student predicts operation and strength from image
pixels. We use the predicted class probabilities and strength outputs
to approximate a full 192-dimensional 3D displacement field and
backpropagate a smooth-L1 3D vertex error directly to both neural
heads. A second teacher-forced vertex loss supervises strength within
the known original operation.

The differentiable basis is a **surrogate**, not the exact Kotlin
mesh generator. It approximates nonlinear changes with a physical
full-strength template. It does not supply the true operation or
vertices at inference. Acceptance is determined separately by the
actual native Kotlin-generated GLBs and full source-matched indexed
vertex RMSE.

## All prior useful training lessons retained

The source-hashed REAL training inputs are:
- 672 v3 training-only examples from 16 original source families;
- 504 v4 training-only examples, valid even though the v4 candidate's
  *weights* were rejected;
- 504 new v5 training examples from 12 new families.

Total: **1,680 real Kotlin geometry training examples**.
Previous development and blind cohorts are excluded from gradient
training and case sampling. The v5 development cohort is a new 96
examples across four distinct families. The v5 blind cohort is a
different new 96 examples across four other distinct families,
with disjoint training, development and blind strength values.
The v5 curriculum contains 716 entirely new original native GLBs.

## Three fair CPU training arms

Exactly the same starting weights, source images, source labels,
batch composition, optimizer family and time budget per session:

1. REPLAY ONLY control: prior neural model + 1,176 previous valid
   training examples + 504 fresh examples. Includes the same
   old-model retention distillation as every other arm.
2. GEOMETRY SUPERVISION: above plus differentiable 64-vertex 3D
   native displacement losses for both operator probabilities and
   continuous strength.
3. GEOMETRY + HARD EXAMPLE MINING: same geometry losses, with
   importance-based source sampling from REAL operation/strength
   mistakes. 40% of examples remain uniformly sampled so well
   learned operations are not forgotten. Wrong predictions are
   NEVER treated as correct labels.

Two independent seeds per arm = six real CPU optimization
sessions, with **1,800 seconds of measured optimizer time** in
total. Each saves its best fresh-DEVELOPMENT-only checkpoint.
The method is selected on development data only, with old TRAINING
retention gates. All three methods and the parent get blind
scores exactly once after method and seed/step selection.

The original Kotlin AdvancedFormLab rebuilds **384 actual native
GLBs**, one for every (96 blind source geometries) × (retained
parent, replay control, geometry supervised, and geometry + hard
mining). An independent verifier checks every source GLB hash,
student GLB hash, topology, classification, strength and actual
normalized vertex distance. This prevents a loss improvement in
a Python surrogate from being called a 3D modeling improvement.

## Truthful checkpoint promotion

For a candidate to be called eligible for HUMAN research review:
- earlier training operation accuracy must remain within 2 points,
  and earlier continuous-strength MAE within +0.015;
- heldout operation accuracy cannot drop >~1 point and strength
  MAE cannot get significantly worse;
- REAL Kotlin GLB error must improve by at least 2% versus the
  preserved parent;
- a geometry-aware arm must improve actual error by at least 1%
  versus the equal-budget replay-only control;
- it must beat unchanged geometry by at least 10%, and not reverse
  more than 4 heldout adjacent strength-order comparisons;
- complete source, model, and GLB SHA256 evidence is required.

A green GitHub Actions run means genuine computation ran, not
that the student's model was more intelligent or accurate.

All 3 trained weights, their original prior lineage, training
metrics, and actual 3D results are committed permanently to
training/learning_runs/geometry_aware_v5_<github_run_id>/ ,
regardless of positive or negative conclusion. We do not
overwrite previously verified weights, nor automatically load
unapproved research weights into Android.

## Status and scope

Code:
- tools/mini_ai/native_vertex_supervision.py
- tools/mini_ai/native_geometry_aware_student.py
- tools/mini_ai/native_geometry_aware_forward_audit.py
- tools/mini_ai/native_geometry_aware_acceptance.py
- tools/mini_ai/retain_geometry_aware_learning.py
- .github/workflows/forge-mini-geometry-aware-v5.yml

This tests generalization among six ORIGINAL SINGLE-OPERATION
advanced geometry lessons. It is NOT yet evidence of full
multi-component, multi-operation procedural CAD program inference,
unrestricted text-to-3D, hidden-camera shape completion, or
production-quality game meshes. Compound modeling programs are
the NEXT curriculum, after the geometry-aware validation.

Only the PUBLIC tpylman90-ctrl/Assetwright repository is changed.
The private repository, Forge-Core, SceneForge and Shattered Realms
are untouched.
