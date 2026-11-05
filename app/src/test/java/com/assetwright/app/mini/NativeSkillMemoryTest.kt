package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertNotEquals
import org.junit.Test

/** The first directly usable, persistent user-approved advanced geometry skill. */
class NativeSkillMemoryTest {
    @Test
    fun approvedExactGeometrySkillBeatsFixedVocabulary() {
        val lessons = listOf(
            NativeSkillMemory.Lesson("deep sculpted racer hull",
                AdvancedFormOperation.LOWER_RECESS, .83f))
        val predicted = NativeSkillMemory.propose("DEEP SCULPTED RACER HULL", lessons)
        assertEquals(AdvancedFormOperation.LOWER_RECESS, predicted.operation)
        assertEquals(.83f, predicted.strength, .00001f)
        assertEquals("approved exact lesson", predicted.origin)
    }

    @Test
    fun similarReviewedPromptsCarryNativeStrengthAcrossRequests() {
        val trained = listOf(
            NativeSkillMemory.Lesson("wide sculpted racer shell",
                AdvancedFormOperation.SUPERELLIPSE_PROFILE, .72f))
        val prediction = NativeSkillMemory.propose("wide sculpted racer body shell", trained)
        assertEquals("approved similar lesson", prediction.origin)
        assertEquals(AdvancedFormOperation.SUPERELLIPSE_PROFILE, prediction.operation)
        assertEquals(.72f, prediction.strength, .00001f)
    }

    @Test
    fun vocabularyUsesRealNativeOperationsWithoutInventedDinoWeights() {
        assertEquals(AdvancedFormOperation.SECTION_TWIST,
            NativeSkillMemory.propose("twisted beam", emptyList()).operation)
        assertEquals(AdvancedFormOperation.LOWER_RECESS,
            NativeSkillMemory.propose("deep undercut channel", emptyList()).operation)
        assertEquals(.24f,
            NativeSkillMemory.propose("subtle twisted beam", emptyList()).strength, .00001f)
        assertEquals(.82f,
            NativeSkillMemory.propose("dramatic twisted beam", emptyList()).strength, .00001f)
    }

    @Test
    fun actualKotlinNativeGeometryChangesWithLearnedOperatorAndPower() {
        val a=NativeSkillMemory.generate("curved beam",
            AdvancedFormOperation.TANGENT_SWEEP, .15f)
        val b=NativeSkillMemory.generate("curved beam",
            AdvancedFormOperation.TANGENT_SWEEP, .85f)
        assertTrue(a.triangleCount in 900..3000)
        assertEquals(a.triangleCount,b.triangleCount)
        assertNotEquals(a.parts[0].vertices[37],b.parts[0].vertices[37])
        assertTrue(GlbWriter.encode(b).size > 2000)
    }

    @Test(expected=IllegalArgumentException::class)
    fun nativeGeometryDoesNotAcceptOutOfRangeUnreviewedStrength() {
        NativeSkillMemory.generate("curved beam",
            AdvancedFormOperation.TANGENT_SWEEP, 1.1f)
    }
}
