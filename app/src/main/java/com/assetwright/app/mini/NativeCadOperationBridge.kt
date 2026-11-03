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

    val supportedOperations = setOf(REAR_SOCKET, COCKPIT_SHOULDER, REAR_NACELLE)

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
