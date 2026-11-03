package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/** Research-only: native GLBs from actual trained operator/strength proposals. */
class NativePlannerBenchmarkExportTest {
    @Test
    fun independentlyInferredOperationsProduceOurOriginalGLBs() {
        val source = System.getenv("ASSETWRIGHT_NATIVE_PLANNER_BATCH")
            ?.takeIf { it.isNotBlank() } ?: return
        val destination = System.getenv("ASSETWRIGHT_NATIVE_PLANNER_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val plan = Properties()
        Files.newBufferedReader(Path.of(source)).use { plan.load(it) }
        val required = mutableSetOf("schema", "external_mesh_used", "count", "model_sha256")
        for (index in 0..2) {
            required += "proposal$index.operation"
            required += "proposal$index.strength"
        }
        require(plan.stringPropertyNames() == required)
        require(plan.getProperty("schema") == "assetwright-owned-native-planner-batch-v1")
        require(plan.getProperty("external_mesh_used") == "false")
        require(plan.getProperty("count") == "3")
        require(Regex("[0-9a-f]{64}").matches(plan.getProperty("model_sha256")))
        val root = Path.of(destination)
        Files.createDirectories(root)
        val base = VehicleSpec(
            "Learned native operations", 4.45f, 2.18f, 1.27f, 1.55f,
            .42f, 1.08f, "Mobile",
            "Original hover coupe with one rear engine",
            ConstructionPlan(2, "exposed")
        )
        assertEquals(1, base.driveCount)
        val order = listOf(
            NativeCadOperationBridge.REAR_SOCKET,
            NativeCadOperationBridge.COCKPIT_SHOULDER,
            NativeCadOperationBridge.REAR_NACELLE
        )
        val samples = mutableListOf(Triple("baseline", base, 0f))
        for (index in order.indices) {
            val operation = plan.getProperty("proposal$index.operation")
            // A classifier error is a failure, never a silent handcoded fallback.
            require(operation == order[index]) {
                "Owned student chose an unexpected native modeling operation"
            }
            val strength = plan.getProperty("proposal$index.strength").toFloat()
            require(strength in .45f..1f)
            val generated = NativeCadOperationBridge.apply(base, operation, strength)
            assertTrue(ShapeProgram.steps(generated).any { it.operation == operation })
            samples += Triple(operation,generated,strength)
        }
        for ((variant,spec,strength) in samples) {
            val bytes = GlbWriter.encode(MiniGeometry.generate(spec))
            assertTrue("Invalid original native mesh export", bytes.size > 2000)
            val checksum = MessageDigest.getInstance("SHA-256")
                .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
            val stem = "native_planner__" + variant
            Files.write(root.resolve(stem + ".glb"),bytes)
            val meta = "{\"schema\":\"assetwright-owned-native-planner-glb-v1\"," +
                "\"source_engine\":\"android-native-MiniGeometry\"," +
                "\"original_procedural_asset\":true," +
                "\"variant\":\"" + variant + "\"," +
                "\"strength\":" + strength + "," +
                "\"model_sha256\":\"" + plan.getProperty("model_sha256") + "\"," +
                "\"source_glb_sha256\":\"" + checksum + "\"}"
            Files.write(root.resolve(stem + ".json"),meta.toByteArray(Charsets.UTF_8))
        }
        assertEquals(4,samples.size)
    }
}
