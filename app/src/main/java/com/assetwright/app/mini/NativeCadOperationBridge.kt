package com.assetwright.app.mini

/**
 * Research-only typed CAD lesson -> ORIGINAL native geometry operations.
 *
 * Zero-to-CAD and DINOv2 teach and validate concepts; their source scripts,
 * model outputs and meshes NEVER execute in this Kotlin modeling engine.
 * Only these reviewed bounded controls can modify our own generated GLB.
 */
object NativeCadOperationBridge {
    const val REAR_SOCKET = "recess_rear_socket"
    const val COCKPIT_SHOULDER = "sculpt_cockpit_shoulder"
    const val REAR_NACELLE = "loft_rear_nacelle"
    const val LOWER_ROCKER = "recess_lower_rocker"

    val supportedOperations = setOf(REAR_SOCKET, COCKPIT_SHOULDER, REAR_NACELLE)

    /**
     * Native construction program: deterministic dependency order, exact
     * operation allowlist and unique bounded parameters. No downloaded
     * CadQuery scripts or outside meshes are ever executed.
     */
    data class Command(val operation: String, val strength: Float)

    // Frozen V1 order: do not change the accepted measured inverse study.
    val constructionOrder = listOf(COCKPIT_SHOULDER, REAR_SOCKET, REAR_NACELLE)

    // Separate V2 typed research grammar; no V2 learned planner is claimed.
    val expandedOperations = supportedOperations + LOWER_ROCKER
    val expandedConstructionOrder = listOf(
        COCKPIT_SHOULDER, LOWER_ROCKER, REAR_SOCKET, REAR_NACELLE
    )

    fun applyExpandedProgram(source: VehicleSpec, commands: List<Command>): VehicleSpec {
        require(commands.size in 1..4) { "Expected 1..4 V2 geometry operations" }
        val names = commands.map { it.operation }
        require(names.size == names.toSet().size) { "Repeated V2 operation" }
        require(names.all { it in expandedOperations }) { "Unknown V2 native operation" }
        require(names == names.sortedBy { expandedConstructionOrder.indexOf(it) }) {
            "V2 dependency violation: hull shaping, cutouts, then propulsion"
        }
        require(commands.all { it.strength.isFinite() && it.strength in 0f..1f }) {
            "V2 strengths must be finite and within 0..1"
        }
        var result = source
        for (command in commands) {
            result = if (command.operation == LOWER_ROCKER) {
                result.copy(designControls = result.designControls.copy(
                    rockerChannelRecess = command.strength))
            } else apply(result, command.operation, command.strength)
        }
        return result
    }

    fun applyProgram(source: VehicleSpec, commands: List<Command>): VehicleSpec {
        require(commands.size in 1..3) { "Expected 1..3 original geometry operations" }
        val names = commands.map { it.operation }
        require(names.size == names.toSet().size) { "Repeated modeling operation" }
        require(names.all { it in supportedOperations }) { "Unknown native operation" }
        require(names == names.sortedBy { constructionOrder.indexOf(it) }) {
            "Invalid operation dependency order: sculpt hull, recess, then shroud"
        }
        var result = source
        commands.forEach { result = apply(result, it.operation, it.strength) }
        return result
    }

    fun apply(spec: VehicleSpec, operation: String, depth: Float): VehicleSpec {
        require(operation in supportedOperations) {
            "Unimplemented native construction operation"
        }
        require(depth.isFinite() && depth in 0f..1f) {
            "Native modeling strength must be finite and within 0..1"
        }
        if (operation == REAR_SOCKET) require(spec.driveCount == 1) {
            "Blind rear socket requires one central engine"
        }
        val revised = when (operation) {
            REAR_SOCKET -> spec.designControls.copy(rearSocketDepth = depth)
            COCKPIT_SHOULDER -> spec.designControls.copy(cockpitShoulderTransition = depth)
            REAR_NACELLE -> spec.designControls.copy(rearNacelleShrouding = depth)
            else -> error("Operation allowlist exhaustiveness failure")
        }
        return spec.copy(designControls = revised)
    }
}
