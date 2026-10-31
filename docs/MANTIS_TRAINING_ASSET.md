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

## Blender research and next modeling standard

This is a practical research summary for Assetwright, not a claim that the generator has learned autonomously or that the following work is already implemented.

### Diagnosis from the current asset

The generator is strongest at repeated hardware and layered assemblies. It still relies on beveled boxes, straight rods and extruded plates for too many major forms. A valid 120k export does not establish reference fidelity. The rear also demonstrates why the driving camera needs its own review. The v7 correction is completed; the surface-modeling and baking work below remains a next stage.

### Shape and topology

Use a simple mirrored control mesh for each major housing, with deliberate cross-sections and support loops to control taper, curvature and edge transitions. Subdivision is selective: support loops and creases control the shape, while simply increasing levels is not a shape solution. Keep physically separate service panels separate. Use shared mounting landmarks for pivots, brackets and shell edges so parts actually fit. Shrinkwrap can help conform fitted panels to a master surface with a controlled offset; it does not reconstruct a reference automatically.

Sources: [Subdivision Surface](https://docs.blender.org/manual/en/5.4/modeling/modifiers/generate/subdivision_surface.html), [Shrinkwrap](https://docs.blender.org/manual/en/4.2/modeling/modifiers/deform/shrinkwrap.html), [Blender Studio modeling guide](https://studio.blender.org/tools/artist-guide/asset-creation/modeling).

### Machined detail and shading

Use Boolean Difference for real recesses when geometry is needed, with closed cutter meshes and inspection of the result. Check the resulting topology before subdivision. Set bevel widths to the manufactured part's scale; tiny fasteners do not need the same segments as prominent housings. Hardened/weighted normals help preserve flat faces around rounded edges, but do not fix an incorrect silhouette. Review a neutral clay render and broad moving highlights before material polish.

Sources: [Boolean](https://docs.blender.org/manual/en/dev/modeling/modifiers/generate/booleans.html), [Bevel and Harden Normals](https://docs.blender.org/manual/en/4.0/modeling/meshes/editing/edge/bevel.html).

### UVs, baking and materials

Smart projection remains useful for small mechanical parts. For hero panels, create and inspect seams and UV stretching, reserve adequate island margins and plan consistent visible texture density. Make separate high-detail and game meshes for one pilot assembly before attempting the whole craft. Bake tangent-space normals and AO with selected-to-active projection and a tested cage. Check intersections and projection errors. The existing authored micro-normal maps represent surface grain only; they are not high-to-low bakes. Place wear where contact, handling and heat justify it rather than covering every panel with random scratches.

Sources: [UV seams](https://docs.blender.org/manual/en/5.2/modeling/meshes/uv/unwrapping/seams.html), [Render Baking](https://docs.blender.org/manual/en/latest/render/cycles/baking.html).

### Export and review

glTF triangulates surfaces and can split vertices at UV/normal discontinuities. Count evaluated export triangles and inspect the imported result, not only the editable source. Keep normal images Non-Color and connect through a tangent-space Normal Map node. Check the Blender version printed by the runner before adopting modifier/API examples from a newer manual.

Source: [glTF export and materials](https://docs.blender.org/manual/id/4.0/addons/import_export/scene_gltf2.html).

Next implementation order:
1. Prototype one fitted rear housing with a control mesh, actual recesses and coherent mounts.
2. Compare clay front/side/top and rear chase views against the reference before detailing.
3. Build and bake a matching low-detail housing; inspect it after GLB import.
4. Reuse the proven approach across the craft and simplify LODs by assembly.
5. Move budget validation ahead of expensive renders and report per-assembly triangle costs.

These are project-specific decisions informed by the sources, not universal prescriptions. The v7 build remains an unbaked procedural asset and has not been driving-tested in Godot.


## Controlled housing rebuild v8

Rebuilds the side equipment pods from six deliberate octagonal cross-sections: tapered ends, raised shoulders and pinched lower edges. Boolean-cut pockets contain recessed service hatches. Crown ribs and lower carriers follow the new shell; mounting clevises connect it to the chassis. This replaces the earlier repeated beveled boxes.

Rear drives use shorter axial packaging, narrower stepped barrels, thick terminal collars and segmented outer jackets. The existing petals, stators, governors, lines and rear markers share an assembly transform to retain their fit. Rear lift cells remain at the v7 positions. Front suspension webs now have shaped, variable-width cross-sections, and shoulder harnesses are flat straps.

The full-detail and reduced LOD budgets are checked before review rendering. The training record now includes evaluated triangle costs grouped into drive, pods, lift and chassis/cockpit. Grouping uses object-name categories for diagnostics, rather than claiming a semantic ML segmentation. Blender API compatibility covers Eevee engine naming/settings and BMesh face-normal recalculation.

Adds a rear three-quarter camera alongside side, top and chase views. These are renders of the procedural mesh. Inspect neutral-clay views and the exported GLB alongside the material renders. No Godot driving or LOD-transition validation is claimed. Hand-authored UVs, a high-to-low baking pilot, broader frame reconstruction and reference-directed material wear remain unfinished.
