# Mantis / MK I training asset

Mantis is the first reference-led, mechanically dense hover-racer exemplar for Assetwright. It is generated from editable Blender geometry without a paid model-generation service. The same deterministic generator makes the GLB, an editable Blender scene, five inspection renders plus cockpit and drive close-ups and a rear chase-angle review, a review board, and a JSON feature record.

## Build

Run the **Mantis MK I training asset** workflow from GitHub Actions, or let a push to `tools/blender/generate_mantis.py` build it. The workflow generates one asset per run and publishes the output as the `assetwright-mantis-mk1` artifact for three days.

## Shape targets

- Exposed black exoskeleton with visible triangulated frame tubes and crossmembers.
- Low, forward-swept profile with two articulated mantis-like arms ending in circular hover cells.
- Open, single-seat cockpit with harness, instrument pod, and skeletal canopy cage.
- Olive armored side pods with seams, vents, latches, fasteners, and serial markings.
- Paired rear turbine drums with concentric rings, stators, and amber cores.
- Swept tail fins and compact aft hover cells.

The detailed source mesh targets a 120,000-triangle real-time budget and records evaluated triangle counts for each export. The build produces:

- `mantis_mk1.blend`: editable geometry, materials, studio and cameras.
- `mantis_mk1.glb`: detailed source / LOD0.
- `mantis_mk1_lod1.glb`: automatically decimated mid-distance mesh, capped at 45,000 triangles.
- `mantis_mk1_lod2.glb`: automatically decimated far-distance mesh, capped at 20,000 triangles.
- `mantis_mk1_collision.glb`: separate low-poly compound collision proxy.

The LODs currently use size-based detail culling and mesh decimation. They are not hand-retopologized quad-flow meshes. High-to-low normal, AO, and curvature baking is not implemented yet. Authored micro-normal maps describe fine surface grain; they are not a substitute for baking larger forms. The asset is intended for Godot GLB import and later reuse in SceneForge. It remains a procedural training exemplar; it does not train or update a machine-learning model by itself.

## Reference reconstruction v5

Replaces the previous solid rectangular hull with separate tapered nose blades, sloping cheek panels, a recessed cockpit floor and connected triangulated cage. Front suspension links now extend forward close to the nose. Rear turbines have open revolved nozzle walls, recessed cores, swept stator blades and top-mounted governors. Thin swept stabilizers and split service pods follow the reference layout. Parts are authored at their final coordinates instead of stretching rotated meshes afterward.

Front, side and rear review cameras are level orthographic views. The concept sheet is visual guidance rather than a metrically consistent CAD drawing; this is a reconstruction, not an exact recovered source mesh. The 120k ceiling is a maximum, not a requirement to pad the mesh. Render comparison remains necessary before approving the asset as a training example.

All exports exclude the studio floor. Text is converted to meshes before triangle accounting, and face normals are recalculated before export. Repeated hover-cell parts use matching angular counts to avoid duplicate overlapping segments.

## Mechanical and material refinement v6

Preserves the approved v5 silhouette. Adds recessed hatch frames and pulls, cockpit switch banks and pedals, suspension clevis ears, connected coolant lines, fin relief panels and small dashboard graphics. Smooth-shaded rings use fewer cross-section segments, freeing budget for these more readable forms.

Non-emissive materials use embedded albedo, roughness and authored tangent-space micro-normal images. Fine coating variation replaces the previous coarse random scratch strokes. Emissive materials are kept clean. The `cockpit_detail` and `drive_detail` renders supplement the five standard review views. Generated LODs still require in-engine visual and performance review.

## Rear packaging refinement v7

Rear lift discs are moved inward, rearward and upward to nest immediately beneath the rear chassis, with short saddle mounts replacing the exposed stalks. Front arm reach is reduced 20% around the fixed suspension roots; lift cells move rigidly to retain circular rims and fastener patterns. Collision proxies follow the new positions.

The rear assembly gains separate tapered nozzle petals, actuator rods, recessed combustion rings and center cones, angular lower guards and diffuser vanes, rear marker housings and a central service plate. A `chase` render supplements the standard views to assess the rear at a driving-camera angle; it is a Blender review, not an in-engine screenshot.

## Learning-loop record

`mantis_mk1_training_record.json` preserves the asset prompt, negative prompt, generator version, target engine, triangle count, coordinate convention, view names, and feature labels. The user reference image is not copied into the public repository by this workflow.
