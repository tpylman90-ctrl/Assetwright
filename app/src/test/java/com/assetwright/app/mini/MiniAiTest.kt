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
