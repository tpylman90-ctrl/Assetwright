package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertNotNull
import org.junit.Test

class AdaptiveShapeModelTest {
    private fun ex(prompt: String, width: Float): TrainingExample =
        TrainingExample(prompt, 5.15f, width, 1.55f, 1.88f, .51f, 1.13f)

    @Test
    fun approvedExampleTrainsCompactWeightsWithoutGlb() {
        val seed = listOf(
            ex("hover racer narrow low cockpit", 1.7f),
            ex("hover suv wide panoramic roof", 2.0f),
            ex("hover coupe low long nose", 1.88f)
        )
        val approved = listOf(
            ex("hover suv wide panoramic roof", 2.8f),
            ex("hover racer narrow low cockpit", 1.8f),
            ex("hover coupe low long nose", 2.0f)
        )
        val snapshot = AdaptiveShapeModel.fit(approved, seed)
        assertNotNull(snapshot)
        assertEquals(240, snapshot!!.weights.size)
        assertEquals(3, snapshot.trainedCount)
        val query = "hover suv wide panoramic roof"
        val base = MiniAi.predict(query, "Mobile", seed)
        val corrected = AdaptiveShapeModel.predict(base, snapshot)
        assertTrue(corrected.width > base.width)
        assertTrue(corrected.width in 1.45f..3.2f)
    }

    @Test
    fun lowEvidenceDoesNotProduceUnboundedGeometry() {
        val seed = listOf(ex("hover racer", 1.8f))
        val accepted = listOf(ex("wide hover racer", 3.2f))
        val snapshot = AdaptiveShapeModel.fit(accepted, seed)
        val base = MiniAi.predict("a wide hover racer", "Mobile", seed)
        val prediction = AdaptiveShapeModel.predict(base, snapshot)
        assertTrue(prediction.width in 1.45f..3.2f)
        assertTrue(prediction.length in 3.4f..7f)
    }
}
