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

    @Test
    fun blindRearSocketIsConnectedHullGeometryForOneEngineOnly() {
        val single = spec().copy(sourcePrompt =
            "A hover racer with one central engine and a recessed rear socket")
        assertEquals(1, single.driveCount)
        val plain = MiniGeometry.generate(single)
        val variant = MiniGeometry.generate(single.copy(
            designControls = VehicleDesignControls(rearSocketDepth = 1f)
        ))
        val plainHull = plain.parts.single { it.name == "Sculpted continuous body" }
        val socketHull = variant.parts.single { it.name == "Sculpted continuous body" }
        assertEquals("Socket is part of the hull, not an extra mesh",
            plain.parts.size, variant.parts.size)
        assertTrue("Add native annular rim and blind well rings",
            socketHull.vertices.size >= plainHull.vertices.size + single.radialSegments * 2)
        // The previous hull had no centerline vertices in this stern region.
        val stern = single.length * .5f
        val buried = { mesh: MeshPart ->
            mesh.vertices.count {
                it.y < stern - .07f && it.y > stern - .32f &&
                it.x * it.x + (it.z - .8f) * (it.z - .8f) < .19f * .19f
            }
        }
        assertEquals(0, buried(plainHull))
        assertTrue("Need actual interior well surface, not a separate ornament",
            buried(socketHull) >= single.radialSegments)
        assertTrue(variant.triangleCount < 12000)
        val operations = ShapeProgram.steps(variant.spec).map { it.operation }
        assertTrue(operations.contains("recess_rear_socket"))
        assertTrue(ShapeProgram.steps(plain.spec).none {
            it.operation == "recess_rear_socket"
        })
        val multi = spec().copy(designControls =
            VehicleDesignControls(rearSocketDepth = 1f))
        // The same operation cannot silently cut through two engine housings.
        assertEquals(MiniGeometry.generate(spec()).parts,
            MiniGeometry.generate(multi).parts)
    }
}
