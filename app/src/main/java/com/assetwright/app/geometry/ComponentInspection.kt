package com.assetwright.app.geometry

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.*

/**
 * Component = source GLB node/mesh primitive by default. An unlabeled GLB
 * does not magically contain semantic 'robotic arm' etc. Optional manual
 * labels are review metadata, never changes to the mesh.
 */
data class PartHealth(
    val source: GeometryPart,
    val triangles: Int,
    val vertices: Int,
    val surfaceArea: Double,
    val bounds: FloatArray,
    val degenerateTriangles: Int,
    val boundaryEdges: Int?,
    val nonmanifoldEdges: Int?,
    val edgeCountExact: Boolean,
    val sharpVertexFraction: Double,
    val highCurvatureFraction: Double,
    val meanAbsoluteCurvature: Double,
    val normalDirectionalCoherence: Double,
    val triangleDensity: Double,
    val flags: List<String>
)

private fun edgeKey(a: Int,b: Int):Long {
    val x=min(a,b);val y=max(a,b)
    return (x.toLong() shl 32) or (y.toLong() and 0xffffffffL)
}

private fun hint(name:String):String? {
    // Do not infer semantic identity from geometry alone. Use source names.
    val s=name.lowercase()
    return when {
        "gripper" in s || "end effector" in s || "end_effector" in s -> "gripper"
        "battery" in s || "cassette" in s || "cell swap" in s -> "battery cassette"
        "control cabinet" in s || "control_cabinet" in s || "electrical cabinet" in s -> "control cabinet"
        "enclosure" in s || "housing" in s -> "enclosure"
        "robot" in s || "manipulator" in s || "arm assembly" in s -> "robotic arm"
        else -> null
    }
}

fun GeometryMesh.partHealth():List<PartHealth> {
    // Work with real named GLB parts. This is source-mesh-primitive-level
    // grouping; a GLB fused into one mesh needs desktop segmentation.
    val curve=curvature
    val edgesSeverity=sharpness
    val output=ArrayList<PartHealth>()
    for(part in parts){
        val begin=part.firstTriangle
        val end=(begin+part.triangleCount).coerceAtMost(count)
        val first=part.firstVertex
        val last=(first+part.vertexCount).coerceAtMost(n)
        if(end<=begin || last<=first)continue
        val lo=FloatArray(3){Float.POSITIVE_INFINITY}
        val hi=FloatArray(3){Float.NEGATIVE_INFINITY}
        var sharp=0
        var bend=0
        var absBend=0.0
        for(v in first until last) {
            val x=v*3
            for(d in 0..2) {
                lo[d]=min(lo[d],xyz[x+d]);hi[d]=max(hi[d],xyz[x+d])
            }
            if(edgesSeverity[v]>=35f)sharp++
            if(abs(curve[v])>=0.12f)bend++
            absBend+=abs(curve[v]).toDouble()
        }
        var area=0.0
        var degenerate=0
        var nx=0.0;var ny=0.0;var nz=0.0
        // On dense meshes exact edge maps can exceed phone memory. In that
        // case explicitly report topology counts as unknown, not zero.
        val exact=part.triangleCount <= 80_000
        val edgeCounts=if(exact)HashMap<Long,Int>(part.triangleCount*2) else null
        for(t in begin until end) {
            val a=triangles[3*t];val b=triangles[3*t+1];val c=triangles[3*t+2]
            val ai=a*3;val bi=b*3;val ci=c*3
            val ux=(xyz[bi]-xyz[ai]).toDouble()
            val uy=(xyz[bi+1]-xyz[ai+1]).toDouble()
            val uz=(xyz[bi+2]-xyz[ai+2]).toDouble()
            val vx=(xyz[ci]-xyz[ai]).toDouble()
            val vy=(xyz[ci+1]-xyz[ai+1]).toDouble()
            val vz=(xyz[ci+2]-xyz[ai+2]).toDouble()
            val cx=uy*vz-uz*vy;val cy=uz*vx-ux*vz;val cz=ux*vy-uy*vx
            val norm=sqrt(cx*cx+cy*cy+cz*cz)
            if(norm<1e-10)degenerate++ else {
                area+=norm*.5
                nx+=cx*.5;ny+=cy*.5;nz+=cz*.5
            }
            if(edgeCounts!=null)for((u,v) in arrayOf(a to b,b to c,c to a)) {
                val key=edgeKey(u,v)
                edgeCounts[key]=(edgeCounts[key]?:0)+1
            }
        }
        val bounding=floatArrayOf(lo[0],lo[1],lo[2],hi[0],hi[1],hi[2])
        val density=part.triangleCount/area.coerceAtLeast(1e-9)
        // Area-weighted normals cancel on closed objects. This is a
        // directional-coherence indicator, not evidence of bad alignment.
        val coherence=sqrt(nx*nx+ny*ny+nz*nz)/area.coerceAtLeast(1e-9)
        val boundary=edgeCounts?.values?.count{it==1}
        val nonManifold=edgeCounts?.values?.count{it>2}
        val flags=ArrayList<String>()
        if(degenerate>0)flags.add("$degenerate zero-area/degenerate triangles")
        if(nonManifold!=null && nonManifold>0)flags.add("$nonManifold non-manifold indexed edges")
        if(boundary!=null && boundary>0)flags.add("$boundary indexed boundary edges (may include UV seams)")
        if(bend.toDouble()/part.vertexCount>=0.35)flags.add("Large fraction of high local bending; inspect for deliberate mechanical complexity or reconstruction noise")
        if(sharp.toDouble()/part.vertexCount>=0.45)flags.add("Many abrupt face-angle changes; inspect surface continuity")
        output.add(PartHealth(
            part,part.triangleCount,part.vertexCount,area,bounding,
            degenerate,boundary,nonManifold,exact,
            sharp.toDouble()/part.vertexCount,
            bend.toDouble()/part.vertexCount,
            absBend/part.vertexCount,
            coherence,density,flags
        ))
    }
    // Relative overload is only meaningful with enough comparable components.
    val densityMedian=output.map{it.triangleDensity}.filter{it.isFinite()&&it>0}
        .sorted().let { if(it.isEmpty())0.0 else it[it.size/2] }
    val total=output.sumOf{it.triangles}.coerceAtLeast(1)
    return output.map{it.copy(flags=it.flags + buildList {
        if(output.size>=3 && densityMedian>0 && it.triangleDensity>densityMedian*4 &&
            it.triangles>1000) add("Triangle density >4x part median; review for polygon budget")
        if(it.triangles>total*0.40 && output.size>=3)
            add("Uses >40% of entire model's triangles; review relative allocation")
    })}
}

fun GeometryMesh.componentInspectionJson(
    reports:List<PartHealth>,
    userLabels:Map<Int,String> = emptyMap(),
    selectedId:Int? = null
):String {
    val root=JSONObject()
    root.put("schema","assetwright.component_inspection.v1")
    root.put("model",name)
    root.put("original_modified",false)
    root.put("grouping","original GLB nodes/mesh primitives")
    root.put("component_count",reports.size)
    root.put("model_triangles",count)
    val all=JSONArray()
    for (r in reports) {
        val p=r.source
        val requested=userLabels[p.id]?.takeIf{it.isNotBlank()}
        val category=requested?:hint(p.sourceName)
        val e=JSONObject()
        e.put("id",p.id)
        e.put("name",requested?:p.sourceName)
        e.put("source_name",p.sourceName)
        e.put("source_path",p.sourcePath)
        e.put("category",category?:JSONObject.NULL)
        e.put("category_basis",when {
            requested!=null->"user-provided label"
            category!=null->"matched source GLB name; verify"
            else->"unclassified"
        })
        e.put("triangles",r.triangles)
        e.put("vertices",r.vertices)
        e.put("share_of_model_triangles",r.triangles.toDouble()/count.coerceAtLeast(1))
        e.put("surface_area_source_units_squared",r.surfaceArea)
        e.put("triangles_per_square_source_unit",r.triangleDensity)
        e.put("bounds",JSONArray(r.bounds.map{it.toDouble()}))
        e.put("degenerate_triangles",r.degenerateTriangles)
        e.put("boundary_edges",r.boundaryEdges?:JSONObject.NULL)
        e.put("nonmanifold_edges",r.nonmanifoldEdges?:JSONObject.NULL)
        e.put("indexed_edge_analysis_exact",r.edgeCountExact)
        e.put("fraction_vertices_crease_35deg",r.sharpVertexFraction)
        e.put("fraction_vertices_local_bending_over_0_12",r.highCurvatureFraction)
        e.put("mean_absolute_local_bending_proxy",r.meanAbsoluteCurvature)
        e.put("face_normal_directional_coherence",r.normalDirectionalCoherence)
        e.put("diagnostic_flags",JSONArray(r.flags))
        all.put(e)
    }
    root.put("parts",all)
    if(selectedId!=null)root.put("selected_component_id",selectedId)
    val requestedLabels=listOf("robotic arm","gripper","battery cassette","enclosure","control cabinet")
    val matched=JSONObject()
    for(c in requestedLabels) {
        val ids=reports.filter { (userLabels[it.source.id]?:hint(it.source.sourceName))?.lowercase()==c }
            .map{it.source.id}
        matched.put(c,if(ids.isEmpty()) JSONObject().put("status","not identified in imported GLB")
            else JSONObject().put("status","identified by name or user label").put("component_ids",JSONArray(ids)))
    }
    root.put("requested_assembly_groups",matched)
    root.put("warnings",JSONArray(listOf(
        "Parts are grouped by source GLB node/mesh primitive, not learned semantic segmentation.",
        "A fused mesh must be separated for reliable named-part reports.",
        "Polygon overload thresholds are relative heuristics, not universal quality standards.",
        "Indexed boundaries may represent UV seams or split vertices, not physical holes.",
        "Curvature/crease values depend on triangulation and vertex density.",
        "Normal coherence is not an axis-alignment score; closed surfaces may cancel.",
        "Source units may not be metres, so surface density comparisons need consistent scale."
    )))
    return root.toString(2)
}

fun PartHealth.humanSummary(nameOverride:String?=null):String=buildString {
    append(nameOverride?.takeIf{it.isNotBlank()}?:source.sourceName)
    append("\n").append(triangles).append(" triangles • ").append(vertices).append(" vertices")
    append("\n").append("%.1f%%".format(sharpVertexFraction*100)).append(" sharp-angle vertices")
    append("  •  ").append("%.1f%%".format(highCurvatureFraction*100)).append(" high-bending vertices")
    append("\nDegenerate faces: ").append(degenerateTriangles)
    append("  •  Boundary edges: ").append(boundaryEdges?.toString()?:"not measured (>80k triangles)")
    append("\nNonmanifold edges: ").append(nonmanifoldEdges?.toString()?:"not measured")
    append("\nTriangle density: ").append("%.1f".format(triangleDensity)).append(" / source unit²")
    if(flags.isNotEmpty()) append("\nReview: ").append(flags.joinToString("; "))
    else append("\nNo simple geometry diagnostics flagged. This does not prove production readiness.")
}
