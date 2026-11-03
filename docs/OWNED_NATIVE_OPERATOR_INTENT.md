# AssetWright — first OWNED learned three-operation native construction planner

## What is implemented
Our three research-only native operations:
1. `recess_rear_socket`: a **closed, connected** rear-hull blind cavity,
   restricted to one rear propulsion engine.
2. `sculpt_cockpit_shoulder`: an independently measured upper hull
   curvature/width transition, built directly into the existing body mesh.
3. `loft_rear_nacelle`: a six-station rear-drive fairing loft. The
   shroud is currently a **separate intersecting shell**, not Boolean-welded
   with the body.

All operations accept strictly bounded 0..1 native strength. The default
design controls remain zero and preserve the original mobile experience.

## How the OWN Mini AI learns
`native_operation_intent_student.py` trains a small, original, sparse text
model using handwritten *native construction instructions and exact control
strength labels*, with held-out instruction templates and vehicle names.
It predicts both operation and continuous strength. Inference does not
require DINOv2, Zero-to-CAD, Tripo, or any external generator. No source
meshes are consumed or copied.

Why this is an **honest separate dataset**: Zero-to-CAD provides CAD operation
programs, not our hovercraft instruction sentences or their strength
parameters. We have not mislabeled it as a prompt-to-operation corpus.
The previously verified CAD-grammar and DINOv2 visual-feature students
provide research foundations for operator semantics and future visual
supervision. They are **not yet directly fused into this instruction model**.
The operation allowlist and engine-count gate are authored engineering
constraints. No executable downloaded CadQuery code runs in the app.

## Verified narrow held-out development benchmark
[GitHub Actions run 41680541276](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41680541276):

- 135 original, authored operation+strength training instructions
- 36 held-out instructions from 6 different instruction-template groups
- 100% correct selected operation, 0 abstentions
- mean 0.055407 absolute strength error on a 0..1 scale
- majority-class selection baseline 33.3%, constant-strength baseline MAE 0.20

**Caution:** Those templates are synthetic and limited to three explicitly
named vehicle operations. Lexical feature normalization was adjusted after
the first development result failed (52.8% including abstentions). These 36
examples are therefore *development-validation*, NOT a pristine untouched
blind human-language benchmark; no 100% real-world generalization is claimed.

## Geometry closure test
`native_operator_proposal_batch.py` loads only a checkpoint passing its
declared evaluation and produces an audited three-request properties file
from model inferences, not hardcoded operation selection. This file
contains three different choices and floating-point strengths actually
output by the owned student.

`NativePlannerBenchmarkExportTest.kt` executes exactly those requests
through `NativeCadOperationBridge`, `MiniGeometry`, and `GlbWriter` to
produce original baseline and three modified GLBs. If a student
incorrectly selects an operation, or an operation is not allowed, the
test fails instead of substituting a manually chosen mesh.

`native_operator_glb_audit.py` verifies source SHA-256, actual hull
subdivision, connected recess topology, nacelle station/flare, cockpit
shoulder geometry changes, mesh validity, and triangle budgets. This
proves only controllable geometry effects, not artistic quality, welds
between multiple parts, mechanical realism, or unseen text-to-3D skill.

## Next important research gap
- Create *untouched* evaluation instructions from different shape families
  and user feedback. Do not keep tuning on the existing development split.
- Learn native operator *parameters from measured visual targets* using
  verified geometry, rather than purely text-intensity labels.
- Increase primitive coverage (true subtractive cuts in curved areas,
  fillets, tangent lofts, connected shrouds) and train selection of
  multiple sequential operations with dependency checks.
- Visually review four-view outputs before any default Android update.
- Save validated checkpoints durably; temporary CI artifacts expire.

Everything uses free source and CPU workflows with no third-party
model producing final game assets.
