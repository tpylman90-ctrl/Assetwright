package com.assetwright.app.mini

import org.json.JSONArray
import org.json.JSONObject

/**
 * Procedural construction recipe: describes HOW the current native geometry
 * engine assembles a vehicle, without saving any mesh vertices or GLB files.
 *
 * The operation vocabulary is deterministic in v0.5. Future geometry-learning
 * work can use reviewed recipes as labeled construction sequences.
 */
object ShapeProgram {
    const val SCHEMA = "assetwright-shape-program-v1"
    data class Step(
        val operation: String,
        val component: String,
        val dependsOn: List<String>,
        val parameters: Map<String, Double>
    )

    fun steps(spec: VehicleSpec): List<Step> = listOf(
        Step("loft_shell", "hull", emptyList(), mapOf(
            "length" to spec.length.toDouble(),
            "width" to spec.width.toDouble(),
            "nose_taper" to spec.noseTaper.toDouble(),
            "rear_haunch" to spec.rearHaunch.toDouble(),
            "ring_resolution" to spec.radialSegments.toDouble()
        )),
        Step("loft_fitted_canopy", "greenhouse", listOf("hull"), mapOf(
            "canopy_length" to spec.canopyLength.toDouble(),
            "roof_height" to spec.roofHeight.toDouble()
        )),
        Step("loft_keel", "undercarriage", listOf("hull"), emptyMap()),
        Step("attach_rear_drive", "propulsion", listOf("hull"), mapOf(
            "housings" to spec.driveCount.toDouble(), "rear_haunch" to spec.rearHaunch.toDouble()
        )),
        Step("attach_repulsor_mounts", "mount_brackets",
            listOf("undercarriage"), mapOf(
                "brackets" to spec.liftCount.toDouble(),
                "outboard" to if (spec.liftMount == "exposed") 1.0 else 0.0
            )),
        Step("attach_repulsors", "hover_units", listOf("mount_brackets"), mapOf(
            "repulsors" to spec.liftCount.toDouble(),
            "mount_outboard" to if (spec.liftMount == "exposed") 1.0 else 0.0
        )),
        Step("attach_light_strip", "lighting", listOf("hull"), emptyMap())
    ) + if (spec.driveCount == 1 && spec.designControls.rearSocketDepth > 0f) {
        listOf(Step("recess_rear_socket", "hull", listOf("hull"),
            mapOf("socket_depth" to
                (.085 + .16 * spec.designControls.rearSocketDepth.coerceIn(0f, 1f)))))
    } else emptyList()

    fun toJson(spec: VehicleSpec): JSONObject {
        val ops = JSONArray()
        for (step in steps(spec)) {
            val data = JSONObject()
            for ((name, value) in step.parameters) data.put(name, value)
            ops.put(JSONObject()
                .put("operation", step.operation)
                .put("component", step.component)
                .put("depends_on", JSONArray(step.dependsOn))
                .put("parameters", data))
        }
        return JSONObject()
            .put("schema", SCHEMA)
            .put("asset_family", "hover-vehicle")
            .put("prompt", spec.sourcePrompt)
            .put("geometry_engine", "android-native-procedural-v1")
            .put("operation_sequence", ops)
    }
}
