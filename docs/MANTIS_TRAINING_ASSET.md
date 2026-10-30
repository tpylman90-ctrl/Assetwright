# Mantis / MK I training asset

Mantis is the first reference-led, mechanically dense hover-racer exemplar for Assetwright. It is generated from editable Blender geometry without a paid model-generation service. The same deterministic generator makes the GLB, five inspection renders, a review board, and a JSON feature record.

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

- `mantis_mk1.glb`: detailed source / LOD0.
- `mantis_mk1_lod1.glb`: automatically decimated mid-distance mesh, targeted at 15,000–45,000 triangles.
- `mantis_mk1_lod2.glb`: automatically decimated far-distance mesh, targeted at 10,000–20,000 triangles.
- `mantis_mk1_collision.glb`: separate low-poly compound collision proxy.

The LODs currently use size-based detail culling and mesh decimation. They are not hand-retopologized quad-flow meshes. AO, normal, and curvature map baking is also not implemented yet; those are the next high-to-low production stages. The asset is intended for Godot GLB import and later reuse in SceneForge. It remains a procedural training exemplar; it does not train or update a machine-learning model by itself.

## Learning-loop record

`mantis_mk1_training_record.json` preserves the asset prompt, negative prompt, generator version, target engine, triangle count, coordinate convention, view names, and feature labels. The user reference image is not copied into the public repository by this workflow.
