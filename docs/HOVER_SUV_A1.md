# Hover Race SUV — A1

Status: first-pass procedural Blender generator, **not visually approved**.

## Approved reference

Assetwright Library: `/Assetwright/References/Hover_Race_SUV_Concept_A1.png`
(1536x1024 multi-view concept board, preserved separately from the public repository).

Reference characteristics: silver SUV-shaped hover racer with red hood and rear-quarter livery, matte graphite lower intakes, cyan field emission, four chunky inset levitation modules, long pitched nose, broad shoulder flares, sweeping four-door greenhouse, low roof spoiler, athletic high beltline, and red/black fitted cockpit.

## Geometry plan

- Blender axes: front **−Y**, rear **+Y**, up **+Z**.
- Preserve SUV proportions and dynamic racing stance, not a short hover buggy.
- Master shell built as a low-density longitudinal quad loft; roof, glazing, pillars and aero pieces built independently.
- Substantial fenders should read as part of the body mass; do not make them thin add-on wings.
- Four physically distinct hover boots: mounted under arches, dark casing, cyan field coil and diffuser.
- One unified front fascia with recessed grille and narrow LED headlights.
- Interior is a spatial blockout: dashboard, two seats, center console; no floating HUD.
- Glossy reflective paint and clean readable seams; do not consume the triangle budget on bolts.

## Build

Run [Hover Racing SUV A1 first pass](../.github/workflows/hover-suv-a1.yml) through GitHub Actions or:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python tools/blender/generate_hover_suv_a1.py \
  -- --output-dir generated/hover_suv_a1
```

Expected outputs: editable `.blend`, LOD0/1/2 GLBs, six PNG views and JSON metadata. CI limits: 120k/45k/20k triangles. Artifacts expire after 3 days.

## Review gates

1. Front 3/4 and rear 3/4 silhouette close to the supplied board.
2. Side profile: substantial front and rear haunches, no disjoint flares.
3. No hovering UI/dashboard or unmounted lift boots.
4. No faceting, black shading glitches or disconnected glass panels.
5. LOD0/LOD1/LOD2 exported GLB counts checked against caps, not merely source mesh count.

This is an explicit human-review stage. The procedural generator implements the approved concept's major volumes but does not yet represent production automotive Class-A surfacing, advanced UV baking, rigging, collision proxy, or Godot driving integration.
