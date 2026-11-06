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


    @Test
    fun promptFormVocabularyDoesNotCollapseAllRequestsToGenericShell() {
        val prompts = listOf(
            "a fast spindle", "a tapered wedge", "a rectangular box module",
            "a bulging barrel", "a stone arch", "a sharp blade",
            "a smooth canopy pod", "a metal truss beam")
        val forms = prompts.map { NativeSkillMemory.proposeForm(it) }
        assertEquals(8, forms.distinct().size)
        val meshes = forms.map {
            NativeSkillMemory.generateDiverse(
                "original different forms",AdvancedFormOperation.SECTION_LOFT,
                .4f,it)
        }
        assertEquals(8,meshes.size)
        assertEquals(8,meshes.map { it.parts[0].name }.distinct().size)
    }

    @Test
    fun reviewedArchetypeIsRecalledInsteadOfGenericShape() {
        val lesson=NativeSkillMemory.Lesson(
            "advanced sculpted modular vehicle",
            AdvancedFormOperation.LOWER_RECESS,.63f,
            NativeFormArchetype.BOX_MODULE)
        val answer=NativeSkillMemory.propose(
            "advanced sculpted modular vehicle",listOf(lesson))
        assertEquals(NativeFormArchetype.BOX_MODULE,answer.archetype)
        assertEquals(.63f,answer.strength,.001f)
    }

    @Test(expected=IllegalArgumentException::class)
    fun nativeGeometryDoesNotAcceptOutOfRangeUnreviewedStrength() {
        NativeSkillMemory.generate("curved beam",
            AdvancedFormOperation.TANGENT_SWEEP, 1.1f)
    }
}
