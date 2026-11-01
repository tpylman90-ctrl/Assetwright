# Forge-assisted learning for Assetwright

**Status:** v0.3 implementation, source-level; Android CI and physical-device
validation must finish before describing this as a verified release.

This is a deliberate human-in-the-loop workflow that lets Forge (ChatGPT) work
with the real generated mesh, not just an image. The app is offline and does not
connect to ChatGPT/GitHub by itself. The user selects exactly which files to
share for an assistant review. No API key, conversation content or model is sent
anywhere automatically.

## Forge Review 02 — v0.6.1 low cockpit and exposed-unit geometry

A user-exported v0.6 Forge ZIP contained a real, hash-verified GLB with
1,694 triangles and 22 mesh parts. The prompt required two engines and four
exposed repulsors. Both the exported operation sequence and the actual GLB
matched these component counts, including four mounting-bracket meshes.

Visual and geometric inspection exposed two remaining deficiencies:

- The canopy's peak rose only slightly above the fuselage top. The body
  construction used a fixed upper bulge near 1.25 m, independent of the
  user-requested low roof height (e.g. 1.34 m).
- Outboard repulsors were positioned near the widest shoulder, making the
  explicitly exposed mounting style barely distinguishable from the tucked one.

The hull upper profile now adapts to the requested roof height, guaranteeing
at least roughly 0.25 m of greenhouse emergence from the main body in the
supported range. The keel, front light, and drive vertical positions follow
the adjusted hull center. Exposed lift pads are offset beyond the widest body
silhouette, with thicker support arms. The two/three-engine planner and
2/4/6 repulsor counts are unaffected.

A new mesh-based unit test evaluates multiple low-roof settings, measures
actual canopy and body vertex extents, and tests that exposed pads sit beyond
the hull's maximum lateral extent. This is a code-level geometry fix. It is
**not yet a visual review of the newly generated v0.6.1 GLB**; the Android
build must be tested and a fresh review ZIP compared to the original.

This review also found that older Forge ZIPs mislabeled their generator as
version 0.5 even when the app was v0.6. v0.6.1 corrects the review metadata
for future model provenance.

## First geometry-quality review (v0.5.2)

An uploaded, user-exported Forge ZIP was independently decoded and inspected.
The model was a small 18-component hover vehicle with a smooth lofted hull,
glazed greenhouse, two drives and four lift repulsors. This analysis found
geometry issues that numeric prompt lessons alone could not correct:

- A sudden forward-body width change from applying full nose taper to some
  rings and no taper to the next ring.
- Front light endpoints extending beyond the actual narrow front cap.
- A raised glass perimeter that did not fully fit inside the hull shoulder.

The Android generator was corrected using a continuous front-width easing
function, added front and canopy loft stations, a lower canopy mounting edge,
and a light panel fitted inside the actual nose half-width. A new Kotlin test
checks those invariants. These are **source-code modeling improvements**, not
neural updates or proof that a particular rendered shape looks better.
The revised build still requires visual review on Android.

As with all Forge review bundles, no privately shared GLB or original prompt
was committed to the public repository. Only generalized shape construction
changes and synthetic test cases were published.

## 1. Export the review package from Android

1. Generate a supported vehicle in Assetwright.
2. In **Forge AI Review**, type what looks wrong (e.g. "lower the roof and make
   the body wider"). Include reference images in our ChatGPT conversation if
   useful; selected reference images in Assetwright are *not* currently included
   or analyzed by the offline generator.
3. Tap **Export Forge review ZIP** and attach the saved ZIP in the Assetwright
   conversation. It contains:
   - `model.glb`: **actual** game mesh exported from the Android generator;
   - `review.json`: prompt, chosen game quality, current numeric parameters,
     mesh part names, triangle count, user feedback, and the SHA-256 fingerprint
     of the GLB;
   - `README.txt`: file contents and sharing note.

If you want to keep a model or prompt private, do not share its bundle.
Review bundles are not automatically published to the public repository.

## 2. What Forge can do with it

Forge can inspect the GLB, report incorrect proportions, lighting, normals,
hidden sides, mechanical connections, and topology; compare against your
reference pictures; develop revised geometry or new construction rules;
propose corrected dimensions; and modify/test the existing public Assetwright
generator in the GitHub repository as authorized.

For **parameter-only** fixes, Forge can produce the interchange format
`assetwright-forge-proposal-v1`. The offline reviewer CLI validates the bundle
before writing a candidate:

```sh
python tools/mini_ai/forge_review.py exported-review.zip --inspect-only

python tools/mini_ai/forge_review.py exported-review.zip \
  --set width=2.65 --set roofHeight=1.38 \
  --notes "Widen body and lower the bonded canopy" \
  --output forge-proposal.json
```

The command **does not infer better values automatically**: a reviewer supplies
them after inspecting the GLB and user feedback. Every proposal is linked to
the reviewed model's SHA-256 hash. Unknown parameters, values out of range,
hash mismatches and no-op proposals are rejected.

For **construction/code** fixes (new geometry families, better loft surfaces,
actual door openings, fitted cockpit structure), Forge edits the corresponding
Kotlin/Blender generators in the public repository, provides the commit and
build evidence, and asks for visual verification before counting the outcome
as a successful training example. A parameter proposal cannot manufacture
topology features that the geometry engine does not implement.

## 3. Approve back on Android

1. Open the exact generated model you exported for review.
2. Tap **Import Forge correction**, select `forge-proposal.json`.
3. Assetwright checks that the SHA-256 matches the **currently displayed GLB**,
   then displays the proposed explanation.
4. Tap **Apply Forge correction to preview** to regenerate the mesh locally.
5. Inspect the result. **Only tap "Approve design · Teach Mini AI" if the
   correction is actually better.** That action adds the corrected prompt and
   dimensions to your private device learning memory.
6. Optionally export accepted learning examples to your local home-trainer
   inbox. The existing home training watcher evaluates and packages these
   examples; it does not automatically publish them.

If a model was edited or regenerated after review, the proposal will be
rejected as stale. Export a new bundle in that case.

## 4. What this is and is not

- **Working principle:** The assistant helps teach editable numeric vehicle
  parameters; separately, it can upgrade the deterministic geometry generator.
- **Not a trained neural 3D model yet:** We still need a labeled geometry corpus,
  a trained neural parameter model and held-out evaluation of real shapes.
- **Not autonomous ChatGPT background work:** The assistant reviews a bundle
  when you attach it here or request a repository review. There is no hidden
  always-running assistant connected to your computer.
- **Private by default:** The public repo contains tools, schema and original
  code. Do not commit downloaded third-party models, personal feedback exports
  or private review ZIPs unless explicitly authorized to publish them.
- **Safety and validation:** Local review ZIPs are bounded and hash-checked;
  external scripts, prompts, and models are never executed from review files.
  Only allowlisted numeric dimensions can be written by a proposal.
- **Rollback:** Revert an unwanted local correction by approving a new prompt
  correction in the Android UI, or replace an imported home pack with the
  previously validated pack. Keep backups of important data before uninstalling.

## 5. Source files

- `app/src/main/java/com/assetwright/app/mini/ForgeReview.kt`: review ZIP
  exporter, SHA-256 binding, correction parser.
- `app/src/main/java/com/assetwright/app/MainActivity.kt`: Forge AI Review UI.
- `tools/mini_ai/forge_review.py`: independent offline verifier/proposal writer.
- `tools/mini_ai/test_forge_review.py`: hash and bounds regression checks.
- `docs/MINI_AI_TRAINING.md`: private home learning setup.

**Next development gate:** verify Android CI, test ZIP creation and import on a
physical phone, and review the first real exported bundle through this workflow.
