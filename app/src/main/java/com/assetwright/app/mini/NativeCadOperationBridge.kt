package com.assetwright.app.mini

/**
 * An intentionally tiny, typed adapter from a reviewed CAD-operation lesson
 * into an actual native modeling operation. Not an arbitrary script runner.
 *
 * The learned research policy is not deployed on Android: caller must supply
 * a reviewed, allowlisted operation and bounded parameter. MiniGeometry owns
 * and emits every resulting polygon.
 */
object NativeCadOperationBridge {
    const val REAR_SOCKET = "recess_rear_socket"

    fun apply(spec: VehicleSpec, operation: String, depth: Float): VehicleSpec {
        require(operation == REAR_SOCKET) { "Operation is not implemented natively" }
        require(depth.isFinite() && depth in 0f..1f) {
            "Native modeling depth is outside verified bounds"
        }
        require(spec.driveCount == 1) {
            "Blind circular socket experiment requires one central engine"
        }
        return spec.copy(designControls =
            spec.designControls.copy(rearSocketDepth = depth))
    }
}
