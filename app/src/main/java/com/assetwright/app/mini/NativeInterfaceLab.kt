package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.sin

/**
 * Research-only first real connected-interface primitive.
 *
 * One closed genus-one shell: exterior continuous flange, interior THROUGH
 * bore and two annular end faces share real indexed topology. No fake inset,
 * disconnected imported parts, Boolean, 3D fillet or claimed Class-A/G2 CAD.
 * The analytic flange envelope has zero first and second derivatives where
 * it returns to the base tube; its polygonal sampling is only an approximation.
 */
data class NativeInterfaceSpec(
    val length: Float,
    val width: Float,
    val height: Float,
    val boreStrength: Float,
    val flangeStrength: Float,
    val blendStrength: Float,
    val segments: Int = 32,
    val stations: Int = 40
)

object NativeInterfaceLab {
    private fun envelope(u: Float, center: Float, halfWidth: Float): Float {
        val t = abs(u - center) / halfWidth
        if (t >= 1f) return 0f
        val v = 1f - t * t
        return v * v * v
    }

    fun generate(spec: NativeInterfaceSpec): MeshPart {
        require(spec.length.isFinite() && spec.length in 1.5f..12f)
        require(spec.width.isFinite() && spec.width in .65f..7f)
        require(spec.height.isFinite() && spec.height in .55f..7f)
        require(spec.boreStrength.isFinite() && spec.boreStrength in 0f..1f)
        require(spec.flangeStrength.isFinite() && spec.flangeStrength in 0f..1f)
        require(spec.blendStrength.isFinite() && spec.blendStrength in 0f..1f)
        require(spec.segments == 32 && spec.stations == 40) {
            "V1 topology is frozen to 32 radial and 40 axial sections"
        }

        val n = spec.segments
        val m = spec.stations
        val rings = m + 1
        val innerOffset = rings * n
        val vertices = ArrayList<Vec3>(2 * innerOffset)
        val triangles = ArrayList<Int>((m * n * 4 + 4 * n) * 3)
        val baseX = spec.width * .5f
        val baseZ = spec.height * .5f
        val holeRatio = .14f + .34f * spec.boreStrength
        val flangeAmplitude = .08f + .35f * spec.flangeStrength
        val blendWidth = .16f + .12f * spec.blendStrength

        for (station in 0..m) {
            val u = station.toFloat() / m
            val y = spec.length * (u - .5f)
            val growth = 1f + flangeAmplitude * envelope(u, .60f, blendWidth)
            for (k in 0 until n) {
                val angle = 2.0 * PI * k / n
                vertices += Vec3(baseX * growth * cos(angle).toFloat(), y,
                    baseZ * growth * sin(angle).toFloat())
            }
        }
        for (station in 0..m) {
            val y = spec.length * (station.toFloat() / m - .5f)
            for (k in 0 until n) {
                val angle = 2.0 * PI * k / n
                vertices += Vec3(baseX * holeRatio * cos(angle).toFloat(), y,
                    baseZ * holeRatio * sin(angle).toFloat())
            }
        }
        // The two tubes have opposite winding; the annuli share both actual
        // vertex rings. Every indexed edge is used by exactly two triangles.
        for (station in 0 until m) for (k in 0 until n) {
            val next = (k + 1) % n
            val a = station * n + k
            val b = station * n + next
            val c = (station + 1) * n + k
            val d = (station + 1) * n + next
            triangles.addAll(listOf(a, b, c, b, d, c))
            val ia = innerOffset + a
            val ib = innerOffset + b
            val ic = innerOffset + c
            val id = innerOffset + d
            triangles.addAll(listOf(ia, ic, ib, ib, ic, id))
        }
        for (k in 0 until n) {
            val next = (k + 1) % n
            val o0 = k
            val o1 = next
            val i0 = innerOffset + k
            val i1 = innerOffset + next
            triangles.addAll(listOf(o0, i0, o1, o1, i0, i1))
            val oe0 = m * n + k
            val oe1 = m * n + next
            val ie0 = innerOffset + m * n + k
            val ie1 = innerOffset + m * n + next
            triangles.addAll(listOf(oe0, oe1, ie0, oe1, ie1, ie0))
        }

        var volume6 = 0.0
        for (i in triangles.indices step 3) {
            val a = vertices[triangles[i]]
            val b = vertices[triangles[i+1]]
            val c = vertices[triangles[i+2]]
            volume6 += (
                a.x * (b.y*c.z - b.z*c.y) +
                a.y * (b.z*c.x - b.x*c.z) +
                a.z * (b.x*c.y - b.y*c.x)).toDouble()
        }
        require(volume6.isFinite() && abs(volume6) > 1e-5) {
            "Native through-bore shell must enclose positive material"
        }
        if (volume6 < 0.0) for (i in triangles.indices step 3) {
            val temp = triangles[i+1]
            triangles[i+1] = triangles[i+2]
            triangles[i+2] = temp
        }
        return MeshPart("Single-shell through-bore flanged interface",
            0x93ABB9, vertices, triangles)
    }
}
