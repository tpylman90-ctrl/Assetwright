package com.assetwright.app.mini

import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/**
 * Exports REAL MiniGeometry / GlbWriter outputs as independent public CI
 * benchmark fixtures; none are private user samples or imported models.
 * Only runs when Android CI sets ASSETWRIGHT_BENCHMARK_OUT.
 */
class GeneratorBenchmarkExportTest {
    private data class Case(
        val id: String, val prompt: String,
        val length: Float, val width: Float, val roof: Float,
        val canopy: Float, val nose: Float, val rear: Float,
        val lift: Int, val mount: String
    )

    private val cases = listOf(
        Case("racer_exposed", "Aggressive hover racer with four exposed repulsors and twin engines",
            4.85f, 2.40f, 1.34f, 1.75f, .47f, 1.14f, 4, "exposed"),
        Case("suv_tucked", "Wide hover SUV with six tucked repulsors and three engines",
            5.55f, 2.75f, 1.92f, 2.20f, .63f, 1.19f, 6, "tucked"),
        Case("coupe_exposed", "Fast hover coupe with two exposed repulsors and one engine",
            4.45f, 2.18f, 1.27f, 1.55f, .42f, 1.08f, 2, "exposed"),
        Case("suv_hidden", "Compact hover SUV with four hidden lift pads and twin engines",
            4.75f, 2.38f, 1.72f, 1.85f, .58f, 1.13f, 4, "tucked")
    )

    private fun esc(s: String): String =
        s.replace("\\", "\\\\").replace("\"", "\\\"")

    @Test
    fun exportControlledOriginalVehicleVariationsForIndependentGlbQualityAudit() {
        val location = System.getenv("ASSETWRIGHT_BENCHMARK_OUT")?.takeIf { it.isNotBlank() }
            ?: return // No writes during ordinary local test runs.
        val root = Path.of(location)
        Files.createDirectories(root)
        var wrote = 0
        for (scenario in cases) {
            val original = VehicleSpec(
                scenario.id, scenario.length, scenario.width, scenario.roof,
                scenario.canopy, scenario.nose, scenario.rear, "Mobile",
                scenario.prompt, ConstructionPlan(scenario.lift, scenario.mount)
            )
            val variations = listOf(
                "baseline" to original,
                "roof_plus" to original.copy(roofHeight = original.roofHeight + .13f),
                "nose_sculpt" to original.copy(
                    noseTaper = (original.noseTaper - .07f).coerceAtLeast(.27f)),
                "wider_haunch" to original.copy(
                    rearHaunch = (original.rearHaunch + .045f).coerceAtMost(1.3f)),
                "sculpted_canopy" to original.copy(
                    designControls = VehicleDesignControls(canopySquareness = .85f)),
                "faired_mounts" to original.copy(
                    designControls = VehicleDesignControls(fairedRepulsorMounts = 1f)),
                "integrated_aero" to original.copy(
                    designControls = VehicleDesignControls(
                        canopySquareness = .85f,
                        shoulderDefinition = .80f,
                        fairedRepulsorMounts = 1f))
            )
            for ((variant, spec) in variations) {
                val stem = scenario.id + "__" + variant
                val generated = MiniGeometry.generate(spec)
                val glb = GlbWriter.encode(generated)
                assertTrue("Unexpectedly small generated GLB", glb.size > 2000)
                val digest = MessageDigest.getInstance("SHA-256")
                    .digest(glb).joinToString("") { "%02x".format(it.toInt() and 255) }
                Files.write(root.resolve(stem + ".glb"), glb)
                val target = "{\"schema\":\"assetwright-generated-vehicle-target-v1\"," +
                    "\"original_procedural_asset\":true," +
                    "\"case\":\"" + esc(scenario.id) + "\"," +
                    "\"variant\":\"" + esc(variant) + "\"," +
                    "\"prompt\":\"" + esc(spec.sourcePrompt) + "\"," +
                    "\"lift_cells\":" + spec.liftCount + "," +
                    "\"mount\":\"" + spec.liftMount + "\"," +
                    "\"drive_count\":" + spec.driveCount + "," +
                    "\"roof_height\":" + spec.roofHeight + "," +
                    "\"source_glb_sha256\":\"" + digest + "\"," +
                    "\"expected_engine\":\"android-native-MiniGeometry\"}"
                Files.write(root.resolve(stem + ".json"), target.toByteArray(Charsets.UTF_8))
                wrote++
            }
        }
        assertTrue("Incorrect number of generated GLB samples", wrote == 28)
    }
}
