package com.assetwright.app.geometry

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.*

/**
 * Compact assistant-readable GLB analysis derived entirely from this mesh.
 * No source/model mutation, no inference about material or semantic part labels.
 * Use the desktop packet for comprehensive cross-section envelopes/patch analysis.
 */
fun GeometryMesh.modelingPacket(axis: Int, reference: GeometryMesh? = null): String {
    require(axis in 0..2) { "Invalid length axis" }
    val out = JSONObject()
    out.put("schema", "assetwright.mobile_modeling_packet.v1")
    out.put("source_file", name)
    out.put("geometry_only", true)
    out.put("original_model_modified", false)
    out.put("axis", axis)
    out.put("units", "source units; do not assume metres")
    out.put("vertex_count", n)
    out.put("triangle_count", count)
    out.put("bounds", JSONArray(limits.map { it.toDouble() }))
    out.put("dimensions", JSONArray((0..2).map { (limits[it + 3] - limits[it]).toDouble() }))

    fun histogram(values: FloatArray, low: Float, high: Float, bins: Int): JSONObject {
        val counts = IntArray(bins)
        for (value in values) {
            if (!value.isFinite()) continue
            val index = (((value - low) / (high - low)) * bins).toInt().coerceIn(0, bins - 1)
            counts[index]++
        }
        return JSONObject()
            .put("range", JSONArray(listOf(low, high)))
            .put("counts", JSONArray(counts.toList()))
            .put("bin_count", bins)
    }

    val signals = JSONObject()
    signals.put("local_signed_bending_proxy", histogram(curvature, -1f, 1f, 20))
    signals.put("edge_crease_angle_degrees", histogram(sharpness, 0f, 180f, 18))
    signals.put("candidate_ridge_vertices", curvature.count { it > 0.08f })
    signals.put("candidate_valley_vertices", curvature.count { it < -0.08f })
    signals.put("candidate_sharp_edge_vertices", sharpness.count { it >= 35f })
    signals.put("connected_index_islands", (islands.maxOrNull() ?: -1) + 1)
    out.put("surface_signals", signals)

    // True triangle/plane intersections, summarized by station.
    // Unlike a photograph, these are actual geometric measurements; however,
    // multi-component, concave and open sections are NOT converted into solid contours.
    val profiles = JSONArray()
    val across = (0..2).filter { it != axis }
    val sections = 15
    for (station in 0 until sections) {
        val fraction = (station + 1f) / (sections + 1f)
        val segments = slice(axis, fraction)
        val section = JSONObject()
        section.put("fraction", fraction.toDouble())
        section.put("cross_section_axes", JSONArray(across))
        section.put("segment_count", segments.size)
        if (segments.isNotEmpty()) {
            val lo = FloatArray(2) { Float.POSITIVE_INFINITY }
            val hi = FloatArray(2) { Float.NEGATIVE_INFINITY }
            for (seg in segments) {
                for (p in arrayOf(seg.a, seg.b)) for (d in 0..1) {
                    lo[d] = min(lo[d], p[across[d]])
                    hi[d] = max(hi[d], p[across[d]])
                }
            }
            section.put("extent_min", JSONArray(lo.toList()))
            section.put("extent_max", JSONArray(hi.toList()))
            section.put("extent_size", JSONArray(listOf(hi[0] - lo[0], hi[1] - lo[1])))
            val samples = JSONArray()
            // Representative measured segment endpoints, not a full ordered outline.
            val step = max(1, segments.size / 48)
            for (i in segments.indices step step) {
                if (samples.length() >= 48) break
                val seg = segments[i]
                samples.put(JSONArray(listOf(
                    JSONArray(seg.a.map { it.toDouble() }),
                    JSONArray(seg.b.map { it.toDouble() })
                )))
            }
            section.put("sample_intersection_segments_xyz", samples)
        }
        profiles.put(section)
    }
    out.put("cross_section_stations", profiles)

    // Separate top, side and end vertex-based silhouette envelopes.
    val views = JSONObject()
    for ((axisName, projectedAxis) in listOf("side" to 0, "top" to 1, "end" to 2)) {
        val envelope = silhouette(projectedAxis, 72)
        val points = JSONArray()
        for (i in envelope.indices step 2) {
            if (i + 1 >= envelope.size) break
            points.put(JSONArray(listOf(
                envelope[i][0].toDouble(),
                envelope[i][1].toDouble(),
                envelope[i + 1][1].toDouble()
            )))
        }
        views.put(axisName, points)
    }
    out.put("orthographic_vertex_envelopes", views)

    val difference = if (reference != null) {
        val values = compare(reference)
        JSONObject()
            .put("reference_file", reference.name)
            .put("a_to_b_mean_normalized_sampled_vertex_distance", values[0].toDouble())
            .put("b_to_a_mean_normalized_sampled_vertex_distance", values[1].toDouble())
            .put("warning", "No ICP registration. Bounding-box-aligned vertex approximation only.")
    } else JSONObject().put("status", "Reference model not loaded")
    out.put("reference_comparison", difference)

    out.put("recommended_modeling_sequence", JSONArray(listOf(
        "Trace the station extents and front/side/top envelopes to reconstruct proportions.",
        "Build the continuous primary shell first, before detail panels.",
        "Plan deliberate hard edges from the crease distribution and inspected images.",
        "Use separate editable assemblies for vents, mechanical parts and cabin.",
        "Compare a new GLB by matching relative station widths and silhouette shape.",
        "Preserve the original GLB and store each experimental edit separately."
    )))
    out.put("accuracy_notes", JSONArray(listOf(
        "Curvature is a local mesh-dependent bending proxy, not principal curvature.",
        "Triangles and open boundaries are not proof of modeling quality.",
        "Cross-section segment samples are not full loops or hole-aware reconstruction.",
        "Connected index islands are not semantic vehicle parts.",
        "Only geometry analysis is included; material appearance is not encoded.",
        "There is no automatic neural training or persistent learned weights."
    )))
    return out.toString(2)
}
