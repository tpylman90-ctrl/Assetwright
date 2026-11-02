package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.abs
import kotlin.math.pow

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

    fun cylinderX(name: String, color: Int, x0: Float, x1: Float,
                  y: Float, z: Float, radius: Float, segments: Int) {
        loft(name, color, listOf(x0, x1).map { x ->
            (0 until segments).map { i ->
                val angle = i * 2.0 * PI / segments
                Vec3(x, y + radius * cos(angle).toFloat(),
                    z + radius * sin(angle).toFloat())
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
        // A roofHeight is the finished vehicle's roof line, not just a
        // nominal upper limit. Preserve at least .26 m of visible greenhouse
        // over the shell, including at the minimum supported roof height.
        val hullCenterZ = minOf(.80f, spec.roofHeight - .46f)
        val hullUpperRadius = minOf(.27f, spec.roofHeight - hullCenterZ - .26f)
        val hullLowerRadius = .38f
        val shoulderSculpt = spec.designControls.shoulderDefinition.coerceIn(0f, 1f)
        val roofSquareness = spec.designControls.canopySquareness.coerceIn(0f, 1f)
        val mountFairing = spec.designControls.fairedRepulsorMounts.coerceIn(0f, 1f)
        // Denser, continuous nose-to-shoulder transition. Previously the nose
        // factor jumped from 0.55 to 1.0 between adjacent stations, causing
        // an abrupt flare on every exported vehicle.
        val stations = listOf(
            -0.50f to 0.38f, -0.46f to 0.52f, -0.39f to 0.71f,
            -0.30f to 0.88f, -0.21f to 0.97f, -0.05f to 1.00f,
            0.12f to 1.03f, 0.27f to spec.rearHaunch,
            0.40f to spec.rearHaunch * 1.01f, 0.50f to 0.82f
        )
        val bodyRings = stations.map { (t, profile) ->
            (0 until spec.radialSegments).map { i ->
                val angle = i * 2.0 * PI / spec.radialSegments
                val side = cos(angle).toFloat()
                val top = sin(angle).toFloat()
                val frontProgress = ((t + 0.50f) / 0.45f).coerceIn(0f, 1f)
                val eased = frontProgress * frontProgress * (3f - 2f * frontProgress)
                val frontShape = spec.noseTaper + (1f - spec.noseTaper) * eased
                val shoulderVolume = shoulderSculpt * .065f * abs(side) * eased
                val width = w * profile * frontShape * (1f + shoulderVolume)
                Vec3(
                    width * side,
                    l * t,
                    hullCenterZ + if (top >= 0f)
                        hullUpperRadius * top * (.94f + .06f * profile) +
                            shoulderSculpt * .055f * abs(side) * top
                    else hullLowerRadius * top
                )
            }
        }
        m.loft("Sculpted continuous body", BODY, bodyRings)

        // A low central keel remains inside the body silhouette.
        m.loft("Underside keel", UNDERBODY, listOf(-0.35f, 0.35f).map { t ->
            listOf(
                Vec3(-w * .65f, l * t, hullCenterZ - .32f),
                Vec3(w * .65f, l * t, hullCenterZ - .32f),
                Vec3(w * .57f, l * t, hullCenterZ - .11f),
                Vec3(-w * .57f, l * t, hullCenterZ - .11f)
            )
        })

        // The greenhouse lower edge intersects the upper hull: no floating cockpit.
        val roof = spec.roofHeight
        val span = spec.canopyLength.coerceAtMost(l * .56f)
        val center = -l * .045f
        // The old glass ellipse sat above the shoulder at its widest point.
        // Its lower perimeter now intersects the hull, while its roof is
        // gradually raised through a fitted eight-station greenhouse profile.
        val cabinStations = listOf(
            -.50f to .38f, -.42f to .57f, -.30f to .79f,
            -.12f to .94f, .08f to 1f, .27f to .91f,
            .42f to .72f, .50f to .35f
        )
        val cabinRings = cabinStations.map { (t, taper) ->
            (0 until spec.radialSegments).map { i ->
                val angle = i * 2.0 * PI / spec.radialSegments
                val side = cos(angle).toFloat()
                val top = sin(angle).toFloat()
                val lowerFoot = hullCenterZ + .10f
                // The baseline uses a near-elliptical greenhouse. The
                // experimental exponent flattens its upper crown into a
                // wider aerodynamic roof without changing the specified peak.
                val crown = maxOf(top, 0f).toDouble().pow(
                    (1f - .69f * roofSquareness).toDouble()
                ).toFloat()
                val z = lowerFoot + .08f * minOf(top, 0f) +
                    (roof - lowerFoot).coerceAtLeast(0f) * crown * taper
                Vec3(w * .78f * taper * side, center + span * t, z)
            }
        }
        m.loft("Bonded panoramic canopy", GLASS, cabinRings)

        // Light on the front cap, with endpoints INSIDE the actual nose
        // width. The previous +/-0.48*w strip protruded beyond the narrow nose.
        val noseHalfWidth = w * .38f * spec.noseTaper
        val front = -l * .500f - .012f
        m.panel("Continuous front light", LIGHT,
            Vec3(-noseHalfWidth * .68f, front, hullCenterZ + .09f),
            Vec3(noseHalfWidth * .68f, front, hullCenterZ + .09f),
            Vec3(noseHalfWidth * .68f, front, hullCenterZ + .16f),
            Vec3(-noseHalfWidth * .68f, front, hullCenterZ + .16f))

        // Engine count is a construction decision, not a body-dimension tweak.
        // Three-engine layouts add a central booster between the two fitted
        // outer drives; one-engine layouts use only the central position.
        val tripleOffset = maxOf(w * .72f, .54f) // prevent overlap on narrow hulls
        val drivePositions = when (spec.driveCount) {
            1 -> listOf(0f)
            3 -> listOf(-tripleOffset, 0f, tripleOffset)
            else -> listOf(-w * .57f, w * .57f)
        }
        val aft = l * .475f
        val driveZ = hullCenterZ + .01f
        for ((index, x) in drivePositions.withIndex()) {
            val centralBooster = spec.driveCount == 3 && index == 1
            val r = if (centralBooster) .28f else .24f
            val extension = if (centralBooster) .39f else .30f
            val name = if (centralBooster) "Central booster" else "Rear drive"
            m.cylinderY("$name housing", ENGINE, x, aft - .10f,
                aft + extension, driveZ, r, 20)
            m.cylinderY("$name core", UNDERBODY, x, aft + extension,
                aft + extension + .015f, driveZ, r * .75f, 20)
            m.cylinderY("$name energy ring", LIGHT, x, aft + extension + .015f,
                aft + extension + .032f, driveZ, r * .5f, 20)
        }

        // Learned semantic construction plan controls lift-unit quantity and
        // mount exposure without changing engine count or primary body shape.
        val foreAft = when (spec.liftCount) {
            2 -> listOf(0.0f)
            6 -> listOf(-.32f, 0f, .32f)
            else -> listOf(-.28f, .31f)
        }
        // An exposed repulsor must extend beyond even the widest rear
        // haunch; 0.98*w left the entire pad under the broad shell.
        val mountOffset = if (spec.liftMount == "exposed") 1.45f else .64f
        for (side in listOf(-1f, 1f)) {
            val padX = side * w * mountOffset
            for (position in foreAft) {
                val padY = l * position
                m.discZ("Underslung repulsor", ENGINE, padX,
                    padY, .29f, .39f, .19f, 16)
                m.discZ("Repulsor field", LIGHT, padX,
                    padY, .275f, .29f, .135f, 16)
                // Real mesh bracket spans pad and underbody instead of a
                // floating, visually separate hover unit.
                if (mountFairing > 0f) {
                    // Five profiled sections: thick root, swept transition,
                    // and tight lift-cell collar. Unlike the previous two-ring
                    // cylinder, the cross section tapers toward the pad and
                    // rises smoothly to blend into the underside.
                    val x0 = side * w * .38f
                    val steps = listOf(0f, .20f, .46f, .76f, 1f)
                    m.loft("Repulsor mount bracket", UNDERBODY, steps.map { t ->
                        val rootWeight = (1f - t) * (1f - t)
                        val broadness = .12f + mountFairing * .14f * rootWeight
                        val height = .092f + mountFairing * .075f * rootWeight
                        val z = .40f + mountFairing * .035f *
                            sin((PI * t).toFloat())
                        (0 until 12).map { i ->
                            val theta = i * 2.0 * PI / 12
                            Vec3(
                                x0 + (padX - x0) * t,
                                padY + broadness * cos(theta).toFloat(),
                                z + height * sin(theta).toFloat()
                            )
                        }
                    })
                } else {
                    m.cylinderX("Repulsor mount bracket", UNDERBODY,
                        side * w * .38f, padX,
                        padY, .41f, if (spec.liftMount == "exposed") .13f else .085f, 12)
                }
            }
        }

        return GeneratedAsset(spec, m.finish())
    }
}
