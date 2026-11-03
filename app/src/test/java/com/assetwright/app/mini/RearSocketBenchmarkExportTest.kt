package com.assetwright.app.mini

import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/**
 * Two original, native MiniGeometry exports for an independently audited
 * CAD-inspired blind-socket operation. Never imports an outside mesh.
 */
class RearSocketBenchmarkExportTest {
    @Test
    fun exportActualConnectedSocketAndBaselineForIndependentTopologyReview() {
        val dest = System.getenv("ASSETWRIGHT_SOCKET_BENCHMARK_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root = Path.of(dest)
        Files.createDirectories(root)
        val description = "Original hover coupe with one rear engine"
        val baseline = VehicleSpec(
            "native_socket", 4.45f, 2.18f, 1.27f, 1.55f,
            .42f, 1.08f, "Mobile", description,
            ConstructionPlan(2, "exposed")
        )
        assertTrue(baseline.driveCount == 1)
        val proposal = System.getenv("ASSETWRIGHT_NATIVE_OPERATION_PROPOSAL")
        val shaped = if (proposal.isNullOrBlank()) {
            NativeCadOperationBridge.apply(
                baseline, NativeCadOperationBridge.REAR_SOCKET, 1f)
        } else {
            val props = Properties()
            Files.newBufferedReader(Path.of(proposal)).use { props.load(it) }
            require(props.stringPropertyNames() ==
                setOf("schema", "operation", "depth", "external_mesh_used"))
            require(props.getProperty("schema") ==
                "assetwright-reviewed-native-operation-request-v1")
            require(props.getProperty("external_mesh_used") == "false")
            NativeCadOperationBridge.apply(baseline,
                props.getProperty("operation"),
                props.getProperty("depth").toFloat())
        }
        for ((variant, spec) in listOf(
            "baseline" to baseline,
            "socket_recess" to shaped
        )) {
            val glb = GlbWriter.encode(MiniGeometry.generate(spec))
            assertTrue(glb.size > 2000)
            val sha = MessageDigest.getInstance("SHA-256").digest(glb)
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            val stem = "native_socket__" + variant
            Files.write(root.resolve(stem + ".glb"),glb)
            // This is the source-of-truth record for the independent critic.
            val metadata = "{\"schema\":\"assetwright-native-socket-target-v1\"," +
                "\"original_procedural_asset\":true," +
                "\"expected_engine\":\"android-native-MiniGeometry\"," +
                "\"case\":\"native_socket\"," +
                "\"variant\":\"" + variant + "\"," +
                "\"drive_count\":1," +
                "\"roof_height\":" + spec.roofHeight + "," +
                "\"rear_socket_depth\":" + spec.designControls.rearSocketDepth + "," +
                "\"source_glb_sha256\":\"" + sha + "\"}"
            Files.write(root.resolve(stem + ".json"),metadata.toByteArray(Charsets.UTF_8))
        }
    }
}
