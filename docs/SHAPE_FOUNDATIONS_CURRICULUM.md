# AssetWright — shape foundations curriculum (research only)

## Priority
Visual inspection of V2 vehicles rejected the idea that exact parameter
prediction and extra triangles imply good 3D form. Train native general
geometry BEFORE extending the vehicle-only planner.

## Learning ladder
1. Primitive volumes, cross sections and proportions: box, cylinder, cone,
   sphere, ellipsoid and capsule.
2. Deformation: scale, taper, shear, extrusion and corner rounding.
3. Advanced construction: multisection lofts, path sweeps, moving frames,
   subdivision, fillets and genuine G0/G1/G2 seam goals.
4. Connected structures: cutouts, openings, booleans, joint interfaces
   and watertight assemblies.
5. Transfer into vehicles, architecture, furniture, tools and machinery,
   with independent category and human visual benchmarks.

## Actual first experiment
The new Kotlin NativeFormLab creates five original continuous, capped
mesh types: cylinder (strength changes its radius), rounded-box superellipse extrusion, sampled ellipsoid,
tapered loft and arch sweep with fixed-orientation cross sections.
These are elementary research shapes, NOT true CAD NURBS/3D fillets,
advanced moving-frame sweeps or an arbitrary asset generator.

The bounded GitHub experiment makes 45 original training GLBs and 20
separate dimension-family validation GLBs. It hashes each source, independently
audits actual vertex/index buffers, manifoldness, outward volume and
complexity. Our new five-class CPU softmax student learns only from
four measured geometry features: taper, mid bulge, centerline bend and
corner fullness. Source labels are training targets, NEVER model input
features. Evaluation compares the 20% majority guess against a candidate
requiring >=90% accuracy, >=3/4 correct per class and >=60 point gain.
Any rejected candidate is preserved instead of falsely promoted.

## Research honesty and boundaries
The validation forms come from the SAME generator, with different numeric
dimensions and strengths. This is a narrow development benchmark,
not proof of novel-design or cross-category understanding. The accepted
three-operation model and prior blind vehicle benchmarks remain untouched.
The Android default generator does not run these research weights.

Teaching concepts: Blender modeling foundations
https://education.blender.org/blender_education_badges/modeling/
and Fusion loft geometry/continuity
https://help.autodesk.com/view/fusion360/ENU/?contextId=SLD-LOFT-SOLID

Next stage: add full capsule/cone, continuous inverse parameter learning,
real tangent-oriented sweeps and variable-section curvature probes; then
test on entirely new object families before any production promotion.

## First live training lesson
The initial live run correctly rejected the corpus because its cylinder strength did not move any vertices: three training GLBs of the same numeric family were byte-for-byte identical. Distinct command labels were not independent geometry. We fixed the actual native cylinder radius control instead of dropping its SHA-256 uniqueness gate or lowering model acceptance thresholds. The discarded initial run remains available in GitHub Actions as research history.

## First native study — independently verified, November 3, 2026

The initial GitHub form study rejected duplicate source GLBs because the cylinder's nominal control made no geometry change. We repaired the cylinder radius behavior, preserving the SHA-256 uniqueness rule and all training thresholds. The first failed run remains in Actions history.

The corrected study exported 65 original Kotlin geometry GLBs, all passing independent structural and provenance checks. The own from-scratch five-class morphology learner trained on 45 GLBs from three dimension configurations, then correctly classified all 20 held-out GLBs from two new **synthetic** dimension configurations. The majority-class baseline was 20%; the measured student score was 100%, with 4/4 correctly classified for every class. **These evaluation configurations are now exposed and cannot be reused for future pristine blind testing.** This result is limited to intentionally separable generated form types, not advanced surface understanding or arbitrary object generation.

Successful original proof: https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41770508021

Durable archived research release (source GLBs, 45 training hashes, 20 evaluation hashes, trained weights, report and predictions): https://github.com/tpylman90-ctrl/Assetwright/releases/tag/assetwright-native-forms-79b712cf2d07

Research release verification workflow: https://github.com/tpylman90-ctrl/Assetwright/actions/runs/41770962161

The original Android and V2 geometry nonregression builds also passed at the source commit; the regular app has NOT switched to these form models. The workflow is now **manual reproduction only**, with no automatic new release from these inspected synthetic holdouts. Future stages need reserved new families, learning form controls in addition to recognition, and independently tested cross-category transfer.
