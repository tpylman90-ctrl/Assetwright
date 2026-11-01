package com.assetwright.app.mini

import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Test

class MiniAiTest {
    @Test
    fun recognizesSupportedFamilyWithoutInternet() {
        assertTrue(MiniAi.supports("A wide hover SUV with a long canopy"))
        assertTrue(MiniAi.supports("A hoover racer"))
        assertFalse(MiniAi.supports("A fantasy sword"))
    }

    @Test
    fun exactApprovedCorrectionOverridesOriginalSeed() {
        val approved = TrainingExample(
            "wide hover suv", 6.1f, 2.8f, 1.9f, 2.5f, 0.48f, 1.2f
        )
        val seed = TrainingExample(
            "wide hover suv", 4.9f, 2.2f, 1.6f, 1.7f, 0.55f, 1.05f
        )
        val result = MiniAi.predict("Wide Hover SUV", "Mobile", listOf(approved, seed))
        assertEquals(approved.width, result.width, 0.0001f)
        assertEquals(approved.length, result.length, 0.0001f)
        assertEquals(approved.roofHeight, result.roofHeight, 0.0001f)
    }

    @Test
    fun explicitEngineCountsChangeConstructionAndExportedRecipe() {
        val samples = listOf(
            "a hover coupe with one rear engine" to 1,
            "a hover racer with twin thrusters" to 2,
            "a hover vehicle with three engines" to 3,
            "a hoover suv with 3 rear boosters" to 3,
            "a hover coupe with engines x3" to 3,
            "a hover racer with no engine count given" to 2
        )
        val baseline = listOf(
            TrainingExample("hover coupe", 4.8f, 2.3f, 1.5f, 1.8f, 0.5f, 1.1f)
        )
        for ((prompt, expectedCount) in samples) {
            val spec = MiniAi.predict(prompt, "Mobile", baseline)
            assertEquals("Incorrect engine count for " + prompt, expectedCount, spec.driveCount)
            val asset = MiniGeometry.generate(spec)
            val houses = asset.parts.filter { it.name.endsWith("housing") }
            val cores = asset.parts.filter { it.name.endsWith("core") }
            val energy = asset.parts.filter { it.name.endsWith("energy ring") }
            assertEquals("Engine geometry mismatch for " + prompt, expectedCount, houses.size)
            assertEquals(expectedCount, cores.size)
            assertEquals(expectedCount, energy.size)
            assertEquals(4, asset.parts.count { it.name == "Underslung repulsor" })
            val instruction = ShapeProgram.steps(spec).single {
                it.operation == "attach_rear_drive"
            }
            assertEquals(expectedCount.toDouble(), instruction.parameters["housings"])
            if (expectedCount == 3) {
                assertTrue(asset.parts.any { it.name == "Central booster housing" })
                val driveLocations = houses.map { housing ->
                    housing.vertices.map { it.x }.average()
                }.sorted()
                assertTrue(driveLocations[0] < -.1)
                assertEquals(0.0, driveLocations[1], 0.001)
                assertTrue(driveLocations[2] > .1)
            }
        }
    }

    @Test
    fun buildsRealVerticesAndValidGlbEnvelope() {
        val examples = listOf(
            TrainingExample("wide hover suv panoramic canopy",
                5.4f, 2.5f, 1.8f, 2.3f, .55f, 1.12f),
            TrainingExample("low hover racer narrow silhouette",
                4.5f, 1.8f, 1.2f, 1.5f, .38f, 1.06f)
        )
        val spec = MiniAi.predict("wide hover suv panoramic canopy", "Mobile", examples)
        val mesh = MiniGeometry.generate(spec)
        assertTrue(mesh.triangleCount > 100)
        assertTrue(mesh.triangleCount < 20000)
        assertTrue(mesh.parts.any { it.name.contains("canopy") })
        // Closed components should have positive signed volume: outward winding.
        // Light-strip panels are intentionally open and are excluded.
        for (part in mesh.parts.filter { it.name != "Continuous front light" }) {
            var volumeSix = 0.0
            for (i in part.indices.indices step 3) {
                val a = part.vertices[part.indices[i]]
                val b = part.vertices[part.indices[i + 1]]
                val c = part.vertices[part.indices[i + 2]]
                volumeSix += (
                    a.x * (b.y * c.z - b.z * c.y) +
                    a.y * (b.z * c.x - b.x * c.z) +
                    a.z * (b.x * c.y - b.y * c.x)
                ).toDouble()
            }
            assertTrue("Inverted mesh winding in " + part.name, volumeSix > 0.0)
        }
        val bytes = GlbWriter.encode(mesh)
        val header = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(0x46546C67, header.getInt(0))
        assertEquals(2, header.getInt(4))
        assertEquals(bytes.size, header.getInt(8))
        val jsonLength = header.getInt(12)
        assertEquals(0x4E4F534A, header.getInt(16))
        val json = String(bytes, 20, jsonLength, Charsets.UTF_8)
        assertTrue(json.contains("\"asset\""))
        assertTrue(json.contains("\"version\":\"2.0\""))
        assertTrue(json.contains("\"POSITION\""))
        assertTrue(json.contains("\"NORMAL\""))
        val binMarkerOffset = 20 + jsonLength + 4
        assertEquals(0x004E4942, header.getInt(binMarkerOffset))
    }
}
