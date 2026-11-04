package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.math.abs

/**
 * V2 development geometry only; NOT a new blind benchmark or trained model.
 * All GLBs are original MiniGeometry/GlbWriter outputs.
 */
class NativeRockerV2Test {
    private fun sample(family: String) = when (family) {
        "rockerdev_a" -> VehicleSpec(
            "Development roadster", 4.75f, 2.31f, 1.34f, 1.70f, .48f, 1.10f,
            "High detail", "Original roadster with one central engine",
            ConstructionPlan(4, "exposed"))
        "rockerdev_b" -> VehicleSpec(
            "Development hauler", 5.80f, 2.67f, 1.75f, 2.06f, .57f, 1.22f,
            "High detail", "Original hauler with one central engine",
            ConstructionPlan(4, "exposed"))
        else -> error("Unknown V2 development family")
    }

    private fun channelHalfSpan(spec: VehicleSpec): Float {
        val hull = MiniGeometry.generate(spec).parts.single {
            it.name == "Sculpted continuous body"
        }
        // Homologous t=-.05 native axial, theta=315 degree lower hull.
        val ring = hull.vertices.chunked(spec.radialSegments).single { row ->
            abs(row.first().y + .05f * spec.length) < .001f
        }
        return abs(ring[spec.radialSegments * 7 / 8].x)
    }

    private fun undersideMinHeight(spec: VehicleSpec): Float {
        val hull = MiniGeometry.generate(spec).parts.single {
            it.name == "Sculpted continuous body"
        }
        val ring = hull.vertices.chunked(spec.radialSegments).single { row ->
            abs(row.first().y + .05f * spec.length) < .001f
        }
        return ring.filter { abs(it.x) < .002f }.minOf { it.z }
    }

    private fun rejects(block: () -> Unit) {
        var rejected = false
        try { block() } catch (_: IllegalArgumentException) { rejected = true }
        assertTrue("Invalid native program was accepted", rejected)
    }

    @Test
    fun lowerChannelIsMonotoneConnectedHullDeformationNotAnOverlay() {
        for (family in listOf("rockerdev_a", "rockerdev_b")) {
            val spec = sample(family)
            val base = MiniGeometry.generate(spec)
            val original = channelHalfSpan(spec)
            var previous = original
            var bottom = undersideMinHeight(spec)
            val originalBottom = bottom
            for (strength in listOf(.25f, .50f, .90f)) {
                val changed = NativeCadOperationBridge.applyExpandedProgram(
                    spec, listOf(NativeCadOperationBridge.Command(
                        NativeCadOperationBridge.LOWER_ROCKER, strength)))
                val asset = MiniGeometry.generate(changed)
                val span = channelHalfSpan(changed)
                assertTrue("Corresponding source hull vertices must actually move",
                    previous - span > .012f)
                previous = span
                val raised = undersideMinHeight(changed)
                assertTrue("The V2 side-view underbody silhouette must move",
                    raised - bottom > .015f)
                bottom = raised
                assertEquals("No new floating body parts", base.parts.size, asset.parts.size)
                assertTrue("The surface needs local smooth profile stations",
                    asset.parts.first().vertices.size > base.parts.first().vertices.size)
                assertTrue(asset.triangleCount <= 12000)
                assertTrue(ShapeProgram.steps(changed).any {
                    it.operation == NativeCadOperationBridge.LOWER_ROCKER })
            }
            assertTrue(original - previous > .15f)
            assertTrue("A shallow recess cannot satisfy the visual-review correction",
                bottom - originalBottom > .075f)
            assertTrue(ShapeProgram.steps(spec).none {
                it.operation == NativeCadOperationBridge.LOWER_ROCKER })
        }
    }

    @Test
    fun expandedProgramEnforcesFourUniqueTypedDependentOperations() {
        val spec = sample("rockerdev_a")
        val order = NativeCadOperationBridge.expandedConstructionOrder
        val commands = order.map { NativeCadOperationBridge.Command(it, .725f) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(spec, commands.reversed()) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(spec, commands + commands[0]) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(
            spec, commands.take(3) + commands[1]) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(
            spec, listOf(NativeCadOperationBridge.Command("import_teacher_mesh", .5f))) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(
            spec, listOf(NativeCadOperationBridge.Command(order[1], Float.NaN))) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(
            spec, listOf(NativeCadOperationBridge.Command(order[1], 1.1f))) }
        rejects { NativeCadOperationBridge.applyExpandedProgram(
            spec.copy(sourcePrompt = "Hover racer with twin engines"),
            listOf(commands[2])) }
        rejects { NativeCadOperationBridge.applyProgram(spec, listOf(commands[1])) }
        val combined = NativeCadOperationBridge.applyExpandedProgram(spec, commands)
        assertEquals(order, ShapeProgram.steps(combined).map { it.operation }
            .filter { it in order })
        val geometry = MiniGeometry.generate(combined)
        assertEquals(MiniGeometry.generate(spec).parts.size, geometry.parts.size)
        assertTrue(geometry.triangleCount <= 12000)
        assertTrue(channelHalfSpan(combined) < channelHalfSpan(spec) - .065f)
        assertEquals(3, NativeCadOperationBridge.constructionOrder.size)
    }

    private fun write(root: Path, family: String, name: String,
                      commands: List<NativeCadOperationBridge.Command>) {
        val base = sample(family)
        val spec = if (commands.isEmpty()) base else
            NativeCadOperationBridge.applyExpandedProgram(base, commands)
        val glb = GlbWriter.encode(MiniGeometry.generate(spec))
        val sha = MessageDigest.getInstance("SHA-256").digest(glb).joinToString("") {
            "%02x".format(it.toInt() and 255)
        }
        val stem = family + "__" + name
        Files.write(root.resolve(stem + ".glb"), glb)
        val operations = commands.joinToString(",") {
            "{\"operation\":\"" + it.operation + "\",\"strength\":" + it.strength + "}"
        }
        val meta = "{\"schema\":\"assetwright-native-rocker-v2-development\"," +
            "\"generator\":\"android-native-MiniGeometry\",\"phase\":\"development\"," +
            "\"family\":\"" + family + "\",\"case\":\"" + stem + "\"," +
            "\"source_glb_sha256\":\"" + sha + "\",\"commands\":[" + operations + "]}"
        Files.write(root.resolve(stem + ".json"), meta.toByteArray(Charsets.UTF_8))
    }

    @Test
    fun exportOriginalGLBsForIndependentV2DevelopmentAudit() {
        val location = System.getenv("ASSETWRIGHT_ROCKER_V2_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root = Path.of(location)
        Files.createDirectories(root)
        for (family in listOf("rockerdev_a", "rockerdev_b")) {
            write(root, family, "baseline", emptyList())
            for ((label, strength) in listOf(
                "s250" to .25f, "s500" to .50f, "s900" to .90f)) {
                write(root, family, label, listOf(
                    NativeCadOperationBridge.Command(
                        NativeCadOperationBridge.LOWER_ROCKER, strength)))
            }
            write(root, family, "combined_four", NativeCadOperationBridge
                .expandedConstructionOrder.map {
                    NativeCadOperationBridge.Command(it, .725f)
                })
        }
    }
}
