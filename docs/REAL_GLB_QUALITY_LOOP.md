# Real Generated GLB Quality Loop — first evaluation stage

## What's been implemented

Assetwright's own Android-native `MiniGeometry.generate` and `GlbWriter.encode`
now export controlled benchmark vehicles from **four fixed, original hover
vehicle prompts**. Each prompt gets four variants:

- unchanged **baseline**
- slightly higher, fitted canopy roof
- sharper nose taper
- slightly wider rear haunches

This is the same generator used by the Android app, not a Python imitation.
The JVM export test only writes GLBs when the CI explicitly sets
`ASSETWRIGHT_BENCHMARK_OUT`. These examples contain no external asset meshes,
user-private prompts, or personal model weights.

An independent standard-library Python GLB critic reads the real binary
vertex and triangle index buffers, rather than only trusting reported
triangle counts. It checks:

- requested 1/2/3 rear propulsion units and 2/4/6 repulsors + brackets
- actual canopy-to-hull clearance and specified roof height
- exposed vs tucked repulsor lateral positions
- mounting-bracket geometry reaching the repulsors
- zero-area/degenerate triangles and topologically overused edges
- total generated triangle count under a conservative Android budget
- SHA-256 correspondence between each original GLB and its evaluation target

All available controlled candidates are scored. A variant only becomes a
**candidate for human visual review** if it passes the hard geometry checks
and improves the baseline's screening score by at least 0.005. If the
baseline is defective, the loop explicitly refuses to select a new
champion without further inspection. The original baseline remains
unchanged when the challenger's improvement is insufficient.

This is **geometric quality control, not aesthetic intelligence**:
the score does not understand elegant curves, realistic material response,
surface continuity under reflections, object originality, similarity to
licensed references, watertight visual seams, UV quality, proper rigging,
or actual mechanical assembly correctness. It cannot automatically verify
those, and a candidate cannot self-label itself as a correct training
example.

## How to use

The Android CI workflow automatically executes the benchmark alongside
`:app:testDebugUnitTest`:

1. The Kotlin test `GeneratorBenchmarkExportTest` generates 16 original
   GLBs and per-variant target metadata only inside CI.
2. `generated_glb_critic.py` inspects actual geometry from those files.
3. `generator_quality_loop.py` produces source-hash-linked selection
   decisions and explicitly marks every result `promoted_to_training=0`.
4. GitHub uploads an `assetwright-real-glb-generator-benchmark` artifact
   containing GLBs, target manifests, and `evaluation.json` for offline
   Blender and phone comparison.

The public research model is **not** replaced with a model selected from
these outputs. No personal data, private model weights, or user generated
assets enter the public project.

For a complete closed generation/review/learn loop, we still need actual
visual evaluation against reviewed designs, independent human-labeled
accept/reject examples, source diversity, comparison against external
reference similarity, and a reviewed mechanism for modifying generator
geometry beyond the six existing body parameters.

## Source of truth

- `app/src/test/java/com/assetwright/app/mini/GeneratorBenchmarkExportTest.kt`
- `tools/mini_ai/generated_glb_critic.py`
- `tools/mini_ai/generator_quality_loop.py`
- `tools/mini_ai/test_generated_glb_critic.py`
- `.github/workflows/android.yml`


## First verified native-GLB benchmark — GitHub run 41381711593

The app's JVM export test produced **16 actual GLBs** from four fixed
original hovercraft descriptions, and the independent Python topology
critic successfully checked all 16. All 16 passed structural QA; no
candidate was admitted into model training or deployed to Android.

- Exposed racer: baseline score 0.890405; raised-roof candidate 0.977071,
  with canopy clearance increasing from 0.26755 to 0.39755 metres.
- Exposed coupe: baseline score 0.888317; raised-roof candidate 0.934766,
  with canopy clearance increasing from 0.25886 to 0.32853 metres.
- Hidden SUV: baseline kept; all four candidates structurally valid.
- Tucked SUV: baseline kept; all four candidates structurally valid.

The human-visible research comparison is still needed: high structural
scores do not make the vehicle look professionally sculpted. In an
independent approximate 3/4 render of the GLBs, both raised-canopy
changes were visually modest despite increased numeric clearance.
The current vehicle shell still has prominent straight mount arms and a
simple cockpit silhouette. Those aesthetics are outside the automated
critic. We must introduce real design-review labels and visual metrics
before using any of these structural score deltas to train modeling
preferences.

Source: https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41381711593
Artifact: `assetwright-real-glb-generator-benchmark`


## Experiment: design-oriented geometry controls (not production defaults)

The four-view racer/coupe benchmark exposed two clear shortcomings:
- the canopy crown remains a rounded blob even when raised;
- exposed repulsor supports are uniform straight cylinders.

The generator now has three **experimental design control dimensions**,
initialized to zero in ordinary VehicleSpec values:
- `canopySquareness` — raises the upper elliptical side profile toward a
  flattened, broader aerodynamic roof without increasing its peak height;
- `shoulderDefinition` — subtly shapes shoulder volume and crown;
- `fairedRepulsorMounts` — replaces two-endpoint cylindrical arms with
  smoothly tapered, five-station cross sections.

The official Android benchmark exports seven versions per vehicle (28 real
GLBs): original four variations plus `sculpted_canopy`,
`faired_mounts` and `integrated_aero`. Because all experiment controls
default to zero, no design change is silently activated in normal
phone generation.

A second, independently computed measurement pass uses actual GLB vertex
positions to check the *roof crown width ratio* and the *number of distinct
arm cross-sections*. These are interpretable geometry proxies directly
motivated by previously reviewed failures, not an AI vision model or a
claim to evaluate attractiveness. Raising the same rounded canopy does
not satisfy the flatter-roof proxy; simply moving a pipe does not satisfy
the profiled-arm proxy.

For the current controlled benchmark, a model is nominated for visual
review only when it passes all previous structural checks, increases
these explicit shape proxies, and does not materially reduce the structural
score. Only human-reviewed examples may become supervised modeling
lessons. No visual-proxy score is automatically promoted to private
training weights or Android deployment.

The original 4-view comparisons are preserved in
`training/reviews/vehicle_visual_feedback.json` with exact GLB hashes.
Those are *Forge-authored negative design assessments*, not ground truth
labels, and cannot be used as automatic training data.


## Design-quality experiment verified — 28 original generated GLBs

Run [41451924250](https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41451924250)
successfully compiled the Android mesher and independently evaluated all
**28 original GLBs** from four representative hover vehicles. All 28
passed the structural geometry gate. No new generated outputs or private
training weights were promoted.

The conservative two-feature design proxy improved for each new
`integrated_aero` candidate:

| Metric | Existing vehicle | Aero prototype |
|---|---:|---:|
| Upper canopy crown width / max cabin half-width | 0.38268 | 0.70711 |
| Repulsor mount cross-section stations | 2 | 5 |
| Satisfied design proxy checks | 0/2 | 2/2 |

The code nominated all four `integrated_aero` outputs for **visual
review**, but these measurements are narrow technical proxies and are not
artistic approval. An independent orthographic 3/4 comparison found the
silhouette improvement visibly modest. The body surfaces, rear propulsion,
and cockpit/body transition remain visually basic.

Accordingly, the exact shortlisted GLB SHA-256s have also been recorded
in `training/reviews/vehicle_visual_feedback.json` as *not production
quality*. These evaluations cannot become automatically accepted
supervised modeling examples. The existing Android default generator
uses zero-valued experimental controls and remains visually unchanged.

Next research and modeling tasks: add connected body feature geometry
instead of decorative overlays, integrate the nacelles into the rear hull
and use multiple real reference views to teach/propose meaningful silhouette
changes before retraining design preferences. Do not optimize roof and
support proxies alone.
