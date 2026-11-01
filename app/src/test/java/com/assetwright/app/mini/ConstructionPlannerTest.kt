package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class ConstructionPlannerTest {
    private val cases = listOf(
        ConstructionLabel("hover racer with two tucked repulsors", 2, "tucked"),
        ConstructionLabel("hover SUV with two hidden lift pods", 2, "tucked"),
        ConstructionLabel("hover racer with two exposed repulsors", 2, "exposed"),
        ConstructionLabel("hover SUV with two visible hover pads", 2, "exposed"),
        ConstructionLabel("hover coupe with four tucked lift pods", 4, "tucked"),
        ConstructionLabel("hover SUV with four hidden repulsors", 4, "tucked"),
        ConstructionLabel("hover racer with four exposed hover pads", 4, "exposed"),
        ConstructionLabel("hover SUV with four outboard lift pods", 4, "exposed"),
        ConstructionLabel("hover coupe with six tucked lift units", 6, "tucked"),
        ConstructionLabel("hover SUV with six concealed hover pads", 6, "tucked"),
        ConstructionLabel("hover racer with six external repulsors", 6, "exposed"),
        ConstructionLabel("hover SUV with six outrigger lift pods", 6, "exposed")
    )

    @Test
    fun supervisedClassifierAndExplicitOverridesKeepPartCountsValid() {
        val model = ConstructionPlanner.train(cases)
        assertEquals(12, model.examples)
        val explicit = listOf(
            "hover car with two exposed repulsors" to ConstructionPlan(2, "exposed"),
            "hover racer with four hidden lift pods" to ConstructionPlan(4, "tucked"),
            "hover SUV with six outboard hover pads" to ConstructionPlan(6, "exposed"),
            "hover coupe with repulsors x6 and integrated bodywork" to ConstructionPlan(6, "tucked")
        )
        for ((prompt, expected) in explicit) {
            assertEquals(prompt, expected, ConstructionPlanner.plan(prompt, model))
        }
        assertEquals(ConstructionPlan(4, "tucked"),
            ConstructionPlanner.plan("ordinary hover SUV", null))
    }

    @Test
    fun generatedMeshMatchesSemanticRoleCountsAndPhysicalMountingBounds() {
        val shape = VehicleSpec("Hover SUV",5.0f,2.4f,1.65f,2.2f,.52f,1.12f,
            "Mobile","hover SUV with three engines")
        for (count in listOf(2,4,6)) for (mount in listOf("tucked","exposed")) {
            val spec = shape.copy(constructionPlan=ConstructionPlan(count,mount))
            val asset = MiniGeometry.generate(spec)
            val units = asset.parts.filter { it.name=="Underslung repulsor" }
            val brackets = asset.parts.filter { it.name=="Repulsor mount bracket" }
            val fields = asset.parts.filter { it.name=="Repulsor field" }
            assertEquals(count,units.size)
            assertEquals(count,brackets.size)
            assertEquals(count,fields.size)
            assertEquals(3,asset.parts.count { it.name.endsWith("housing") })
            assertTrue(asset.triangleCount in 500..20000)
            val centerX = units.map { part ->
                part.vertices.map { it.x.toDouble() }.average()
            }.map { abs(it) }.average()
            if (mount=="exposed") assertTrue(centerX > .90)
            else assertTrue(centerX < .90)
            // Each support rail must reach near its corresponding pad's X
            // position, not be disconnected as an unrelated decoration.
            for (index in units.indices) {
                val padX = units[index].vertices.map { it.x.toDouble() }.average()
                val support = brackets[index].vertices.map { it.x.toDouble() }
                assertTrue(support.minOrNull()!! <= padX + 0.1)
                assertTrue(support.maxOrNull()!! >= padX - 0.1)
            }
            val steps = ShapeProgram.steps(spec)
            assertEquals(count.toDouble(), steps.single {
                it.operation=="attach_repulsors"
            }.parameters.getValue("repulsors"),0.0)
            assertEquals(count.toDouble(), steps.single {
                it.operation=="attach_repulsor_mounts"
            }.parameters.getValue("brackets"),0.0)
            assertEquals(listOf("mount_brackets"),steps.single {
                it.operation=="attach_repulsors"
            }.dependsOn)
        }
    }

    @Test
    fun missingTrainingExamplesNeverSilentlyCreateExoticComponents() {
        val model = ConstructionPlanner.plan("hover car with six hidden pads", null)
        assertEquals(6,model.liftCells)
        assertEquals("tucked",model.mount)
        assertEquals(ConstructionPlan(4,"tucked"),
            ConstructionPlanner.plan("hover sedan",null))
    }
}
