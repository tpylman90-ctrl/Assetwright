package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Export ONLY original MiniGeometry meshes for supervised inverse-recipe study.
 * No external mesh model is used. Ordinary tests do nothing unless the
 * ASSETWRIGHT_TRANSFER_OUT environment variable is explicitly set.
 */
class VisualTransferExportTest {
    private fun esc(value: String): String =
        value.replace("\\", "\\\\").replace("\"", "\\\"")

    @Test
    fun exportOriginalGeometryForOptionalVisualTransferStudy() {
        val destination = System.getenv("ASSETWRIGHT_TRANSFER_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root = Path.of(destination)
        Files.createDirectories(root)
        val types = listOf("racer", "coupe", "suv")
        val lengths = listOf("compact", "balanced", "elongated")
        val cabins = listOf("low swept canopy", "raised touring cabin",
            "wide panoramic canopy", "sharp tapered nose")
        var count = 0
        for (kind in types.indices) for (stretch in lengths.indices) for (roof in cabins.indices) {
            val category = types[kind]
            val size = lengths[stretch]
            val description = cabins[roof]
            val ident = "own_" + category + "_" + size + "_option" + roof
            val propulsion = listOf("single engine", "twin engines", "three engines")[kind]
            val prompt = "Original $size hover $category with $description and $propulsion"
            val length = 4.35f + .48f * stretch + .22f * kind
            val width = 1.90f + .22f * kind + if (roof == 2) .23f else .04f
            val roofHeight = 1.27f + .13f * kind + if (roof == 1) .26f else .045f
            val canopyLength = 1.40f + .17f * stretch + if (roof == 2) .28f else .1f
            val noseTaper = .49f - (if (roof == 3) .09f else 0f) + .025f * kind
            val rearHaunch = 1.04f + .035f * kind + .015f * stretch
            val plan = ConstructionPlan(if (kind == 2) 6 else 4,
                if (kind == 0) "exposed" else "tucked")
            val spec = VehicleSpec(ident, length, width, roofHeight,
                canopyLength, noseTaper, rearHaunch,
                "Mobile", prompt, plan)
            val glb = GlbWriter.encode(MiniGeometry.generate(spec))
            require(glb.size > 2000) { "Original GLB generation failed" }
            val sha = MessageDigest.getInstance("SHA-256").digest(glb)
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            val stem = ident + "__baseline"
            Files.write(root.resolve("$stem.glb"), glb)
            // Exact values passed to the native construction engine.
            val target = "{\"schema\":\"assetwright-generated-vehicle-target-v1\"," +
                "\"original_procedural_asset\":true," +
                "\"case\":\"" + esc(ident) + "\"," +
                "\"variant\":\"baseline\"," +
                "\"prompt\":\"" + esc(prompt) + "\"," +
                "\"parameters\":{\"length\":" + length +
                ",\"width\":" + width +
                ",\"roof_height\":" + roofHeight +
                ",\"canopy_length\":" + canopyLength +
                ",\"nose_taper\":" + noseTaper +
                ",\"rear_haunch\":" + rearHaunch + "}," +
                "\"lift_cells\":" + plan.liftCells + "," +
                "\"mount\":\"" + plan.mount + "\"," +
                "\"drive_count\":" + spec.driveCount + "," +
                "\"roof_height\":" + roofHeight + "," +
                "\"source_glb_sha256\":\"" + sha + "\"," +
                "\"expected_engine\":\"android-native-MiniGeometry\"}"
            Files.write(root.resolve("$stem.json"), target.toByteArray(Charsets.UTF_8))
            count++
        }
        assertEquals(36, count)
    }
}
