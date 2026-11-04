package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sign
import kotlin.math.sin

/**
 * Original, research-only form vocabulary independent of vehicle prompts.
 * Native Z-up geometry; only our GlbWriter converts coordinates to glTF.
 */
enum class NativeFormKind { CYLINDER, ROUNDED_BOX, ELLIPSOID, TAPERED_LOFT, ARCH_SWEEP }

data class NativeFormSpec(
    val kind: NativeFormKind,
    val length: Float,
    val width: Float,
    val height: Float,
    val strength: Float,
    val segments: Int = 32,
    val stations: Int = 16
)

object NativeFormLab {
    fun generate(spec: NativeFormSpec): MeshPart {
        require(spec.length.isFinite() && spec.length in .5f..12f)
        require(spec.width.isFinite() && spec.width in .3f..8f)
        require(spec.height.isFinite() && spec.height in .3f..8f)
        require(spec.strength.isFinite() && spec.strength in 0f..1f)
        require(spec.segments in 16..64 && spec.segments % 8 == 0)
        require(spec.stations in 8..32)
        val rings = spec.stations + 1
        val verts = ArrayList<Vec3>(rings * spec.segments + 2)
        val triangles = ArrayList<Int>()
        val rx = spec.width * .5f
        val rz = spec.height * .5f
        for (station in 0 until rings) {
            val u = station.toFloat() / spec.stations
            val axial = spec.length * (u - .5f)
            val along = sin(PI * u).toFloat()
            // Tiny non-zero end rings avoid degenerate bulb pole faces.
            val bulb = maxOf(.06f, along).toDouble().pow(
                (.72f + .45f * spec.strength).toDouble()
            ).toFloat()
            val sweepX = .38f * spec.width * spec.strength * along
            val taper = 1f + .85f * spec.strength * (u - .5f)
            val exponent = .95f - .62f * spec.strength
            for (k in 0 until spec.segments) {
                val a = 2.0 * PI * k / spec.segments
                val cc = cos(a).toFloat()
                val ss = sin(a).toFloat()
                val (xShape,zShape) = if (spec.kind == NativeFormKind.ROUNDED_BOX) {
                    // Rounded-rectangle superellipse, within one indexed shell.
                    (cc.sign * abs(cc).toDouble().pow(exponent.toDouble()).toFloat()) to
                    (ss.sign * abs(ss).toDouble().pow(exponent.toDouble()).toFloat())
                } else cc to ss
                val widthScale = when (spec.kind) {
                    // A cylinder's native strength is radius expansion.
                    // Every training level must create genuinely different
                    // source-hashed geometry, not duplicate GLB labels.
                    NativeFormKind.CYLINDER -> .80f + .40f * spec.strength
                    NativeFormKind.ELLIPSOID -> bulb
                    NativeFormKind.TAPERED_LOFT -> taper
                    else -> 1f
                }
                val heightScale = if (spec.kind == NativeFormKind.ELLIPSOID) bulb else 1f
                val pathX = if (spec.kind == NativeFormKind.ARCH_SWEEP) sweepX else 0f
                // V1 sweep uses fixed-orientation cross sections. No claim of
                // parallel-transport frames or true NURBS continuity.
                verts += Vec3(pathX + rx * widthScale * xShape,
                              axial, rz * heightScale * zShape)
            }
        }
        val n = spec.segments
        for (station in 0 until rings - 1) {
            for (k in 0 until n) {
                val next = (k + 1) % n
                val a = station * n + k
                val b = station * n + next
                val c = (station + 1) * n + k
                val d = (station + 1) * n + next
                triangles.addAll(listOf(a, b, c, b, d, c))
            }
        }
        val startCenter = verts.size
        verts += Vec3(0f,-spec.length*.5f,0f)
        val endCenter = verts.size
        verts += Vec3(0f,spec.length*.5f,0f)
        val last = (rings-1)*n
        for (k in 0 until n) {
            val next = (k + 1) % n
            triangles.addAll(listOf(startCenter,next,k))
            triangles.addAll(listOf(endCenter,last+k,last+next))
        }
        var signedVolumeSix = 0.0
        for (i in triangles.indices step 3) {
            val a=verts[triangles[i]]
            val b=verts[triangles[i+1]]
            val c=verts[triangles[i+2]]
            signedVolumeSix += (
                a.x*(b.y*c.z-b.z*c.y) +
                a.y*(b.z*c.x-b.x*c.z) +
                a.z*(b.x*c.y-b.y*c.x)).toDouble()
        }
        require(abs(signedVolumeSix) > 1e-7) { "Degenerate original form" }
        if (signedVolumeSix < 0.0) {
            for (i in triangles.indices step 3) {
                val tmp = triangles[i+1]
                triangles[i+1] = triangles[i+2]
                triangles[i+2] = tmp
            }
        }
        return MeshPart("Original form",0xAAB9C7,verts,triangles)
    }
}
