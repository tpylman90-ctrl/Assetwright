package com.assetwright.app.geometry

import org.junit.Assert.*
import org.junit.Test

class ComponentHealthTest {
    @Test fun twoNamedPartsHaveIndependentMetrics() {
        val verts = floatArrayOf(
            0f,0f,0f, 1f,0f,0f, 1f,1f,0f, 0f,1f,0f,
            5f,0f,0f, 6f,0f,0f, 6f,1f,0f, 5f,1f,0f
        )
        val faces = intArrayOf(0,1,2,0,2,3,4,5,6,4,6,7)
        val parts = listOf(
            GeometryPart(0,"RobotAssembly / Arm","node/arm",0,2,0,4),
            GeometryPart(1,"RobotAssembly / Gripper","node/gripper",2,2,4,4)
        )
        val model=GeometryMesh("fixture.glb",verts,faces,null,parts)
        val reports=model.partHealth()
        assertEquals(2,reports.size)
        assertEquals(2,reports[0].triangles)
        assertEquals(2,reports[1].triangles)
        assertEquals(4,reports[0].boundaryEdges)
        assertEquals(4,reports[1].boundaryEdges)
        assertEquals(0,reports[0].degenerateTriangles)
        assertTrue(reports[1].surfaceArea>0.9)
        assertTrue(reports[0].source.sourceName.contains("Arm"))
        assertTrue(reports[1].source.sourceName.contains("Gripper"))
    }

    @Test fun degenerateFaceIsReportedOnlyOnItsOwnPart() {
        val v=floatArrayOf(0f,0f,0f,1f,0f,0f,0f,1f,0f,5f,0f,0f,6f,0f,0f,7f,0f,0f)
        val f=intArrayOf(0,1,2,3,4,5)
        val parts=listOf(
            GeometryPart(0,"Enclosure","enclosure",0,1,0,3),
            GeometryPart(1,"Battery Cassette","cassette",1,1,3,3)
        )
        val reports=GeometryMesh("test.glb",v,f,null,parts).partHealth()
        assertEquals(0,reports[0].degenerateTriangles)
        assertEquals(1,reports[1].degenerateTriangles)
        assertTrue(reports[1].flags.any{it.contains("degenerate")})
    }
}
