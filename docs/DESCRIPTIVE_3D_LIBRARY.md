# Descriptive 3D library — licensed text/geometry training

## Why Assetwright needs this

Before this change, Forge's asset study downloaded at most eight models per
run and produced geometry measurements for only five distinct sources in
the first several cycles. That was useful for validating the Blender
workflow but far too small for general language-to-shape understanding.

The new library pass ingests **all model records** returned by the official
Poly Haven API, not just the eight geometry-download candidates.
Each record keeps the original publisher's object title, description,
category, tags, selected structured attributes, and published dimensions
when supplied. All records retain the source URL and CC0 provenance.

Unlike naive synthetic prompt generation, these captions correspond to
**actual cataloged 3D objects**. Do not invent descriptions or infer true
structural attachments from title keywords.

## What each stored record means

- `publisher_description`: human-authored publisher metadata, never an
  automatically asserted part/joint label.
- `dimension_ratios`: smallest/largest and middle/largest axis ratios
  computed from the publisher's dimensions (3D object bounding proportions).
- `verified_blender_geometry`: present only when an asset's actual official
  CC0 mesh has been processed successfully in the preceding Forge study.
- `description_quality`: missing, short, or substantive (60+ characters).
- `category`, `tags`, `facets`: metadata useful for material, object
  class, style and part-vocabulary research, not fabricated assembly plans.

All records have `license=CC0-1.0`, a model source link and
`description_origin=publisher_metadata`.

## Models, tests and boundaries

The pipeline builds a BM25 text reference-search index to find the best
actual catalog objects for a modeling prompt. It also trains a small
regularized hashed-word regression from descriptions and metadata to the
publisher's normalized 3D bounding ratios, with a **whole-object
held-out split**. A constant average-shape model serves as the baseline.

When enough labeled records are not available, or the candidate fails
to outperform the baseline, the model is rejected. No text-derived
geometry model is automatically published to Android. Instead, Forge can
use the library to locate relevant real references, inspect licensed
geometry where available, and create validated construction lessons.

Pipeline artifacts include:

- `descriptive_catalog.json`: detailed source-linked descriptions;
- `descriptive_catalog_report.json`: factual coverage and metadata counts;
- `reference_search_demo.json`: example text retrieval results;
- `text_shape_prior/evaluation.json`: held-out source-level model report;
- optionally `text_shape_prior/validated_prior.json`: gated descriptive
  bounding-ratio prior.

**Do not call retrieval a learned 3D construction process.** A true
description-to-mesh model needs many more licensed, verified
caption/geometry pairs, component-role labels, attachment constraints,
and actual generated-mesh evaluation. Published bounding dimensions are
a useful first grounding signal but do not encode contours or topology.

## Future larger library sources

Objaverse 1.0 offers hundreds of thousands of annotated objects, and Cap3D
publishes more than one million generated object captions. Cap3D captions
are licensed under **ODC-By 1.0** and the originating Objaverse objects
carry **individual license metadata** (including some noncommercial
restrictions). They must not be assumed CC0 or automatically copied into
Assetwright's public/Android feeds.

A future gated provider may import captions with required attribution,
filter objects individually by verified license, and record caption-vs-mesh
matching proof. Do not use the unfiltered dataset for commercial training
or redistribute asset meshes without confirming their provenance.

References:
- https://api.polyhaven.com
- https://github.com/Poly-Haven/Public-API/blob/master/ToS.md
- https://polyhaven.com/license
- https://objaverse.allenai.org/docs/objaverse-1.0/
- https://huggingface.co/datasets/tiange/Cap3D

Research ingestion is initiated by Forge's prompt-triggered GitHub Actions,
not a persistent ChatGPT daemon. The Android model and local user data
remain separate from these research artifacts.
