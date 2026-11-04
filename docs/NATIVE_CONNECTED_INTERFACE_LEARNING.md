# Connected through-bore and flange learning — development stage

## Purpose

The accepted three-operation AssetWright student accurately reconstructed
synthetic continuous hulls, but the source geometry lacked true structural
openings and joined interfaces. This new isolated laboratory tests a real
topological hole, an integral flange, and independently measured smoothing,
without weakening prior learning gates or promoting research models.

## Source engine, no imported AI geometry

NativeInterfaceLab.kt creates **one connected indexed solid shell** with
an open through-bore along the entire longitudinal axis. Its interior liner
connects to the outside surface with annular faces at both ends. This is
genuine genus-one topology (Euler characteristic 0, one component, no edge
boundaries), not an opaque inset plate, a detached pipe, or a shader trick.

A widened flange is constructed from the SAME shared exterior rings. Its
compact-support polynomial envelope returns to the base surface with
zero analytic first and second derivatives. A controlled blend width changes
how gradually the flange connects to the parent tube. This is an analytic
smoothness *target sampled as triangles*, not true Class-A CAD NURBS/G2
continuity across separately modeled patches or a circular constant-radius
fillet. No Boolean solver, weld operation or arbitrary profile sketch is
implemented yet.

Three bounded independent continuous modeling controls:
- boreStrength — physical through-hole cross-section
- flangeStrength — real outer-wall flange expansion
- blendStrength — shoulder/transition length and curvature

## Fresh original GLB curriculum

480 source-hashed Kotlin GLBs: 360 training shapes in 12 new numerical
dimension families, 60 validation shapes in four disjoint families, and 60
extreme aspect-ratio tests in four more families. The measured model
sees only actual glTF vertices and derived geometric features, never the
operation-strength labels or case names as inference inputs.

Every source must independently satisfy:
- One source-connected shell and 2,624 true native vertices
- 5,248 triangles, 7,872 distinct two-sided edges, Euler = 0, genus = 1
- Zero nonmanifold/open edges, invalid triangles, inverted material volumes
- Real annular caps at BOTH ends with a noncollapsed axial through-passage
- Matched exterior X and Z section profiles, valid interior radius
- Sampled flange width second differences under 0.063, first differences
  under 0.118 — not proof of true analytic CAD G2 on arbitrary surfaces
- Exact source SHA-256, valid original Kotlin provenance and unique train
  / test partitions

The owned small CPU ridge student learns all three controls from source
morphology. Frozen pre-evaluation gates require average control error
<=.018/.027 on new dimensions/extreme proportions, independent per-control
and worst-case gates, and >=.13 MAE improvement over a fixed .5 baseline.

120 fresh student-controlled reconstructions are exported using the
original Kotlin geometry engine. Independently compare actual GLB vertices
and topology; enforce normalized forward surface RMS <=.012/.016 on
the ordinary/aspect heldouts plus strict worst-case caps. A source-verified
80-image clay/wire review is then generated for human approval.

## Learning boundaries

This studies only a single hollow housing family. The student estimates
continuous controls for a known topology; it DOES NOT learn when a
general object needs a Boolean cut, automatically weld unrelated
components, design an arbitrary object, or guarantee CAD Class-A finish.
The previous 912-GLB advanced learner and 1,120-GLB composition checkpoint
remain unchanged and Android does not load this model.

Further milestones: native sketch-driven arbitrary bores with safe
topological remeshing, multiple connected body/engine branches, real fillet
patches, tangent/normal continuity probes, and independent unfamiliar
asset-category benchmarks.

Conceptual references (not geometry providers):

- Fusion loft guide rails and G0/G1/G2 conditions:
  https://help.autodesk.com/cloudhelp/ENU/Fusion-Patch/files/SFC-REF-LOFT-DLG.htm
- Autodesk Alias explicit geometric continuity definitions:
  https://help.autodesk.com/cloudhelp/2026/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/Alias_Tool_Palette_Reference_Surfaces_palette_Surface_Tools_Common_Parameters_html.html

Only free native Kotlin, Python, NumPy, Pillow, GitHub Actions tooling.
