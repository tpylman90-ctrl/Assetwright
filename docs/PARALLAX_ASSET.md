# Parallax / 01

An original two-seat hover coupe designed by Forge without a concept sheet or reference image. This is a separate Assetwright experiment; the Mantis generator and saved Mantis v10 package remain independent.

## Design

Porcelain titanium shoulders flow around a continuous smoked sapphire cockpit. Four vertical lift ducts pass through the body and belly. Curved stator fans, violet field rings, recessed side intakes, swept split tail fins and two flattened oval rear drive ports supply functional depth. A midnight petrol keel and narrow ice-white/amber lighting frame the clean shell. The cabin contains two fitted seats, a driver yoke and a compact dashboard.

The main body uses quad control surfaces, selective subdivision and Boolean apertures. Separate glazing, seals, machinery and trim remain editable. Portable glTF PBR factors carry color, roughness, metallic, alpha and emission. UVs are smart-projected; high-to-low normal and AO baking are not implemented.

## Build and review

Run the **Parallax 01 original hover coupe** GitHub Actions workflow or push a change to `tools/blender/generate_parallax.py`. The hosted Blender build writes an editable `.blend`, full-detail GLB, two LOD GLBs, a collision GLB, eight model renders and a JSON record. Artifacts are retained for three days; user-facing review releases are saved separately.

Local fast shape review:

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python tools/blender/generate_parallax.py \
  -- --output-dir generated/parallax-shape --shape-check
```

The full build caps LOD0 at 120,000 triangles, LOD1 at 45,000 and LOD2 at 20,000. It evaluates modifiers before reducing LODs. Exported GLB counts must match the record. Studio geometry is excluded. Front three-quarter, front, side, rear three-quarter, rear, top, cockpit and chase views show the actual procedural mesh.

Blender coordinates are nose −Y, rear +Y and up +Z. This is a static asset: Godot driving, LOD-transition behavior, animations and high-to-low baking have not been validated. The JSON record preserves the original prompt and negative prompt; it is not an automatic ML training run.


## V2: sculptural side-body pass

The first model's frontal and three-quarter shapes were approved, but the strict side view
read as a largely featureless capsule. The V2 generator addresses that by changing the
actual load-bearing shoulder geometry rather than relying on a collection of added rods:

- **Continuous formed rocker trench:** Sixteen-point shoulder control sections cut a
  concave lower relief into both flanks; a dark recessed strip reads in side elevation.
  The outer lip carries a separately sculpted, swept composite undercut aero blade.
- **Deeper fitted side intakes:** A long tapered, closed Boolean cutter replaces the
  old rectangular side air pocket. Each opening has a dark recessed plenum, angled
  splitters, a formed eyebrow and a fitted lower sill, with a violet field core inside.
- **Loaded rear quarter:** Revised longitudinal control sections widen the aft shoulder
  around the rear lift machinery and raise the lower tail for a more dynamic taper.
  A local crest and a fitted rear-haunch fairing create shoulder-to-tail flow.
- **More purposeful side lighting:** The narrow violet filament tracks the sculpted
  rocker lip rather than tracing a straight line on the broad side wall.

This pass preserves the original four through-body lift ducts, twin rear drives,
two-seat canopy and clean porcelain/petrol material language. It deliberately puts
silhouette and surface quality ahead of tiny fasteners.

**Validation pending:** A successful source commit is not evidence that the Blender
workflow passed or that the new side profile is attractive. Check the newly generated
side, hero three-quarter, top and rear three-quarter renders, then inspect whether the
recesses are open and the aft haunch blends properly. Geometry, LOD, export and Godot
readiness must be verified from the new workflow outputs.


## V2 polygon optimization (after the 125,908-triangle failed build)

The V2 sculptural side-body pass initially exceeded the 120,000-triangle ceiling
by 5,908 triangles. In that build the evaluated mesh breakdown was:

| Assembly group | Evaluated triangles before optimization |
| --- | ---: |
| Body | 83,604 |
| Cockpit | 21,524 |
| Propulsion and lighting | 20,780 |
| **Total** | **125,908** |

The corrective pass reduces the twin ceramic shoulder meshes from three
subdivision levels to two. This retains their V2 control sections, haunch
profiles and the concave side-rocker trench while reducing their subdivision
quads by approximately 75% (about 40,000 fewer triangles across both
shoulders, before accounting for Boolean cuts and other evaluated modifiers).
Default radial lift-shell and rear-drive ellipse resolution is reduced from
64 to 48 samples to avoid allocating excess geometry to small machined rings.
The hard-surface helper also enables Auto Smooth before weighted-normal
evaluation when the Blender version exposes that property.

The generator now writes the 20 heaviest evaluated meshes to the
`PARALLAX_BUDGET` CI output and records them in the training JSON for targeted
future optimization. The 120,000-triangle evaluated-mesh limit still runs
before expensive renders and exports.

**Validation requirement:** These are source-code changes, not verified
export counts. Read the fresh GitHub Actions log and inspect the side,
hero three-quarter, rear three-quarter, and top rendered meshes. If a
reduction noticeably facets a reflection or weakens the sculpted shoulder
line, distribute resolution around that curvature instead of raising
subdivision indiscriminately.


## V3 direction: 1957-inspired jet-age competition hover racer

**Design correction from the visual review:** Parallax is not a soft luxury lounge
coupe. Its existing long nose, rounded front fenders, slim greenhouse and
twin rear propulsion ports unexpectedly evoke the 1957 Chevrolet Corvette SS
XP-64 racing prototype. Use that period of competition-roadster design as
historical visual inspiration **without reproducing the Corvette's bodywork,
badges, sponsors, racing number or manufacturer identity**. Parallax keeps its
original white porcelain-titanium / deep petrol / smoked sapphire scheme,
four through-body hover ducts, and twin electric propulsion outlets.

**Exterior V3 modeling decisions**
- Preserve the already approved front/rear 3/4 shape and the deeply shaped V2
  undercut rocker rather than adding a large spoiler or modern wedge nose.
- Add an original, smooth, fitted jet-age racing cove on each shoulder, with
  continuous longitudinal curvature and a controlled champagne-alloy highlight.
- Enrich the twin rear drive throats with layered machined collars and recessed
  violet field elements. Keep them compact, not industrial exhaust funnels.
- Keep the flowing tail shoulder, small swept stabilizers, and clean lift
  duct apertures. Surface and body mass outrank bolts and random vents.

**Cabin V3:** Two compact, low GT competition buckets with separate sculpted
shells, tailored ivory cushions, deep-blue pads, raised bolsters, restraint
anchors and individual seam bands. A bonded center tunnel and armrest hold
a rotary mode selector and tactile switchgear. The driver receives two
round digital-analogue hybrid gauges beneath a formed dashboard brow and a
small polished competition steering rim; the passenger has a softer swept
dash fascia. Satin champagne alloy and understated upholstered side panels
add luxury without sacrificing the purposeful racing packaging.

**Critical review views:** The generator now emits `interior_open` and
`instruments` in addition to the eight exterior views. In those two
renders only, the canopy glass is hidden to reveal actual mesh geometry.
The saved vehicle source and exported GLB retain the complete canopy.

**Budget and validation:** The last independently verified V2 run produced
82,222 triangles at LOD0, 26,577 at LOD1, 10,712 at LOD2 and 48 for
collision. V3 counts and aesthetics must be validated with the new workflow;
the 120k/45k/20k caps remain. Inspect cockpit component intersections,
canopy clearance, front/side/3/4 continuity, and material legibility before
approving for reuse. This is a modeling iteration, not a validated Godot
driving test or automatic ML model training.


## V4 cabin reconstruction: organic surfaces and bonded dash

User review of the V3 `interior_open` and `instruments` renders identified
two high-priority structural problems: the seats were conspicuously assembled
from disconnected beveled rectangular blocks, and the black dashboard hovered
above a separate blue bridge with no visible bulkhead mounting. **Exterior
surfacing is approved; keep the V3 body, four lift ducts, spear trim, and rear
drive assemblies unchanged.**

The V4 generator replaces those cabin objects with mechanically connected,
editable control meshes:

- Seats are built from progressive elliptical stations with contoured
  leather cushions, a separate curved structural seat shell, rounded integral
  headrests, shaped thigh/shoulder bolsters and fitted flat harness ribbons.
  Trim remains restrained; stitching no longer serves as substitute geometry.
- A nine-station closed dashboard cross-section spans the full cockpit width.
  Its forward and lower faces land on the internal cockpit floor/bulkhead;
  tapering outer stations blend into the interior side walls instead of
  terminating as a floating horizontal box.
- A recessed driver instrument nacelle has two independent fitted circular
  hybrid gauge faces. The steering rim is attached by a column to the dash.
- The narrow console is an organically formed longitudinal body with an
  integrated padded armrest and selector. Both door-side upholstered panels
  are profile surfaces, not bevelled blocks.
- The existing `interior_open` and `instruments` camera outputs remain
  dedicated real-mesh cutaway renders with canopy glass hidden for inspection
  *only*; saved and exported vehicle meshes retain the canopy.

**Required verification after CI:** Evaluate under 120,000 LOD0, 45,000 LOD1,
20,000 LOD2 triangles; inspect side/hero/rear exterior to verify no visual
regression. Check seat shell-to-pad layering, shoulder-belt embedment,
dash-to-inner-sill mounting, instrument visibility, steering-column attachment,
console clearance and canopy clearance in the close-up cutaway. The source
revision does not establish visual correctness until those Blender renders
are inspected; no Godot interior-camera test has been completed.
