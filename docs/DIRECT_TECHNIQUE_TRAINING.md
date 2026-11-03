# Direct technique teaching — making Forge's modeling process explicit

## Why this is different from training on finished models

Assetwright's original research learner predicts eight shape descriptors from
licensed, captioned 3D models. Those samples communicate *what a shape is*,
but often not *how to construct it*. Finished GLBs alone lack operation
history, parameter choices, intended tradeoffs and reasons for edits.

We can supply that missing supervision from **our own procedural code**.
A modeling technique lesson is an explicit record of:

1. The diagnosed design problem and desired observable change.
2. Why an operation is appropriate instead of another shortcut.
3. A known executable operator (or an honest declaration that one is missing).
4. Its bounded parameter controls and construction steps.
5. Typical failure cases and the geometry checks that detect them.
6. The original before/after GLB hashes for a controlled intervention.
7. Whether the effect was measured and separately approved visually.

This is **programmatic procedural supervision / imitation of recorded
modeling decisions**, not reinforcement learning from its own guesses.

## Stage 1 — curriculum

Source: `training/curricula/vehicle_modeling_techniques.json`.

Three original, implemented experimental modeling techniques:

| Operation | Native control | Why it matters | Independent metric |
|---|---|---|---|
| Cross-section canopy crown loft | `canopySquareness` | Lower dome-like roof visual curvature | `roof_crown_width_ratio` |
| Sculpted shoulder station loft | `shoulderDefinition` | Make molded volumes instead of thin attached wings | Not yet independently measurable |
| Tapered five-station hover mount | `fairedRepulsorMounts` | Replace uniform structural pipes | `mount_root_tip_taper_ratio` |

Two longer-term native modeling techniques are in the curriculum as
**unimplemented**, not misrepresented as existing controls:

- Shared-boundary canopy-to-hull transition surfaces;
- Rear engine-nacelle sockets molded into the body.

Each technique records *why, geometry recipe, failure modes, original
supervision examples and separately phrased heldout feedback*.

## Stage 2 — learn when to choose a modeling operation

`tools/mini_ai/technique_teacher.py` fits a small, local supervised word
classifier to 36 **original Forge-authored critiques** and evaluates on
12 held-out critiques (four each for three currently executable operations).
The learner proposes **only a permitted modeling operation ID**, never
arbitrary Python/Blender execution. Unsafe control names, unimplemented
operators, missing parameter bounds and training/validation shortfalls
are rejected.

The classifier's score measures matching authored critique vocabulary;
it does NOT establish design reasoning comparable to a modeler or prove
generalization to complex unseen prompts. The model is research-only.

## Stage 3 — measure the consequence of each technique

The actual Android-native geometry benchmark exports 28 original
generated GLBs, with exact SHA-256 identifiers and structural checks.
`tools/mini_ai/technique_effect_audit.py` pairs the baseline with the
variation in which **one known parameter was deliberately changed**:

- baseline vs `sculpted_canopy` — verify crown width increases;
- baseline vs `faired_mounts` — verify root-to-tip support taper increases.

The required change is evaluated on at least three independently
generated vehicle cases. A candidate also has to pass the existing
structural checks; inserting extra mesh rings without true taper is
no longer counted as mastering a mounting technique.

The shoulder-volume operation currently has no clean independent
geometry metric. It remains **unmeasured**, not automatically awarded
a positive lesson. Composite `integrated_aero` variations change
multiple controls simultaneously and are deliberately not used as
single-technique causal ground truth.

## Stage 4 — visual and user approval

Previous before-and-after review found the new roof and tapered supports
measurably improved but still not production-quality. Direct technique
training must **not** turn those structural improvements into aesthetic
labels or promote generated meshes back into the licensed teacher corpus.

A future visual review needs front/side/top/three-quarter render
comparison, control of reflective surface continuity, human approval,
and actual game-ready criteria. The initial technique selection model,
intervention labels and comparison artifacts are separate from private
user data and Android runtime weights.

## Blender technique lesson expansion

Further authored lessons may cover manual edge-loop control, tangent-
matched surface bridging, inset engine sockets, bevel/weighted-normal
highlight behavior, subdivision support loops, UVs, LODs and diagnostic
clay/specular render passes. Those require *real implementations* or
well-described reviewed Blender operation traces; their names alone
must not be presented as learned working capabilities.

## CI artifacts

`.github/workflows/android.yml` runs:
- `technique_teacher.py` after testing the native app;
- `technique_effect_audit.py` after evaluating the real GLB batch;
- the artifact `assetwright-real-glb-generator-benchmark` includes the
  validated selector, operation-effect report and original generated GLBs.

Model weights are not used for automatic code mutation, user-private
training data never enters this public CI, and the Android generator
continues to use zero-valued experimental design controls until
separate approval and deployment.


## First verified direct-teaching run: 41570791202

The GitHub Android benchmark completed successfully after preventing Gradle
from substituting cached unit-test output for the GLB export itself.

- **103 Python tests passed**, native Android compilation/tests passed.
- **28/28 genuine generated GLBs** passed the existing structural gate.
- **36 original Forge-authored critique examples** train an operation-ID
  selector on three executable techniques.
- **12/12 controlled held-out critique prompts** matched their intended
  technique (100% on this small, authored test only; majority baseline
  33.3%). This is **not** general design intelligence.
- **Canopy crown loft** generated a verified +0.32443 increase in
  roof-crown-width ratio on each of four independent original vehicles.
- **Tapered structural-mount loft** generated a verified +1.04362 increase
  in root-to-tip mount profile ratio for the same four vehicles.
- **Shoulder station sculpt** has a real experimental code control but
  no independently isolated metric. No positive geometry-supervision claim.
- **Body/canopy seamless bridging** and **embedded rear nacelle sockets**
  are documented but not yet implemented.
- **Zero generated models** were approved as production-quality or
  recursively added as independent ground-truth training data.
- No user-private samples, models or Android runtime AI weights changed.

Both machine-readable training outputs are in the named GitHub Actions
artifact `assetwright-real-glb-generator-benchmark`:

- `technique-learning/selector/validated_selector.json`
- `technique-learning/selector/evaluation.json`
- `technique-learning/effects.json`

The source is preserved in run
https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41570791202.

The next engineering gain must come from implementing more expressive
**working modeling operators**, not collecting more superficially
labeled images or maximizing two easy geometry proxies.
