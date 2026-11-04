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
mesh types: cylinder, rounded-box superellipse extrusion, sampled ellipsoid,
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
