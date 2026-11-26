# Assetwright Geometry Lab — component-aware inspection (v0.7.4)

## Full model viewing and part selection (native Android)

Open Geometry Lab, import a GLB and use the **Full Assembly** panel.

- The complete model is shown as an orbitable, solid-filled triangle preview.
- Drag to rotate and pinch to zoom. Tap a visible triangle to select its **source GLB node/mesh primitive**, or use the dropdown.
- Keep the full assembly in view while the selected component is highlighted. Toggle **Isolate selected** to examine the chosen part without the rest of the machine.
- Select **Show full model** to restore the complete assembly.
- Use **Label part** to tag an ambiguous source component as *Robotic arm*, *Gripper*, *Battery cassette*, *Enclosure*, *Control cabinet* or a custom label. These tags are report metadata; the GLB remains untouched.
- A capped triangle sample is rendered for responsive Android Canvas viewing, **not** for numeric analysis. This viewer does not yet provide PBR textures, hardware Z-buffer or production CAD selection accuracy.

### Per-part diagnostics

Each part gets:
- Source GLB node/mesh path, optional user label and provenance
- Triangle/vertex counts and percentage of model triangle budget
- Surface area and triangle density (in source-coordinate units)
- Axis-aligned dimensions
- Degenerate triangles
- Indexed boundary and non-manifold edges for parts with up to 80k triangles
- High-crease vertex fraction and high-bending fraction
- A global face-normal directional coherence indicator (not a misalignment score)
- Contextual diagnostic flags for unusual topology, concentrated polygon use and abrupt surface changes

**Export Components JSON / Components CSV** writes individual part rows, including the five target classes when present. The existing **Export Modeling Data JSON for ChatGPT** now also embeds component reports, enabling analysis by an assistant without resending the entire GLB.

Reports based on GLB names are provisional. If a complete robotic arm is fused into a single mesh, the app cannot yet reliably infer where the arm ends and its gripper begins. Rename or separate objects in Blender/Assetwright first, or use the experimental desktop segmentation tools. The app marks unmatched target groups as *not identified*, never fabricated.

### High-density GitHub scanner

`tools/geometry_lab/component_reports.py` analyzes actual scene nodes/geometry instances, applies node transforms, and creates `component_reports.json` and `component_reports.csv`. This runs inside the **Assetwright Geometry Lab - full geometry scan** workflow for supplied GLBs. A synthetic five-assembly GLB test checks category reporting.

### Correct interpretation

- More polygons are **not inherently bad**: a gripper with threads or articulated jaws may legitimately be denser than a flat enclosure.
- A large share of sharp edges is a diagnostic *signal*, not proof that a mechanical part is malformed.
- Indexed boundary edges may result from UV or normal seams rather than physical holes.
- Face-normal coherence is low even on a perfectly modeled closed box; it cannot independently diagnose alignment.
- Density can only be compared between parts in consistent source units/scales.
- The full mesh is analyzed while the display is sampled; source GLBs are never overwritten.
- Device performance, touching and visual quality still require phone testing beyond passing the Android build.
