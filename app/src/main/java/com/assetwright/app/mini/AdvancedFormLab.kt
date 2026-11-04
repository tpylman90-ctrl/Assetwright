package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.pow
import kotlin.math.sign
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Research-only generalized geometry lessons built with OUR indexed mesh
 * engine. None is a downloaded mesh, a Boolean cutout, or a Class-A NURBS.
 * This deliberately does not alter the Android production generator.
 */
enum class AdvancedFormOperation {
    SECTION_LOFT, TANGENT_SWEEP, SECTION_TWIST,
    SUPERELLIPSE_PROFILE, LOWER_RECESS, RIBBED_FAIRING
}

data class AdvancedFormSpec(
    val operation: AdvancedFormOperation,
    val length: Float,
    val width: Float,
    val height: Float,
    val strength: Float,
    val segments: Int = 24,
    val stations: Int = 24
)

object AdvancedFormLab {
    private fun ease(x: Float): Float {
        val v=x.coerceIn(0f,1f)
        return v*v*(3f-2f*v)
    }

    fun generate(spec: AdvancedFormSpec): MeshPart {
        require(spec.length.isFinite() && spec.length in 1f..12f)
        require(spec.width.isFinite() && spec.width in .5f..7f)
        require(spec.height.isFinite() && spec.height in .5f..7f)
        require(spec.strength.isFinite() && spec.strength in 0f..1f)
        require(spec.segments in 24..48 && spec.segments % 8 == 0)
        require(spec.stations in 16..32 && spec.stations % 8 == 0)
        val n=spec.segments
        val rings=spec.stations+1
        val vertices=ArrayList<Vec3>(rings*n+2)
        val indices=ArrayList<Int>(spec.stations*n*6+2*n*3)
        val hx=spec.width*.5f
        val hz=spec.height*.5f
        val bendAmplitude=minOf(spec.width*.20f,spec.length*.08f)*spec.strength

        for (ring in 0..spec.stations) {
            val u=ring.toFloat()/spec.stations
            val axis=spec.length*(u-.5f)
            val sinus=sin(PI*u).toFloat()
            val pathX=if(spec.operation==AdvancedFormOperation.TANGENT_SWEEP)
                bendAmplitude*sinus else 0f
            val tangent=if(spec.operation==AdvancedFormOperation.TANGENT_SWEEP)
                bendAmplitude*(PI/spec.length).toFloat()*cos(PI*u).toFloat() else 0f
            // The local right vector is perpendicular to the actual curved
            // centerline tangent. Unlike prior fixed-frame sweep research,
            // this frame also moves cross-section Y coordinates.
            val invLength=1f/sqrt(1f+tangent*tangent)

            val loftA=exp(-((u-.29f)/.145f).toDouble().pow(2.0)).toFloat()
            val loftB=exp(-((u-.73f)/.165f).toDouble().pow(2.0)).toFloat()
            val smoothWindow=(sinus*sinus).coerceIn(0f,1f)
            val ridge=cos(6.0*PI*u).toFloat()
            val widthScale=when(spec.operation) {
                AdvancedFormOperation.SECTION_LOFT ->
                    1f+spec.strength*(.27f*loftA+.36f*loftB)
                AdvancedFormOperation.RIBBED_FAIRING ->
                    1f+.16f*spec.strength*smoothWindow*ridge
                else -> 1f
            }
            val heightScale=if(spec.operation==AdvancedFormOperation.SECTION_LOFT)
                1f+.12f*spec.strength*loftB else 1f
            val twist=if(spec.operation==AdvancedFormOperation.SECTION_TWIST)
                (PI*.47*u*spec.strength).toFloat() else 0f
            val tc=cos(twist)
            val ts=sin(twist)
            val exponent=if(spec.operation==AdvancedFormOperation.SUPERELLIPSE_PROFILE)
                1f-.57f*spec.strength else 1f

            for (k in 0 until n) {
                val angle=2.0*PI*k/n
                val cc=cos(angle).toFloat()
                val ss=sin(angle).toFloat()
                val profileX=cc.sign*abs(cc).toDouble().pow(exponent.toDouble()).toFloat()
                val profileZ=ss.sign*abs(ss).toDouble().pow(exponent.toDouble()).toFloat()
                var px=hx*widthScale*profileX
                var pz=hz*heightScale*profileZ
                if(spec.operation==AdvancedFormOperation.LOWER_RECESS) {
                    // Paired lower-side channels on the SAME connected shell.
                    // Ends remain intact, and the lip transitions are smooth.
                    val angular=ease((1f-abs(ss+.7071068f)/.42f))
                    px*=1f-.34f*spec.strength*smoothWindow*angular
                    pz+=.08f*spec.height*spec.strength*smoothWindow*
                        ease((-ss-.73f)/.25f)
                }
                if(spec.operation==AdvancedFormOperation.SECTION_TWIST) {
                    val oldX=px
                    px=oldX*tc-pz*ts
                    pz=oldX*ts+pz*tc
                }
                vertices+=Vec3(pathX+px*invLength,
                    axis-px*tangent*invLength,pz)
            }
        }
        for (ring in 0 until spec.stations) for (k in 0 until n) {
            val next=(k+1)%n
            val a=ring*n+k
            val b=ring*n+next
            val c=(ring+1)*n+k
            val d=(ring+1)*n+next
            indices.addAll(listOf(a,b,c,b,d,c))
        }
        val firstCenter=vertices.size
        vertices+=Vec3(0f,-spec.length*.5f,0f)
        val lastCenter=vertices.size
        vertices+=Vec3(0f,spec.length*.5f,0f)
        val rear=spec.stations*n
        for(k in 0 until n) {
            val next=(k+1)%n
            indices.addAll(listOf(firstCenter,next,k))
            indices.addAll(listOf(lastCenter,rear+k,rear+next))
        }
        var volume6=0.0
        for (i in indices.indices step 3) {
            val a=vertices[indices[i]]
            val b=vertices[indices[i+1]]
            val c=vertices[indices[i+2]]
            volume6+=(a.x*(b.y*c.z-b.z*c.y)+
                      a.y*(b.z*c.x-b.x*c.z)+
                      a.z*(b.x*c.y-b.y*c.x)).toDouble()
        }
        require(volume6.isFinite() && abs(volume6)>1e-5) {
            "Degenerate original advanced native form"
        }
        if(volume6<0) for(i in indices.indices step 3) {
            val temp=indices[i+1]
            indices[i+1]=indices[i+2]
            indices[i+2]=temp
        }
        return MeshPart("Original advanced form",0x98B8D4,vertices,indices)
    }
}
