# Vehicle fidelity pipeline — Shrike visual benchmark

## The objective

Produce **original, editable game vehicles** with the surface continuity,
integrated details, and material richness of the uploaded high-quality Shrike,
using our own Blender tooling and approved reference images. We must not
confuse geometric validity with believable automotive surfacing.

The Shrike user-supplied model was successfully loaded in SceneForge, but
is **not a native Assetwright generation result**. It establishes a
visual-quality target, not an autonomous AI capability.

### What the benchmark actually demonstrates

The verified SceneForge-oriented model uses a roughly 6.8 × 3.56 × 1.85 m
envelope, ~164K triangles and three 2K baked texture maps: base color,
metallic/roughness and OpenGL-style tangent normal. It is one painted mesh;
its window/cabin separation needs additional authoring for a game camera.
Treat those counts as reference observations, not mandatory production
minimums or proof of quality.

The previous A1/A2 generators have editable surfaces and components, but
depend heavily on flat or procedural base colors, tube-like curves and
independently placed body strips. More geometry alone will not fix those
surface and material gaps.

## Construction gates

1. **Blueprint and shape brief**: establish orthographic silhouette guides,
   vehicle proportions and station curves. Review both body width distribution
   and roof/fender height rails. No secondary details until front, side,
   top and rear silhouettes are approved.
2. **Editable high-poly master**: author separate quad-oriented primary
   panels using Mirror, deliberate automotive shoulder/crease loops, proper
   reflections and uniform transitions. Allow support-loop or bevel detail
   around air intakes and mechanical fixtures. Use fitted glass boundaries,
   not overlapping floating polygons.
3. **Detail source model**: create actual recessed ducts, joint grooves,
   fender transitions, panel gaps, mounting seams, headlights and
   cockpit elements. Use procedural noise only for small-scale material
   texture, not as a substitute for defining the main vehicle shape.
4. **Game topology and UVs**: retopologize panels to preserve silhouette
   and hard edges, build controllable LODs and separate functional parts.
   Never blindly destroy the UV layout or mesh topology by ratio-only
   decimation. Inspect mesh boundaries and distorted shading.
5. **PBR texture baking**: in Blender Cycles, bake selected-to-active normal
   from high-poly to a lower-detail mesh using a suitable cage. Create
   base color and metallic/roughness maps, with AO used judiciously.
   Preserve normal map handedness for Godot (OpenGL Y+). A reference-like
   close-up should read as molded metal, paint and rubber before any
   complicated game lighting is added.
6. **Approval and runtime**: render front, side, rear and top, plus two
   oblique three-quarter views under identical studio lighting, clay,
   wireframe and specular-reflection material. Test seams, glass, HUD
   position and normal response. Measure actual GLB tris/textures and
   Android FPS; only then import into SceneForge.

## Proposed Android budgets (adjust after profiling)

- LOD0 / Foundry inspection: target 90K–160K triangles and 2K primary
  textures, with selective higher-resolution textures if phone testing
  justifies them.
- LOD1 / normal racing: target 30K–65K triangles, baked maps retained.
- LOD2 / distant opponent: target 5K–15K triangles and a smaller texture.
- No fixed limit is a claim of Android performance. Profile GPU, memory,
  shader complexity, texture format and total fleet scene.

## Review contract — separate objective checks from judgement

Automatic: dimensions, mesh count, UV availability, normals, presence of
PBR maps, collision shapes, degenerate faces, inverted normals, exposed
reversed mesh faces, mesh bounds, floating components, draw calls, model
hashes and performance. The new `tools/mini_ai/pbr_asset_audit.py`
reports the material/structure subset without asserting it is beautiful.

Human review: silhouette match, reflected curvature, integration of
fenders with hull, canopy-body seam fit, depth of insets, material credibility,
consistent panel scale, visible front/rear mechanical plausibility and
originality. A useful simple rubric rates each category from 0–5; no
promotion to the approved game-asset library without convincing reference-
angle renders and explicit user approval.

## Where learning fits

Assetwright's current research model learns coarse caption-to-geometry
descriptors. It **does not generate high-end vehicles** or understand
Class-A surface transitions. We must first record edited before/after
construction specifications, part relationships, real geometry measurements,
reference-view differences and acceptance labels. Then we can train a
planner that proposes panel parameters and component layouts; Blender
remains the geometry and baking engine.

Do not use a third-party Tripo mesh as automatically approved training
ground truth, clone it through mesh conversion or publish a training set
without the appropriate rights. A private benchmark is a visual acceptance
target, not a grant to redistribute source geometry.

## Next concrete milestone

Build one *original* hovercar with this exact sequence and publish a
review package containing an editable Blender master, high-poly/LOD0/LOD1,
the PBR maps, GLB structural audit, and matched studio/Godot views.
Compare its actual appearance to the verified Shrike reference. Until
that model passes the review, further autonomous training volume cannot
be treated as fidelity progress.

### Technical references

- Blender Cycles baking: https://docs.blender.org/manual/en/4.5/render/cycles/baking.html
- Blender retopology: https://docs.blender.org/manual/en/latest/modeling/meshes/retopology.html
- Godot 4.5 StandardMaterial3D / normal maps:
  https://docs.godotengine.org/en/4.5/tutorials/3d/standard_material_3d.html
