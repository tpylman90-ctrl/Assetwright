package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/** Prevent a one-size-fits-all object generator from passing source school. */
class NativeDiverseFormLabTest {
    private fun original(form:NativeFormArchetype,
                         op:AdvancedFormOperation=AdvancedFormOperation.SECTION_LOFT,
                         strength:Float=0f,
                         segments:Int=24,stations:Int=24): MeshPart =
        NativeDiverseFormLab.generate(NativeDiverseFormSpec(
            form,op,4.8f,2.15f,1.55f,strength,segments,stations))

    @Test fun eightArchetypesHaveMeasurablyDifferentRealOriginalMeshSurfaces() {
        val meshes=NativeFormArchetype.values().map { original(it) }
        assertEquals(8,meshes.size)
        val center=meshes.map { form ->
            (listOf(24*4,24*8,24*12,24*16,24*20)).flatMap { i ->
                listOf(form.vertices[i].x,form.vertices[i].z,
                       form.vertices[i+5].x,form.vertices[i+5].z)
            }
        }
        for(i in center.indices) for(j in i+1 until center.size) {
            val difference=center[i].zip(center[j]).sumOf {
                abs((it.first-it.second).toDouble())
            }
            assertTrue("Every original archetype must create a different shape",difference>.05)
        }
        for(mesh in meshes) {
            assertEquals(602,mesh.vertices.size)
            assertEquals(1200,mesh.indices.size/3)
            assertTrue(mesh.vertices.all {
                it.x.isFinite()&&it.y.isFinite()&&it.z.isFinite()
            })
        }
    }

    @Test fun topologyChangesAreRealNotDifferentNamesForSameGeometry() {
        val a=original(NativeFormArchetype.SPINDLE,segments=24,stations=24)
        val b=original(NativeFormArchetype.BOX_MODULE,segments=32,stations=24)
        val c=original(NativeFormArchetype.TRUSS_BEAM,segments=40,stations=32)
        assertNotEquals(a.vertices.size,b.vertices.size)
        assertNotEquals(b.vertices.size,c.vertices.size)
        assertEquals(602,a.vertices.size)
        assertEquals(802,b.vertices.size)
        assertEquals(1322,c.vertices.size)
        for(mesh in listOf(a,b,c)) {
            val asset=GeneratedAsset(
                VehicleSpec("Diverse school",4.8f,2.15f,1.55f,
                    1.7f,.55f,1.07f,"Mobile","Source original native geometry"),
                listOf(mesh))
            val encoded=GlbWriter.encode(asset)
            assertTrue(encoded.size>2000)
        }
    }

    @Test fun nativeTwistAffectsRealVerticesWithinEveryDifferentForm() {
        for(form in NativeFormArchetype.values()) {
            val before=original(form)
            val after=original(form,AdvancedFormOperation.SECTION_TWIST,.65f)
            assertEquals(before.indices,after.indices)
            val displacement=before.vertices.zip(after.vertices).sumOf {
                abs((it.first.x-it.second.x).toDouble())+
                    abs((it.first.z-it.second.z).toDouble())
            }
            assertTrue("Twist must actually alter each archetype",displacement>2)
        }
    }

    @Test(expected=IllegalArgumentException::class)
    fun nativeFormRejectsUnsupportedTessellation() {
        original(NativeFormArchetype.BLADE,segments=25,stations=24)
    }
}
