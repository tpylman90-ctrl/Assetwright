package com.assetwright.app.mini

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Research-only genuine side-junction topology on the original hollow housing.
 * An exterior quad patch is removed, its EXISTING perimeter vertices are
 * stitched to an integrated boss, and that boss terminates in a blind socket.
 * The original longitudinal through-bore remains open and unaffected.
 *
 * This is NOT an intersecting mesh, arbitrary Boolean solver, nor a
 * through-connected T-junction. The boss socket is intentionally blind.
 */
data class NativeBranchSpec(
    val length: Float,
    val width: Float,
    val height: Float,
    val site: Int,               // five longitudinal slots × four directions
    val rise: Float,
    val socketDepth: Float,
    val blend: Float
)

object NativeBranchLab {
    private const val RADIAL = 32
    private const val STATIONS = 40
    private const val PATCH_AXIAL = 6
    private const val PATCH_ANGULAR = 8
    private val starts = intArrayOf(5,11,17,23,29)
    const val SITES = 20
    const val VERTICES = 2730
    const val TRIANGLES = 5460
    const val EDGES = 8190

    fun validate(s: NativeBranchSpec) {
        require(s.length.isFinite() && s.length in 2f..12f)
        require(s.width.isFinite() && s.width in .7f..7f)
        require(s.height.isFinite() && s.height in .6f..7f)
        require(s.site in 0 until SITES)
        for (v in listOf(s.rise,s.socketDepth,s.blend))
            require(v.isFinite() && v in 0f..1f)
    }
    private fun multiply(v:Vec3,s:Float)=Vec3(v.x*s,v.y*s,v.z*s)
    private fun dot(a:Vec3,b:Vec3)=a.x*b.x+a.y*b.y+a.z*b.z

    fun generate(spec:NativeBranchSpec):MeshPart {
        validate(spec)
        val parent=NativeInterfaceLab.generate(NativeInterfaceSpec(
            spec.length,spec.width,spec.height,.48f,.40f,.50f))
        require(parent.vertices.size==2624 && parent.indices.size/3==5248)
        val vertices=parent.vertices.toMutableList()
        val faces=ArrayList<Int>()
        val axialStart=starts[spec.site/4]
        val angleCenterIndex=(spec.site%4)*8
        val angularStart=(angleCenterIndex+RADIAL-4)%RADIAL
        fun inPatch(j:Int,k:Int):Boolean =
            j in axialStart until (axialStart+PATCH_AXIAL) &&
                (k-angularStart+RADIAL)%RADIAL<PATCH_ANGULAR
        // NativeInterfaceLab always emits two outer and two inner triangles
        // per quad, followed by the two intact through-bore end annuli.
        val outerInnerQuads=STATIONS*RADIAL
        for(triangle in parent.indices.indices step 3) {
            val faceOrdinal=triangle/3
            val quad=faceOrdinal/4
            val removed=quad<outerInnerQuads && faceOrdinal%4<2 &&
                inPatch(quad/RADIAL,quad%RADIAL)
            if(!removed) for (i in 0..2) faces.add(parent.indices[triangle+i])
        }
        val boundary=ArrayList<Int>(2*(PATCH_ANGULAR+PATCH_AXIAL))
        for(k in 0 until PATCH_ANGULAR)
            boundary.add(axialStart*RADIAL+(angularStart+k)%RADIAL)
        for(j in 0 until PATCH_AXIAL)
            boundary.add((axialStart+j)*RADIAL+
                (angularStart+PATCH_ANGULAR)%RADIAL)
        for(k in 0 until PATCH_ANGULAR)
            boundary.add((axialStart+PATCH_AXIAL)*RADIAL+
                (angularStart+PATCH_ANGULAR-k)%RADIAL)
        for(j in 0 until PATCH_AXIAL)
            boundary.add((axialStart+PATCH_AXIAL-j)*RADIAL+angularStart)
        require(boundary.size==28 && boundary.toSet().size==28)
        val center=Vec3(
            boundary.sumOf { vertices[it].x.toDouble() }.toFloat()/28f,
            boundary.sumOf { vertices[it].y.toDouble() }.toFloat()/28f,
            boundary.sumOf { vertices[it].z.toDouble() }.toFloat()/28f
        )
        val angle=(2.0*PI*angleCenterIndex/RADIAL)
        val normal=Vec3(cos(angle).toFloat(),0f,sin(angle).toFloat())
        val height=min(spec.width,spec.height)*(.28f+.65f*spec.rise)
        val ringCount=boundary.size
        val perimeter=boundary.map { vertices[it]-center }

        val rings=ArrayList<List<Int>>()
        rings.add(boundary)
        fun addRing(progress:Float,scale:Float,flatten:Float):List<Int> {
            return perimeter.map { offset ->
                val flattened=offset-multiply(normal,dot(offset,normal)*flatten)
                val p=center+multiply(flattened,scale)+multiply(normal,height*progress)
                val index=vertices.size
                vertices.add(p)
                index
            }
        }
        rings.add(addRing(.14f,1.08f+.08f*spec.blend,.18f+.24f*spec.blend))
        rings.add(addRing(.48f,.98f-.07f*spec.blend,.58f+.24f*spec.blend))
        rings.add(addRing(1f,.86f-.13f*spec.blend,1f))
        // Top annulus transitions to a real open socket, not a painted cap.
        rings.add(addRing(1f,.42f,1f))
        val socketFloor=1f-(.17f+.37f*spec.socketDepth)
        rings.add(addRing(socketFloor,.42f,1f))
        for (pair in 0 until rings.size-1) {
            val inner=rings[pair]
            val outer=rings[pair+1]
            for(k in 0 until ringCount) {
                val next=(k+1)%ringCount
                faces.addAll(listOf(
                    inner[k],inner[next],outer[k],
                    inner[next],outer[next],outer[k]))
            }
        }
        val bottomIndex=vertices.size
        vertices.add(center+multiply(normal,height*socketFloor))
        for(k in 0 until ringCount) {
            val next=(k+1)%ringCount
            faces.addAll(listOf(rings.last()[k],rings.last()[next],bottomIndex))
        }

        // Removing the patch creates 35 unreachable original grid vertices.
        // Compact ALL positions and indices so no disconnected vertices
        // artificially inflate Euler characteristic or confuse learning.
        val mapping=IntArray(vertices.size) { -1 }
        val compact=ArrayList<Vec3>()
        val remapped=ArrayList<Int>(faces.size)
        for(old in faces) {
            if(mapping[old]<0) {
                mapping[old]=compact.size
                compact.add(vertices[old])
            }
            remapped.add(mapping[old])
        }
        require(compact.size==VERTICES && remapped.size/3==TRIANGLES) {
            "Native connected-junction source geometry changed unexpectedly"
        }
        var signedSix=0.0
        for(i in remapped.indices step 3) {
            val a=compact[remapped[i]]
            val b=compact[remapped[i+1]]
            val c=compact[remapped[i+2]]
            signedSix+=(
                a.x*(b.y*c.z-b.z*c.y)+
                a.y*(b.z*c.x-b.x*c.z)+
                a.z*(b.x*c.y-b.y*c.x)).toDouble()
        }
        require(signedSix.isFinite() && abs(signedSix)>1e-5)
        if(signedSix<0)for(i in remapped.indices step 3) {
            val t=remapped[i+1]
            remapped[i+1]=remapped[i+2]
            remapped[i+2]=t
        }
        return MeshPart("Continuous body with integrated blind socket branch",
            0xA5BCCC,compact,remapped)
    }
}
