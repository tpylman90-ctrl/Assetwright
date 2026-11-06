# Forge Mini v6 — Eight Real Forms, Not One Generic Shape

## Why this iteration exists

Previous research improved original 3D operation/strength prediction,
but the datasets were largely variants of one 602-vertex ellipsoid-like
tube. High accuracy there does not establish the ability to build a
diverse library of game assets. This study changes the base shape,
its silhouette and its topology, and requires the model to PREDICT
which shape family an original paired image depicts.

## Eight different original procedural archetypes

Original Kotlin NativeDiverseFormLab now constructs:
1. Spindle — tapered smooth fuselage
2. Wedge — unequal planform and cross section toward each end
3. Box module — squared/box-like cross section
4. Barrel — expanded center, tighter ends
5. Arch — raised/arched longitudinal centerline
6. Blade — asymmetric, slender tapered body
7. Canopy pod — distinct upper crown and smaller sides
8. Truss beam — angular/faceted structural ribs

Each is still a single closed original mesh, not full CAD or a
multi-part vehicle. The source uses different longitudinal and cross
section rules, not merely changed overall length/width/height.

Original indexed mesh topology varies too: 602, 802, 1058 and
1322 vertices, depending on native ring/segment counts. Source
sha256, positive volume and manifold connection checks still apply.

## Training/holdout structure

The research study generates 1,088 original Kotlin source GLBs,
including 1,056 before/after changes, 32 archetype-specific unchanged
baselines, and 2,176 reference view renders.

Training: 16 completely new families, 2 per each of the 8 forms;
6 operations and 7 strengths each = 672 examples.

Development: 8 completely different families, 1 per form; 6 operations
and 4 strengths each = 192 examples.

Blind: 8 new families, 1 per form; 6 operations and 4 OTHER strength
values each = 192 examples. The blind topology is the unseen 40x32
vertex-grid and was not used in training or model selection.

Earlier inspected validation families do not re-enter training.
The old 672 v3 + 504 v4 + 504 v5 TRAINING-only lessons provide
1,680 previously correct replay examples. 2,352 combined old+new
native training pairs now contribute to learning.

## REAL model skill transfer

The verified original 160,938-parameter student is still the source
of the existing core/operator/strength/physical model weights.
A NEW, original nine-class form classification head learns which
of the eight archetypes appears in the source views; a ninth
legacy-shell label preserves discrimination from older examples.

Three conditions have the same original source data, 30 total
minutes of genuine CPU gradient optimization and two seeds each:
- Balanced form-class replay with explicit coverage of all archetypes
- Differentiable native Kotlin 64-point 3D vertex supervision
- Native geometry supervision and hard-example sampling using
  correct training labels plus a uniform exposure floor

Both form and operation labels are supervised, but the student's
forward inference input is only paired source images. It cannot
silently inspect correct blind form/operation/strength labels.

The best checkpoint and method are selected on DEVELOPMENT only.
Eight new original blind geometry families are revealed exactly
once after selecting methods and all six session checkpoints.

## Real, non-generic GLB forward verification

The previous model predicts a legacy generic shell; the v6 students
predict their OWN source form, operation and strength. Each output
generates its actual original Kotlin native geometry, without
supplying the correct target archetype or target topology.

A total of 768 real Kotlin GLBs are produced on the 192 blind cases.
Because geometric forms have different mesh topology, they cannot
be compared fairly using same-index vertex RMSE. The independent
3D evaluator uses deterministic triangle-centroid samples and
bidirectional normalized surface Chamfer distance instead.
Each GLB and every source are checked by SHA256 and structural
closed mesh audit.

The predeclared acceptance gate checks: >=75% archetype accuracy,
all 8 archetypes genuinely predicted, at least 4 different output
topologies, <=12/192 legacy-generic outputs, at least half of the
24 examples in EACH form correct, actual physical surface gain,
previous neural skill retention, and ordered-strength stability.
Geometry-loss experiments also must outperform the equal-budget
replay control on actual 3D surface distance.

Green GitHub Actions execution does NOT itself constitute a model
improvement. Research failures are preserved as source-hashed
original neural checkpoints. Only a gate-eligible result can move to
HUMAN review, never automatic Android installation.

## Android geometry skill lab

The Android Forge Mini native geometry lab also now shows all eight
original forms. You can inspect the live 3D shape, select one of six
transformations and a strength, export its original GLB, and approve
the whole FORM + OPERATION + STRENGTH for future prompts.
Previous on-device memory schema is read without losing old lessons.
The device-side form matcher is transparent vocabulary and approved
memory, NOT a deployed research neural checkpoint.

## Boundaries

This is still a supervised single-form/single-operation neural
student, not arbitrary text-to-3D or independent multi-part CAD.
Only public tpylman90-ctrl/Assetwright has been changed. No paid
mesh generators, DINO dependency, or unrelated project mutations.

Workflow: .github/workflows/forge-mini-multiform-v6.yml
