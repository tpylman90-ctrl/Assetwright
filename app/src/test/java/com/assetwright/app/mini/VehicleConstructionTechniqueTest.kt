package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/** Original, local construction-operation experiments; no outside asset meshes. */
class VehicleConstructionTechniqueTest {
    private fun spec() = VehicleSpec(
        "Test racer", 4.85f, 2.4f, 1.34f, 1.75f,
        .47f, 1.14f, "Mobile",
        "Hover racer with four exposed repulsors and twin engines",
        ConstructionPlan(4, "exposed")
    )

    @Test
    fun cockpitTransitionSculptsContinuousOriginalHullInsteadOfAddingOverlay() {
        val original = MiniGeometry.generate(spec())
        val bridged = MiniGeometry.generate(spec().copy(
            designControls = VehicleDesignControls(cockpitShoulderTransition = 1f)
        ))
        val baseHull = original.parts.single { it.name == "Sculpted continuous body" }
        val sculptedHull = bridged.parts.single { it.name == "Sculpted continuous body" }
        val upperWidth = { mesh: MeshPart ->
            mesh.vertices.filter {
                abs(it.y) < .9f && it.z >= .85f && it.z <= 1.03f
            }.maxOf { abs(it.x) }
        }
        assertTrue("Sculpt must widen true hull shoulder, not add a panel",
            upperWidth(sculptedHull) > upperWidth(baseHull) + .025f)
        assertTrue("Hull loft should have more local profile stations",
            sculptedHull.vertices.size > baseHull.vertices.size)
        assertEquals("Cockpit sculpt shouldn't introduce loose body overlay meshes",
            original.parts.size, bridged.parts.size)
        assertTrue(bridged.triangleCount < 12000)
    }

    @Test
    fun rearShroudingMakesSixStationDriveHousingsWithoutLosingEngineCount() {
        val baseline = MiniGeometry.generate(spec())
        val modified = MiniGeometry.generate(spec().copy(
            designControls = VehicleDesignControls(rearNacelleShrouding = 1f)
        ))
        val housings = { asset: GeneratedAsset ->
            asset.parts.filter { it.name == "Rear drive housing" ||
                                  it.name == "Central booster housing" }
        }
        val base = housings(baseline)
        val new = housings(modified)
        assertEquals(2, base.size)
        assertEquals(2, new.size)
        assertTrue("Engine shroud must have more axial stations",
            new.all { it.vertices.size > base.first().vertices.size })
        val rearEnergyRings = modified.parts.count { it.name.endsWith("energy ring") }
        assertEquals(2, rearEnergyRings)
        assertTrue(modified.triangleCount < 12000)
    }

    @Test
    fun publicPhoneDefaultsStillProduceOriginalShape() {
        val s=spec()
        val explicitZero=s.copy(designControls=VehicleDesignControls(
            canopySquareness=0f, shoulderDefinition=0f,
            fairedRepulsorMounts=0f, cockpitShoulderTransition=0f,
            rearNacelleShrouding=0f
        ))
        val a=MiniGeometry.generate(s)
        val b=MiniGeometry.generate(explicitZero)
        assertEquals(a.triangleCount,b.triangleCount)
        assertEquals(a.parts,b.parts)
    }
}
