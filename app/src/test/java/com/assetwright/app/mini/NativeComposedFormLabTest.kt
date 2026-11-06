package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Tests explicit multi-operation source programs and REAL original GLBs. */
class NativeComposedFormLabTest {
    private fun program(vararg commands: NativeComposedFormLab.Command) =
        NativeComposedFormLab.Program(4.6f,2.2f,1.7f,commands.toList())
    private fun command(op:AdvancedFormOperation,strength:Float) =
        NativeComposedFormLab.Command(op,strength)

    @Test
    fun compoundNativeBodyUsesOneOriginalConnectedIndexedShell() {
        val program=program(
            command(AdvancedFormOperation.SECTION_LOFT,.32f),
            command(AdvancedFormOperation.LOWER_RECESS,.28f),
            command(AdvancedFormOperation.TANGENT_SWEEP,.25f))
        val part=NativeComposedFormLab.generate(program)
        val original=AdvancedFormLab.generate(AdvancedFormSpec(
            AdvancedFormOperation.SECTION_LOFT,4.6f,2.2f,1.7f,0f))
        assertEquals(original.indices,part.indices)
        assertEquals(original.vertices.size,part.vertices.size)
        assertEquals(602,part.vertices.size)
        assertNotEquals(original.vertices[112],part.vertices[112])
        val glb=GlbWriter.encode(NativeComposedFormLab.asGeneratedAsset(program))
        assertTrue(glb.size>2000)
        assertEquals('g'.code.toByte(),glb[0])
    }

    @Test
    fun compoundTrainingTargetIsExactAdditionOfOriginalNativeDeltas() {
        val first=command(AdvancedFormOperation.SECTION_LOFT,.24f)
        val second=command(AdvancedFormOperation.LOWER_RECESS,.29f)
        val source=program(first,second)
        val mixed=NativeComposedFormLab.generate(source)
        val base=AdvancedFormLab.generate(AdvancedFormSpec(
            AdvancedFormOperation.SECTION_LOFT,4.6f,2.2f,1.7f,0f))
        val a=AdvancedFormLab.generate(AdvancedFormSpec(
            first.operation,4.6f,2.2f,1.7f,first.strength))
        val b=AdvancedFormLab.generate(AdvancedFormSpec(
            second.operation,4.6f,2.2f,1.7f,second.strength))
        for (index in listOf(0,37,160,295,450,600)) {
            val target=mixed.vertices[index]
            val p=base.vertices[index]
            val u=a.vertices[index]
            val v=b.vertices[index]
            assertEquals(u.x+v.x-p.x,target.x,1e-5f)
            assertEquals(u.y+v.y-p.y,target.y,1e-5f)
            assertEquals(u.z+v.z-p.z,target.z,1e-5f)
        }
    }

    @Test
    fun fourOperationProgramIsNativeAndManifoldIndexedGeometry() {
        val result=NativeComposedFormLab.generate(program(
            command(AdvancedFormOperation.SUPERELLIPSE_PROFILE,.20f),
            command(AdvancedFormOperation.SECTION_LOFT,.21f),
            command(AdvancedFormOperation.RIBBED_FAIRING,.18f),
            command(AdvancedFormOperation.TANGENT_SWEEP,.22f)))
        assertEquals(602,result.vertices.size)
        assertTrue(result.indices.size/3 in 900..3000)
        assertTrue(result.vertices.all {
            it.x.isFinite() && it.y.isFinite() && it.z.isFinite()
        })
    }

    @Test(expected=IllegalArgumentException::class)
    fun mustUseCanonicalDependencyOrderForOriginalConstructionProgram() {
        NativeComposedFormLab.generate(program(
            command(AdvancedFormOperation.TANGENT_SWEEP,.22f),
            command(AdvancedFormOperation.SECTION_LOFT,.24f)))
    }

    @Test(expected=IllegalArgumentException::class)
    fun cannotReuseTheSameNativeOperationInOneProgram() {
        NativeComposedFormLab.generate(program(
            command(AdvancedFormOperation.SECTION_LOFT,.22f),
            command(AdvancedFormOperation.SECTION_LOFT,.24f)))
    }

    @Test(expected=IllegalArgumentException::class)
    fun cannotIntroduceUnboundedCompoundDeformations() {
        NativeComposedFormLab.generate(program(
            command(AdvancedFormOperation.SUPERELLIPSE_PROFILE,.75f),
            command(AdvancedFormOperation.SECTION_LOFT,.33f)))
    }

    @Test(expected=IllegalArgumentException::class)
    fun cannotClaimSingleOperatorIsMultiOperationLearning() {
        NativeComposedFormLab.generate(program(
            command(AdvancedFormOperation.SECTION_LOFT,.33f)))
    }
}
