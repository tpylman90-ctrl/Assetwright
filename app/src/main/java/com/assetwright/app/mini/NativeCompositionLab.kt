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
 * Three native operations blended on ONE indexed manifold loft.
 * This is an independent composition laboratory: it does not change
 * AdvancedFormLab, its frozen 912-GLB result, or the Android generator.
 */
data class NativeCompositionCommand(
    val operation: AdvancedFormOperation,
    val strength: Float
)

data class NativeCompositionSpec(
    val length: Float,
    val width: Float,
    val height: Float,
    val commands: List<NativeCompositionCommand>,
    val segments: Int = 32,
    val stations: Int = 32
)

object NativeCompositionLab {
    val dependencyOrder = listOf(
        AdvancedFormOperation.SECTION_LOFT,
        AdvancedFormOperation.RIBBED_FAIRING,
        AdvancedFormOperation.SUPERELLIPSE_PROFILE,
        AdvancedFormOperation.LOWER_RECESS,
        AdvancedFormOperation.SECTION_TWIST,
        AdvancedFormOperation.TANGENT_SWEEP
    )
    fun validate(spec: NativeCompositionSpec) {
        require(spec.length.isFinite() && spec.length in 1f..12f)
        require(spec.width.isFinite() && spec.width in .5f..7f)
        require(spec.height.isFinite() && spec.height in .5f..7f)
        require(spec.segments in 24..48 && spec.segments % 8 == 0)
        require(spec.stations in 16..48 && spec.stations % 8 == 0)
        require(spec.commands.size == 3) { "V1 composition requires 3 distinct operations" }
        val ops=spec.commands.map { it.operation }
        require(ops.distinct().size==3)
        require(ops == ops.sortedBy { dependencyOrder.indexOf(it) }) {
            "Native surface dependencies must be respected"
        }
        require(spec.commands.all { it.strength.isFinite() &&
            it.strength in .10f..1f })
    }

    private fun smooth(x:Float):Float {
        val a=x.coerceIn(0f,1f)
        return a*a*(3f-2f*a)
    }

    fun generate(spec:NativeCompositionSpec):MeshPart {
        validate(spec)
        val controls=spec.commands.associate { it.operation to it.strength }
        fun strength(op:AdvancedFormOperation)=controls[op] ?: 0f
        val loft=strength(AdvancedFormOperation.SECTION_LOFT)
        val rib=strength(AdvancedFormOperation.RIBBED_FAIRING)
        val round=strength(AdvancedFormOperation.SUPERELLIPSE_PROFILE)
        val recess=strength(AdvancedFormOperation.LOWER_RECESS)
        val twist=strength(AdvancedFormOperation.SECTION_TWIST)
        val sweep=strength(AdvancedFormOperation.TANGENT_SWEEP)
        val n=spec.segments
        val verts=ArrayList<Vec3>((spec.stations+1)*n+2)
        val faces=ArrayList<Int>(spec.stations*n*6+2*n*3)
        val halfWidth=spec.width*.5f
        val halfHeight=spec.height*.5f
        val curveAmplitude=minOf(spec.width*.20f,spec.length*.08f)*sweep

        for (station in 0..spec.stations) {
            val u=station.toFloat()/spec.stations
            val y=spec.length*(u-.5f)
            val envelope=sin(PI*u).toFloat().let{ it*it }
            val bumpA=exp(-((u-.29f)/.145f).toDouble().pow(2.0)).toFloat()
            val bumpB=exp(-((u-.73f)/.165f).toDouble().pow(2.0)).toFloat()
            val ribWave=cos(6.0*PI*u).toFloat()
            val wScale=(1f+loft*(.27f*bumpA+.36f*bumpB))*
                (1f+.16f*rib*envelope*ribWave)
            val hScale=1f+.12f*loft*bumpB
            val exponent=1f-.57f*round
            val twistAngle=(PI*.47*u*twist).toFloat()
            val tc=cos(twistAngle)
            val ts=sin(twistAngle)
            val centerX=curveAmplitude*sin(PI*u).toFloat()
            val dCenter=curveAmplitude*(PI/spec.length).toFloat()*
                cos(PI*u).toFloat()
            val inv=sqrt(1f+dCenter*dCenter).let{1f/it}
            for(k in 0 until n) {
                val angle=2.0*PI*k/n
                val cc=cos(angle).toFloat()
                val ss=sin(angle).toFloat()
                val pxProfile=cc.sign*abs(cc).toDouble().pow(exponent.toDouble()).toFloat()
                val pzProfile=ss.sign*abs(ss).toDouble().pow(exponent.toDouble()).toFloat()
                var px=halfWidth*wScale*pxProfile
                var pz=halfHeight*hScale*pzProfile
                if(recess>0f) {
                    // Local body sculpt BEFORE twist and curved sweep; upper
                    // and lower shoulders remain on this same connected shell.
                    val groove=smooth(1f-abs(ss+.7071068f)/.42f)
                    px*=1f-.34f*recess*envelope*groove
                    pz+=.08f*spec.height*recess*envelope*
                        smooth((-ss-.73f)/.25f)
                }
                val rotatedX=px*tc-pz*ts
                val rotatedZ=px*ts+pz*tc
                verts+=Vec3(centerX+rotatedX*inv,
                    y-rotatedX*dCenter*inv,rotatedZ)
            }
        }
        for(station in 0 until spec.stations) for(k in 0 until n) {
            val b=(k+1)%n
            val a=station*n+k
            val c=(station+1)*n+k
            faces.addAll(listOf(a,station*n+b,c,station*n+b,c+(b-k),c))
        }
        val first=verts.size
        verts+=Vec3(0f,-spec.length*.5f,0f)
        val last=verts.size
        verts+=Vec3(0f,spec.length*.5f,0f)
        val back=spec.stations*n
        for(k in 0 until n) {
            val next=(k+1)%n
            faces.addAll(listOf(first,next,k))
            faces.addAll(listOf(last,back+k,back+next))
        }
        var signed6=0.0
        for(i in faces.indices step 3) {
            val a=verts[faces[i]]
            val b=verts[faces[i+1]]
            val c=verts[faces[i+2]]
            signed6+=(a.x*(b.y*c.z-b.z*c.y)+
                a.y*(b.z*c.x-b.x*c.z)+a.z*(b.x*c.y-b.y*c.x)).toDouble()
        }
        require(signed6.isFinite() && abs(signed6)>1e-6) { "Degenerate native program" }
        if(signed6<0)for(i in faces.indices step 3) {
            val v=faces[i+1]; faces[i+1]=faces[i+2];faces[i+2]=v
        }
        return MeshPart("Native three-operation continuous hull",
            0x93AABF,verts,faces)
    }
}
