# DINOv2 → Own Native Geometry: visual construction school

## Purpose

The earlier Zero-to-CAD + DINOv2 research established source-aligned
image-feature learning, but **both** expanded visual-distillation challenges
failed to beat their stronger nonvisual baseline. More image embeddings alone
did not give the Mini AI an ability to generate shapes.

This experiment deliberately changes the learning target. We give our OWN
from-scratch image student camera views of **real, independently audited Kotlin
GLBs**, with exact original construction operation and continuous strength.
DINOv2 Small is an optional, frozen training teacher; **the trained student
reads pixels without DINO at inference**.

## Full connected experiment

Workflow: `.github/workflows/dino-native-shape-school.yml`

1. `DinoNativeGeometrySchoolTest.kt` exports 252 ORIGINAL indexed, closed
   Kotlin AdvancedFormLab GLBs into environment-scoped research output. The six
   native operations are section loft, tangent sweep, section twist,
   superellipse profile, lower recess, and ribbed fairing.
2. Source families are **disjoint**: 180 training GLBs (six families, five
   strengths), 36 development GLBs (two families, three different strengths)
   and 36 validation GLBs (two new families and three fresh strengths).
3. `dino_native_visual_school.py render` audits real SHA-256 and mesh
   topology (boundaries, nonmanifold edges, triangle budgets, winding), then
   renders two label-free clay views per source using our CPU renderer.
   The views are side and front-three-quarter, crop out all naming overlays,
   and have fixed image dimensions. The workflow creates 504 images.
4. `dino_native_visual_school.py teach` extracts frozen DINOv2 Small
   vectors using the **same authenticated image evidence**. Nothing imports
   a third-party mesh or executes downloaded CAD scripts.
5. `dino_native_visual_student.py` creates the OWN 96-hidden-unit student.
   Its inputs are pooled image pixels/shading and occupancy only.
   Output heads predict (a) one of six actual native construction operations,
   (b) a continuous 0–1 strength, and (c) an auxiliary numeric DINO signature
   during **teacher-guided** training only. The otherwise identical
   teacher-free ablation uses the same data, seed and architecture.
6. A frozen model is chosen **on development families**, then scored once
   against the distinct 36-source validation family split. Training is
   evaluated against an operation-majority and constant-strength baseline.
   The research promotion threshold requires operation accuracy ≥55%,
   strength MAE ≤0.20, at least 3% joint-objective improvement over the
   otherwise identical no-teacher student, and no material accuracy/strength
   regression.
7. Independently of whether teacher transfer is accepted,
   `DinoVisualReconstructionTest.kt` executes **student-selected**
   operation and strength through ORIGINAL Kotlin AdvancedFormLab to produce
   36 new student GLBs, plus 36 constant-prior baseline GLBs.
   No target labels are used to select the student's generated operation.
8. `dino_native_forward_audit.py` compares real vertex/index buffers,
   checks all constructed GLBs for geometric validity, and calculates
   normalized source-vs-reconstruction vertex RMSE. The separate forward
   criterion requires at least 10% error improvement over constant native
   geometry and ≥55% selected-operation accuracy. Failure remains reported.
9. Research-only JSON checkpoints and all source-hashed GLBs are uploaded
   as 45-day GitHub Actions artifacts. The Android app does **not** load
   these student weights, nor is any teacher auto-promoted.

## Interpret results conservatively

Passing the visual-transfer comparison would show a narrow improvement in
recognizing six *known procedural operations* on our own synthetic source
forms. Passing the forward reconstruction audit would prove those predictions
can construct better-matching original GLBs on unseen parametric families.
Neither alone proves arbitrary image-to-3D, realistic materials, complex
multi-part continuity, vehicle aesthetics or generalized CAD mastery.

This is a genuine **visual-to-native-construction benchmark**, not merely a
visual-feature embedding test. It is still early research and needs a much
broader set of object families plus human multi-view reviews before any
release.

Existing validated native-geometry, branch, interface and composition
checkpoints remain untouched. No SceneForge, Forge-Core, Shattered Realms or
private AssetWright files are modified.

## Early failed curriculum, retained for accurate comparisons

The earlier 320/80-source four-view DINO study had validation error
0.04977960 versus 0.04875182 for a simpler operation-only ridge model.
The revised 480/96-source CAD literal study recorded 0.03660592 versus
0.03622425 for its operation-only baseline. Both were rejected;
their inspected validation examples are retired for further model selection.
