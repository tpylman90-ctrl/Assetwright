# Assetwright Geometry Lab — dual display modes (Android v0.7.6)

The same unmodified, imported GLB is used in both modes. Switch directly between them without reopening or changing the model. Orbit/zoom, source-part selection, isolation, and component diagnostics remain available in both.

## Geometry Inspection (default)

- Neutral gray-blue clay shading with a depth-tested full-resolution GPU view
- Source-part selection/highlight; hide all other parts using **Isolate selected**
- Source-named glass/glazing treated as translucent for machinery inspection
- Geometry Lab's separate slicer, curvature, sharp-edge, and topology reports remain below the viewer
- Surface material color, metalness, roughness, and emission intentionally **ignored**
- GLB source is never edited, baked, or rewritten

## Material Preview

- glTF 2.0 PBR metallic/roughness pipeline **per actual GLB primitive material assignment**
- BaseColorFactor and embedded PNG/JPEG/WebP base-color map (linear-space/sRGB-aware)
- MetallicFactor/RoughnessFactor; metallic-roughness map uses **B channel metalness, G channel roughness**
- glTF emissive factor, KHR_materials_emissive_strength, and emissive texture (self-illumination, *not* bloom or light casting)
- Tangent-space normal maps computed using per-pixel screen derivatives, including normalScale
- Embedded texture UVs TEXCOORD_0 and TEXCOORD_1, and KHR_texture_transform
- glTF alpha OPAQUE, MASK, and BLEND materials; does not guess transparency from object names
- Real UV-based texture sampling, glTF wrapping/filters and per-texture mipmaps
- Fixed two-light-like PBR-inspired studio preview, with direct GGX shading and approximate ambient terms, **not** an IBL/HDRI-correct reference renderer
- Texture decoding is downsampled to at most 2048 px and subject to a 96 MiB GPU image budget. When a texture is unsupported, the shader falls back to its factor color; the app lists missing/unsupported images.

## Import requirements

Standard binary glTF 2.0 GLB and EXT_meshopt_compression triangle geometry are supported. Android v0.7.7 also imports KHR_draco_mesh_compression triangle geometry in both display modes. Texture images need to be embedded in the GLB or supplied as data URIs, so that the Android file picker does not need external asset links.

KTX2/Basis (KHR_texture_basisu), URI-referenced external files and advanced material extensions (clearcoat, transmission, sheen, iridescence, anisotropy, specular, volume) are **not** fully supported in this version. Such models may display only partial material fidelity. Imported source files remain unchanged.

### Suggested inspection test

1. Load the original Vantage GLB with embedded base-color, ORM and normal textures.
2. Switch to Geometry Inspection, orbit, select a part and inspect the clay surfaces.
3. Switch to Material Preview **without reimporting the model**; confirm the model shows its original textures.
4. Select a part to read its imported material name, roughness, metalness and alpha mode.
5. Compare to a textured GLB viewer and send a screenshot. Actual performance and fidelity still need device validation.

## Source components vs materials

GLB component identity comes from scene nodes/mesh primitives, not a guessed semantic classifier. Different primitives within a mechanical assembly may use different materials. Part reports analyze original mesh geometry irrespective of active display mode. The Material Preview does not train an AI or change reconstruction accuracy by itself; it makes reference materials available for visual validation.
