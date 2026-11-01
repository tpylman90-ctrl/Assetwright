package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

data class Vec3(val x: Float, val y: Float, val z: Float) {
    operator fun minus(other: Vec3) = Vec3(x - other.x, y - other.y, z - other.z)
    operator fun plus(other: Vec3) = Vec3(x + other.x, y + other.y, z + other.z)
    fun cross(other: Vec3) = Vec3(
        y * other.z - z * other.y,
        z * other.x - x * other.z,
        x * other.y - y * other.x
    )
}

data class MeshPart(
    val name: String,
    val color: Int,
    val vertices: List<Vec3>,
    val indices: List<Int>
)

data class GeneratedAsset(val spec: VehicleSpec, val parts: List<MeshPart>) {
    val triangleCount get() = parts.sumOf { it.indices.size / 3 }
}

private const val BODY = 0x39BEB1
private const val GLASS = 0x1A526A
private const val UNDERBODY = 0x233446
private const val ENGINE = 0x687F94
private const val LIGHT = 0xFFB96B

private class MeshBuilder {
    private val result = mutableListOf<MeshPart>()

    fun loft(name: String, color: Int, rings: List<List<Vec3>>, cap: Boolean = true) {
        require(rings.size >= 2)
        val n = rings.first().size
        require(n >= 3 && rings.all { it.size == n })
        val verts = rings.flatten()
        val triangles = ArrayList<Int>()
        for (j in 0 until rings.size - 1) {
            for (i in 0 until n) {
                val k = (i + 1) % n
                val a = j * n + i
                val b = j * n + k
                val c = (j + 1) * n + i
                val d = (j + 1) * n + k
                triangles.addAll(listOf(a, b, c, b, d, c))
            }
        }
        if (cap) {
            val end = (rings.size - 1) * n
            for (i in 1 until n - 1) {
                triangles.addAll(listOf(0, i + 1, i))
                triangles.addAll(listOf(end, end + i, end + i + 1))
            }
            // Ensure the closed shape has outward-facing surfaces. Rings oriented
            // along -Y or +Z have different initial winding; signed volume catches
            // both and corrects the triangulation before normals are calculated.
            var volumeSix = 0.0
            for (index in triangles.indices step 3) {
                val a = verts[triangles[index]]
                val b = verts[triangles[index + 1]]
                val c = verts[triangles[index + 2]]
                volumeSix += (
                    a.x * (b.y * c.z - b.z * c.y) +
                    a.y * (b.z * c.x - b.x * c.z) +
                    a.z * (b.x * c.y - b.y * c.x)
                ).toDouble()
            }
            if (volumeSix < 0.0) {
                for (index in triangles.indices step 3) {
                    val tmp = triangles[index + 1]
                    triangles[index + 1] = triangles[index + 2]
                    triangles[index + 2] = tmp
                }
            }
        }
        result += MeshPart(name, color, verts, triangles)
    }

    fun panel(name: String, color: Int, a: Vec3, b: Vec3, c: Vec3, d: Vec3) {
        result += MeshPart(name, color, listOf(a, b, c, d), listOf(0, 1, 2, 0, 2, 3))
    }

    fun cylinderY(name: String, color: Int, x: Float, y0: Float, y1: Float,
                  z: Float, radius: Float, segments: Int) {
        loft(name, color, listOf(y0, y1).map { y ->
            (0 until segments).map { i ->
                val angle = i * 2.0 * PI / segments
                Vec3(x + radius * cos(angle).toFloat(), y, z + radius * sin(angle).toFloat())
            }
        })
    }

    fun discZ(name: String, color: Int, x: Float, y: Float,
              z0: Float, z1: Float, radius: Float, segments: Int) {
        loft(name, color, listOf(z0, z1).map { z ->
            (0 until segments).map { i ->
                val angle = i * 2.0 * PI / segments
                Vec3(x + radius * cos(angle).toFloat(),
                    y + radius * sin(angle).toFloat(), z)
            }
        })
    }

    fun finish() = result.toList()
}

/**
 * Native, offline, deterministic 3D vehicle construction. The AI predicts the
 * shape parameters; this mesher produces actual vertices and triangles.
 * Axes: nose -Y, rear +Y, up +Z (same as existing Assetwright vehicle generators).
 */
object MiniGeometry {
    fun generate(spec: VehicleSpec): GeneratedAsset {
        val m = MeshBuilder()
        val l = spec.length
        val w = spec.width * 0.5f
        val stations = listOf(
            -0.50f to 0.46f, -0.43f to 0.70f, -0.29f to 0.94f,
            -0.05f to 0.98f, 0.19f to spec.rearHaunch,
            0.39f to spec.rearHaunch * 1.02f, 0.50f to 0.82f
        )
        val bodyRings = stations.map { (t, profile) ->
            (0 until spec.radialSegments).map { i ->
                val angle = i * 2.0 * PI / spec.radialSegments
                val side = cos(angle).toFloat()
                val top = sin(angle).toFloat()
                val frontShape = if (t < -0.29f) spec.noseTaper else 1f
                val width = w * profile * frontShape
                Vec3(
                    width * side,
                    l * t,
                    0.81f + (0.39f + 0.04f * profile) * top
                )
            }
        }
        m.loft("Sculpted continuous body", BODY, bodyRings)

        // A low central keel remains inside the body silhouette.
        m.loft("Underside keel", UNDERBODY, listOf(-0.35f, 0.35f).map { t ->
            listOf(
                Vec3(-w * .65f, l * t, .48f), Vec3(w * .65f, l * t, .48f),
                Vec3(w * .57f, l * t, .69f), Vec3(-w * .57f, l * t, .69f)
            )
        })

        // The greenhouse lower edge intersects the upper hull: no floating cockpit.
        val roof = spec.roofHeight
        val span = spec.canopyLength.coerceAtMost(l * .56f)
        val center = -l * .045f
        val cabinStations = listOf(-.5f to .53f, -.38f to .85f,
            -.13f to 1f, .19f to .98f, .43f to .79f, .5f to .47f)
        val cabinRings = cabinStations.map { (t, taper) ->
            (0 until spec.radialSegments).map { i ->
                val angle = i * 2.0 * PI / spec.radialSegments
                val side = cos(angle).toFloat()
                val top = sin(angle).toFloat()
                Vec3(w * .80f * taper * side,
                    center + span * t,
                    1.14f + (roof - 1.14f) * .5f * (1f + top) * taper)
            }
        }
        m.loft("Bonded panoramic canopy", GLASS, cabinRings)

        val front = -l * 0.486f
        m.panel("Continuous front light", LIGHT,
            Vec3(-w * .48f, front, .90f), Vec3(w * .48f, front, .90f),
            Vec3(w * .48f, front, .95f), Vec3(-w * .48f, front, .95f))

        // Engine count is a construction decision, not a body-dimension tweak.
        // Three-engine layouts add a central booster between the two fitted
        // outer drives; one-engine layouts use only the central position.
        val drivePositions = when (spec.driveCount) {
            1 -> listOf(0f)
            3 -> listOf(-w * .57f, 0f, w * .57f)
            else -> listOf(-w * .57f, w * .57f)
        }
        val aft = l * .475f
        for ((index, x) in drivePositions.withIndex()) {
            val centralBooster = spec.driveCount == 3 && index == 1
            val r = if (centralBooster) .28f else .24f
            val extension = if (centralBooster) .39f else .30f
            val name = if (centralBooster) "Central booster" else "Rear drive"
            m.cylinderY("$name housing", ENGINE, x, aft - .10f,
                aft + extension, .81f, r, 20)
            m.cylinderY("$name core", UNDERBODY, x, aft + extension,
                aft + extension + .015f, .81f, r * .75f, 20)
            m.cylinderY("$name energy ring", LIGHT, x, aft + extension + .015f,
                aft + extension + .032f, .81f, r * .5f, 20)
        }

        // Lift repulsors are independent of propulsion count.
        for (side in listOf(-1f, 1f)) {
            for (position in listOf(-.28f, .31f)) {
                m.discZ("Underslung repulsor", ENGINE, side * w * .70f,
                    l * position, .29f, .39f, .19f, 16)
                m.discZ("Repulsor field", LIGHT, side * w * .70f,
                    l * position, .275f, .29f, .135f, 16)
            }
        }

        return GeneratedAsset(spec, m.finish())
    }
}
