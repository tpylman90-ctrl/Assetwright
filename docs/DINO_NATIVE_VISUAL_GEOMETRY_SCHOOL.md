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


## Verified first independent end-to-end study — November 5, 2026

[Successful native-geometry research workflow 41958833332](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41958833332)
exported and audited 252 unique original native GLBs and extracted frozen DINOv2
image features from 504 label-free two-view renders. It trained identical
teacher-free and DINO-supervised owned pixel students, then generated **36
student-predicted original Kotlin GLBs** and **36 constant-prior original Kotlin
GLBs**, all with valid independently audited manifold topology.

| Predeclared measurement | Teacher-free | Frozen-DINO supervised | Research requirement |
|---|---:|---:|---:|
| Correct chosen native operation (36 unseen cases) | 22.22% | **25.00%** | ≥55% |
| Absolute strength error (0–1 scale) | 0.23650 | **0.22310** | ≤0.20 |
| Joint pixel-to-native score improvement | — | **3.31%** | ≥3%, without other regression |
| Normalized real target-vs-predicted GLB vertex RMSE | — | **0.018296** | At least 10% better than constant |
| Constant-native-prior GLB vertex RMSE | — | 0.018660 | — |
| Forward native GLB error improvement | — | **1.95%** | ≥10% |

**Research verdict: candidate rejected for native-model promotion.** Frozen
DINO teaching produced a real, small measured benefit over the same pixel
student without the teacher, but both native accuracy and reconstructed
surface distance remain insufficient. A passing workflow means all operations
executed and all generated meshes were structurally valid; it does **not**
certify the learned model.

The exact source GLBs, teacher observations, research weights, per-case
predictions, real student/constant reconstructions, and independent forward
audit remain in [run artifact 13383839458](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41958833332/artifacts/13383839458)
for its configured 45-day retention. Research weights were not installed in
the Android app.

The next defensible curriculum should focus on **controlled before/after
visual comparisons**, retaining per-family baseline meshes and independent
fresh validation families. This isolates actual geometry changes in loft,
sweep, twist, recess and corner fullness from incidental camera, size and
lighting variations. The current official validation shapes have been
inspected and must not be reused as fresh evidence for retuned models.

## Combined release guard

`dino_native_acceptance_gate.py` and
`test_dino_native_acceptance_gate.py` now reconcile the visual and
forward-native reports by exact original target GLB hashes and by the actual
reported accuracy/strength metrics. A passing image benchmark alone cannot
create a validated combined checkpoint. Even if **both** independent research
gates pass, the model stays research-only and requires human visual approval
before any possibility of Android integration.
