# Architectural modeling operators — experimental design lessons

## What was added

Assetwright's original procedural mesher now exposes two additional
**off-by-default** native modeling controls:

- `cockpitShoulderTransition` changes the *original continuous hull mesh*
  by inserting interpolated longitudinal stations and feathering local
  deck-shoulder breadth and height near the cockpit footprint.
  This is an example of **sculpting the receiving surface**, not
  adding a flat decorative panel.
- `rearNacelleShrouding` replaces simple two-ring cylindrical rear drive
  housings with six longitudinal loft stations. Their inboard roots flare
  while the exposed outlet tapers. Original 1/2/3-engine plans and
  nozzle core/energy rings remain intact.

Both operations have original authored lessons in
`training/curricula/vehicle_modeling_techniques.json`. Each includes
the modeling operation, reason to choose it, step-by-step geometry
recipe, known failure modes, and separately phrased text examples.

## Very important: no claim of watertight multi-part fusion

The cockpit shoulder is part of a single continuous hull topology; the
glass cabin remains a **distinct intersecting mesh**. Rear engine
housings likewise remain **separate closed shrouds**, partially inserted
into the hull. Neither change performs Boolean subtraction, physically
shared vertex loops between glass/metal, or a guaranteed watertight
hull-to-nacelle joint.

The future operation
`true_shared_seam_boolean_cutouts` is deliberately marked
*unimplemented*. It requires actual hull face removal, shared topology
or controlled remeshing, validation of normals, and inspection of
reflection continuity along those seams.

This distinction is part of teaching the model to explain its own
limits rather than confusing appearance and mesh topology.

## How they are evaluated

Four original hover-vehicle specifications generate ten variations each
(40 original GLBs). The independent GLB critic measures actual vertex
buffers and verifies the preexisting hard constraints: triangle quality,
engine/hover-unit counts, bracket reach, canopy clearance, and
mobile-favorable triangle budgets.

The design critic now also measures:
- `body_cockpit_shoulder_span`: upper hull breadth local to the cockpit.
- `engine_housing_flare_ratio`: relative nacelle ring radius range.
- `engine_housing_axial_sections`: number of actual longitudinal
  cross sections, including a minimum count for the profiled fairing.

The original authored operation lessons demand an isolated change to
the targeted geometric metric, with a real SHA-linked generated-GLB
before/after contrast on at least 3 out of 4 vehicle cases. The
multi-control `architectural` variant is for visual review **only**
because it cannot provide independent causal labels for one operator.

The text-to-operation selector is retrained and independently tested
from authored examples. Its performance measures recognition of
**documented techniques**, not a general 3D modeler's autonomous
reasoning. No unreviewed generated example is recycled as supervised
ground truth or production-quality approval.

## Next milestone

Open actual front, side, top and three-quarter renders of the
`architectural` and baseline GLBs; inspect engine/body overlap and
canopy/deck silhouette. If visible improvement is still too subtle,
the next work should be true hull cutouts, tangent-controlled lofts,
and normal-field continuity — not more caption statistics.
