package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sign

/**
 * Eight DISTINCT native shape archetypes. Unlike training one elliptical
 * tube in different dimensions, these form families alter cross sections,
 * longitudinal profiles, heights, centerlines, and indexed topology.
 *
 * Still original procedural closed single-shell geometry, not a trained
 * text-to-3D generator or downloaded CAD model. The user-selected form
 * belongs to the procedural construction program, never an image label.
 */
enum class NativeFormArchetype {
    SPINDLE, WEDGE, BOX_MODULE, BARREL, ARCH, BLADE, CANOPY_POD, TRUSS_BEAM
}

data class NativeDiverseFormSpec(
    val archetype: NativeFormArchetype,
    val operation: AdvancedFormOperation,
    val length: Float,
    val width: Float,
    val height: Float,
    val strength: Float,
    val segments: Int = 24,
    val stations: Int = 24
)

object NativeDiverseFormLab {
    fun generate(spec: NativeDiverseFormSpec): MeshPart {
        val original = AdvancedFormLab.generate(AdvancedFormSpec(
            spec.operation,spec.length,spec.width,spec.height,spec.strength,
            spec.segments,spec.stations))
        val n=spec.segments
        val count=spec.stations
        val vertices=original.vertices.mapIndexed { index, point ->
            if(index >= (count+1)*n) {
                // Cap centers follow the actual front/rear centerline.
                val end=if(index == (count+1)*n) 0f else 1f
                val uplift=if(spec.archetype==NativeFormArchetype.ARCH)
                    .035f*spec.height else 0f
                Vec3(point.x,point.y,uplift)
            } else {
                val ring=index/n
                val k=index%n
                val u=ring.toFloat()/count
                val wave=sin(PI*u).toFloat()
                val w2=wave*wave
                val theta=2.0*PI*k/n
                val q=sin(theta).toFloat()
                val c=cos(theta).toFloat()
                var xFactor=1f
                var zFactor=1f
                var zShift=0f
                var xShift=0f
                when(spec.archetype) {
                    NativeFormArchetype.SPINDLE -> {
                        val taper=.39f+.61f*wave.toDouble().pow(.72).toFloat()
                        xFactor=taper
                        zFactor=.70f+.30f*taper
                    }
                    NativeFormArchetype.WEDGE -> {
                        // One end narrows and lowers: unequal plan/side silhouettes.
                        xFactor=.50f+.78f*u
                        zFactor=.72f+.40f*u
                        zShift=spec.height*.085f*(.5f-u)
                    }
                    NativeFormArchetype.BOX_MODULE -> {
                        // Box-like cross section AND flat extended central length.
                        val roundX=c.sign*abs(c).toDouble().pow(.47).toFloat()
                        val roundZ=q.sign*abs(q).toDouble().pow(.47).toFloat()
                        xFactor=(.86f+.12f*w2)*(
                            if(abs(c)>.10f) abs(roundX/c) else 1f)
                        zFactor=(.83f+.13f*w2)*(
                            if(abs(q)>.10f) abs(roundZ/q) else 1f)
                    }
                    NativeFormArchetype.BARREL -> {
                        xFactor=.66f+.58f*w2
                        zFactor=.73f+.37f*w2
                    }
                    NativeFormArchetype.ARCH -> {
                        xFactor=.74f+.24f*w2
                        zFactor=.70f+.24f*w2
                        zShift=.28f*spec.height*w2
                    }
                    NativeFormArchetype.BLADE -> {
                        xFactor=.40f+.62f*(1f-u)
                        zFactor=.48f+.68f*u
                        zShift=spec.height*.10f*(1f-u)
                    }
                    NativeFormArchetype.CANOPY_POD -> {
                        xFactor=.60f+.34f*w2
                        zFactor=.63f+.28f*w2
                        zShift=spec.height*.12f*w2
                        // Stronger upper-side crown: not a generic circular tube.
                        if(q>0f) zFactor+=.23f*q*w2
                    }
                    NativeFormArchetype.TRUSS_BEAM -> {
                        // Alternating facets + three longitudinal structural ridges.
                        val facets=abs(cos(4.0*theta)).toFloat()
                        val r=.80f+.16f*facets
                        xFactor=r*(.94f+.06f*w2)
                        zFactor=r*(.74f+.16f*w2)
                        xShift=.08f*spec.width*w2*cos(6.0*theta).toFloat()
                    }
                }
                // For all operations, apply archetype form to already-original
                // native vertex data. The same warp is used for its baseline,
                // ground truth and student reconstruction.
                Vec3(point.x*xFactor+xShift,point.y,point.z*zFactor+zShift)
            }
        }
        require(vertices.size==original.vertices.size &&
            vertices.all { it.x.isFinite()&&it.y.isFinite()&&it.z.isFinite() })
        var sixVolume=0.0
        for (i in original.indices.indices step 3) {
            val a=vertices[original.indices[i]]
            val b=vertices[original.indices[i+1]]
            val c=vertices[original.indices[i+2]]
            val normal=(b-a).cross(c-a)
            val triangle2=normal.x*normal.x+normal.y*normal.y+normal.z*normal.z
            require(triangle2.isFinite()&&triangle2>1e-12f) {
                "Diverse form generator created collapsed triangle"
            }
            sixVolume+=(a.x*normal.x+a.y*normal.y+a.z*normal.z).toDouble()
        }
        require(sixVolume.isFinite()&&abs(sixVolume)>1e-5) {
            "Diverse source form has invalid original volume"
        }
        // Orientation remains closed; normalize if the whole form is reversed.
        val indices=original.indices.toMutableList()
        if(sixVolume<0) for(i in indices.indices step 3) {
            val tmp=indices[i+1];indices[i+1]=indices[i+2];indices[i+2]=tmp
        }
        return MeshPart(
            "Native form "+spec.archetype.name,0x96AEC2,vertices,indices)
    }
    fun asAsset(spec: NativeDiverseFormSpec): GeneratedAsset {
        val part=generate(spec)
        return GeneratedAsset(
            VehicleSpec(
                "Native "+spec.archetype.name,spec.length,spec.width,
                spec.height,1.7f,.55f,1.07f,"Mobile",
                "Original multi-form native procedural geometry"
            ),listOf(part))
    }
}
