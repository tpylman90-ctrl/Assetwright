package com.assetwright.app.geometry

import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*

/** Inspection only. The source GLB is never rewritten or altered. */
data class GeometryPart(
    val id: Int,
    val sourceName: String,
    val sourcePath: String,
    val firstTriangle: Int,
    val triangleCount: Int,
    val firstVertex: Int,
    val vertexCount: Int,
    val materialIndex: Int = -1
)

class GeometryMesh(
    val name: String,
    val xyz: FloatArray,
    val triangles: IntArray,
    val importedVertexColors: IntArray? = null,
    val parts: List<GeometryPart> = listOf(
        GeometryPart(0, "Unnamed mesh", "no named GLB nodes", 0, triangles.size / 3, 0, xyz.size / 3)
    ),
    val uv0: FloatArray? = null,
    val uv1: FloatArray? = null,
    val surfaceAssets: GltfPreviewAssets = GltfPreviewAssets(emptyList(), emptyList(), emptyList())
) {
    val n get() = xyz.size / 3
    val count get() = triangles.size / 3
    val limits: FloatArray by lazy {
        val b=floatArrayOf(Float.POSITIVE_INFINITY,Float.POSITIVE_INFINITY,Float.POSITIVE_INFINITY,
            Float.NEGATIVE_INFINITY,Float.NEGATIVE_INFINITY,Float.NEGATIVE_INFINITY)
        for(i in xyz.indices step 3) for(d in 0..2) {
            b[d]=min(b[d],xyz[i+d]);b[d+3]=max(b[d+3],xyz[i+d])
        };b
    }
    private fun key(a:Int,b:Int):Long {
        val lo=min(a,b);val hi=max(a,b)
        return (lo.toLong() shl 32) or (hi.toLong() and 0xffffffffL)
    }
    private val normals by lazy {
        FloatArray(count*3).also { out->
            for(t in 0 until count){
                val a=triangles[t*3]*3;val b=triangles[t*3+1]*3;val c=triangles[t*3+2]*3
                val ux=xyz[b]-xyz[a];val uy=xyz[b+1]-xyz[a+1];val uz=xyz[b+2]-xyz[a+2]
                val vx=xyz[c]-xyz[a];val vy=xyz[c+1]-xyz[a+1];val vz=xyz[c+2]-xyz[a+2]
                val x=uy*vz-uz*vy;val y=uz*vx-ux*vz;val z=ux*vy-uy*vx
                val norm=sqrt(x*x+y*y+z*z).coerceAtLeast(0.0000001f)
                out[t*3]=x/norm;out[t*3+1]=y/norm;out[t*3+2]=z/norm
            }
        }
    }
    private val edges by lazy {
        val r=HashMap<Long,IntArray>(count*2)
        for(t in 0 until count) for(k in 0..2) {
            val id=key(triangles[t*3+k],triangles[t*3+(k+1)%3])
            val v=r[id];if(v==null)r[id]=intArrayOf(t,-1) else if(v[1]==-1)v[1]=t
        };r
    }
    val sharpness:FloatArray by lazy {
        val result=FloatArray(n)
        for((k,faces) in edges)if(faces[1]>=0) {
            val a=faces[0]*3;val b=faces[1]*3
            val dot=(normals[a]*normals[b]+normals[a+1]*normals[b+1]+normals[a+2]*normals[b+2])
                .coerceIn(-1f,1f)
            val angle=(acos(dot)*180f/PI.toFloat())
            val i=(k ushr 32).toInt();val j=k.toInt()
            result[i]=max(result[i],angle);result[j]=max(result[j],angle)
        };result
    }
    val curvature:FloatArray by lazy {
        val sum=FloatArray(n*3);val incident=IntArray(n);val ns=FloatArray(n*3)
        for((k,_) in edges) {
            val a=(k ushr 32).toInt();val b=k.toInt()
            incident[a]++;incident[b]++
            for(d in 0..2){val dv=xyz[b*3+d]-xyz[a*3+d];sum[a*3+d]+=dv;sum[b*3+d]-=dv}
        }
        for(t in 0 until count)for(j in 0..2){
            val v=triangles[t*3+j];for(d in 0..2)ns[v*3+d]+=normals[t*3+d]
        }
        val out=FloatArray(n)
        val extent=(0..2).maxOf{limits[it+3]-limits[it]}.coerceAtLeast(0.00001f)
        for(v in 0 until n)if(incident[v]>0) {
            val mag=sqrt((0..2).sumOf{(ns[v*3+it]*ns[v*3+it]).toDouble()}).toFloat().coerceAtLeast(0.00001f)
            var dot=0f;for(d in 0..2)dot+=sum[v*3+d]*ns[v*3+d]/mag
            out[v]=(dot/incident[v]/extent*40f).coerceIn(-1f,1f)
        };out
    }
    val islands:IntArray by lazy {
        val parent=IntArray(n){it}
        fun find(start:Int):Int{var i=start;while(i!=parent[i]){parent[i]=parent[parent[i]];i=parent[i]};return i}
        for(t in 0 until count){val a=find(triangles[t*3]);parent[find(triangles[t*3+1])]=a;parent[find(triangles[t*3+2])]=a}
        val sizes=HashMap<Int,Int>();for(v in 0 until n){val r=find(v);sizes[r]=(sizes[r]?:0)+1}
        val ranks=sizes.entries.sortedByDescending{it.value}.mapIndexed{i,e->e.key to i}.toMap()
        IntArray(n){ranks[find(it)]?:0}
    }
    data class Segment(val a:FloatArray,val b:FloatArray)
    fun slice(axis:Int,frac:Float):List<Segment> {
        val plane=limits[axis]+frac.coerceIn(0f,1f)*(limits[axis+3]-limits[axis])
        val lines=ArrayList<Segment>()
        for(t in 0 until count){
            val p=ArrayList<FloatArray>(2)
            for(j in 0..2){
                val a=triangles[3*t+j]*3;val b=triangles[3*t+(j+1)%3]*3
                val da=xyz[a+axis]-plane;val db=xyz[b+axis]-plane
                if((da<0&&db>0)||(da>0&&db<0)) {
                    val f=da/(da-db);p.add(FloatArray(3){d->xyz[a+d]+f*(xyz[b+d]-xyz[a+d])})
                }
            }
            if(p.size==2)lines.add(Segment(p[0],p[1]))
        };return lines
    }
    fun depth(grid:Int=30):FloatArray {
        // Vertical outer-envelope proxy, not a true cavity ray-cast.
        val low=FloatArray(grid*grid){Float.POSITIVE_INFINITY}
        val high=FloatArray(grid*grid){Float.NEGATIVE_INFINITY}
        val width=(limits[3]-limits[0]).coerceAtLeast(0.00001f)
        val length=(limits[5]-limits[2]).coerceAtLeast(0.00001f)
        for(i in xyz.indices step 3){
            val x=(((xyz[i]-limits[0])/width)*(grid-1)).toInt().coerceIn(0,grid-1)
            val z=(((xyz[i+2]-limits[2])/length)*(grid-1)).toInt().coerceIn(0,grid-1)
            val k=z*grid+x
            low[k]=min(low[k],xyz[i+1]);high[k]=max(high[k],xyz[i+1])
        }
        return FloatArray(grid*grid){if(low[it].isFinite())high[it]-low[it] else Float.NaN}
    }
    fun silhouette(axis:Int,bins:Int=100):List<FloatArray>{
        val horizontal=if(axis==0)2 else 0
        val vertical=if(axis==1)2 else 1
        val lo=FloatArray(bins){Float.POSITIVE_INFINITY};val hi=FloatArray(bins){Float.NEGATIVE_INFINITY}
        val span=(limits[horizontal+3]-limits[horizontal]).coerceAtLeast(0.00001f)
        for(i in xyz.indices step 3) {
            val bin=(((xyz[i+horizontal]-limits[horizontal])/span)*(bins-1)).toInt().coerceIn(0,bins-1)
            lo[bin]=min(lo[bin],xyz[i+vertical]);hi[bin]=max(hi[bin],xyz[i+vertical])
        }
        val result=ArrayList<FloatArray>()
        for(i in 0 until bins)if(lo[i].isFinite()){
            result.add(floatArrayOf(limits[horizontal]+i*span/(bins-1),lo[i]))
            result.add(floatArrayOf(limits[horizontal]+i*span/(bins-1),hi[i]))
        };return result
    }
    fun compare(other:GeometryMesh,maxPoints:Int=450):FloatArray {
        // Approximate normalized two-sided nearest-VERTEX distance, not surface distance.
        fun samples(g:GeometryMesh):FloatArray {
            val out=FloatArray(min(g.n,maxPoints)*3)
            for(i in 0 until out.size/3)for(d in 0..2) {
                val sample=(i.toLong()*g.n/(out.size/3)).toInt()
                out[3*i+d]=(g.xyz[3*sample+d]-g.limits[d])/
                    (g.limits[d+3]-g.limits[d]).coerceAtLeast(0.00001f)
            };return out
        }
        val a=samples(this);val b=samples(other)
        fun dist(v:FloatArray,w:FloatArray):Float {
            var total=0.0
            for(i in v.indices step 3){
                var best=Float.POSITIVE_INFINITY
                for(j in w.indices step 3){
                    val x=v[i]-w[j];val y=v[i+1]-w[j+1];val z=v[i+2]-w[j+2]
                    best=min(best,x*x+y*y+z*z)
                };total+=sqrt(best)
            };return (total/(v.size/3)).toFloat()
        }
        return floatArrayOf(dist(a,b),dist(b,a))
    }
    fun csv(mode:Int,axis:Int,fraction:Float):String=buildString {
        when(mode){
            0,5 -> {
                append("axis,fraction,ax,ay,az,bx,by,bz\n")
                for(l in slice(axis,fraction)) {
                    append(axis).append(',').append(fraction)
                    for(x in l.a+l.b)append(',').append(x)
                    append('\n')
                }
            }
            else -> {
                append("vertex,x,y,z,curvature,crease_angle,island\n")
                for(i in 0 until n){
                    append(i)
                    for(d in 0..2)append(',').append(xyz[i*3+d])
                    append(',').append(curvature[i]).append(',').append(sharpness[i])
                        .append(',').append(islands[i]).append('\n')
                }
            }
        }
    }
    fun report(other:GeometryMesh?=null):String=buildString {
        val b=limits
        append("ASSETWRIGHT GEOMETRY LAB - ORIGINAL MODEL PRESERVED\n")
        append("Source: ").append(name).append('\n')
        append("Vertices: ").append(n).append("\nTriangles: ").append(count)
        append("\nDimensions (source units): ")
        for(d in 0..2)append("%.4f ".format(b[d+3]-b[d]))
        append("\nBoundary edges: ").append(edges.values.count{it[1]<0})
        append("\nCandidate creases >=35 degrees: ").append(edges.values.count{f->
            if(f[1]<0)false else {
                val a=f[0]*3;val c=f[1]*3
                val dot=(0..2).sumOf{normals[a+it].toDouble()*normals[c+it]}
                dot<cos(35.0*PI/180.0)
            }
        })
        append("\nConnected islands: ").append((islands.maxOrNull()?:-1)+1)
        append("\nConvex/concave bending indicators: ").append(curvature.count{it>0.08f})
            .append('/').append(curvature.count{it< -0.08f})
        append("\nSlices: real triangle-plane intersections")
        append("\nSurface reconstruction: contour-envelope guide only; not production quad topology")
        append("\nRecess inspector: vertical depth-envelope proxy, not cavity raycasting")
        append("\nFeature detector: candidate ridges, valleys and islands; not semantic labels")
        if(other!=null) {
            val diff=compare(other)
            append("\nNormalized sampled-vertex difference A->B / B->A: ")
                .append("%.4f / %.4f".format(diff[0],diff[1]))
        } else append("\nShape comparison: load a second reference GLB")
        append("\nNo input meshes were edited.")
    }
    companion object {
        private data class AccessorView(val meta: JSONObject, val bytes: ByteBuffer, val stride: Int)

        fun parse(bytes: ByteArray, name: String): GeometryMesh {
            require(bytes.size >= 20) { "GLB is too small" }
            val bb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            require(bb.int == 0x46546c67 && bb.int == 2) { "Binary glTF 2.0 (.glb) required" }
            val size = bb.int
            require(size in 20..bytes.size) { "Invalid GLB header length" }
            var json: JSONObject? = null
            var base = -1
            var binarySize = 0
            while (bb.position() + 8 <= size) {
                val len = bb.int
                val type = bb.int
                require(len >= 0 && bb.position() + len <= size) { "Invalid GLB chunk length" }
                val pos = bb.position()
                if (type == 0x4e4f534a) {
                    json = JSONObject(String(bytes, pos, len, Charsets.UTF_8).trimEnd('\u0000', ' '))
                }
                if (type == 0x004e4942) {
                    base = pos
                    binarySize = len
                }
                bb.position(pos + len)
            }
            val root = json ?: error("Missing GLB JSON")
            require(base >= 0) { "Missing embedded GLB binary chunk" }
            val surfaceAssets = GltfMaterialReader.read(root, bytes, base, binarySize)
            val required = root.optJSONArray("extensionsRequired")
            if (required != null) for (i in 0 until required.length()) {
                require(required.getString(i) != "KHR_draco_mesh_compression") {
                    "Draco compression is not yet supported. Meshopt models are supported."
                }
            }

            val views = root.getJSONArray("bufferViews")
            val access = root.getJSONArray("accessors")
            val meshes = root.getJSONArray("meshes")
            val decompressed = HashMap<Int, ByteBuffer>()

            fun viewData(id: Int): Pair<ByteBuffer, Int> {
                val view = views.getJSONObject(id)
                val ext = view.optJSONObject("extensions")?.optJSONObject("EXT_meshopt_compression")
                if (ext != null) {
                    val stride = ext.getInt("byteStride")
                    val count = ext.getInt("count")
                    require(count > 0 && stride > 0 && count.toLong() * stride <= 128L * 1024 * 1024) {
                        "Meshopt buffer is too large for mobile analysis"
                    }
                    val cached = decompressed[id]
                    if (cached != null) return cached.duplicate().order(ByteOrder.LITTLE_ENDIAN) to stride
                    require(ext.optInt("buffer", 0) == 0) { "External compressed buffers are unsupported" }
                    val off = ext.optInt("byteOffset", 0)
                    val len = ext.getInt("byteLength")
                    require(off >= 0 && len > 0 && off.toLong() + len <= binarySize) {
                        "Compressed GLB buffer extends beyond file"
                    }
                    val packed = bytes.copyOfRange(base + off, base + off + len)
                    val decoded = MeshoptBridge.decode(
                        packed, count, stride,
                        ext.getString("mode"), ext.optString("filter", "NONE")
                    )
                    require(decoded.size == count * stride) { "Meshopt decoder returned wrong buffer size" }
                    val result = ByteBuffer.wrap(decoded).order(ByteOrder.LITTLE_ENDIAN)
                    decompressed[id] = result
                    return result.duplicate().order(ByteOrder.LITTLE_ENDIAN) to stride
                }
                require(view.optInt("buffer", 0) == 0) { "External geometry buffers are unsupported" }
                val off = view.optInt("byteOffset", 0)
                val len = view.getInt("byteLength")
                require(off >= 0 && len > 0 && off.toLong() + len <= binarySize) {
                    "Geometry buffer extends beyond file"
                }
                val result = ByteBuffer.wrap(bytes, base + off, len).slice().order(ByteOrder.LITTLE_ENDIAN)
                return result to view.optInt("byteStride", 0)
            }

            fun accessor(id: Int): AccessorView {
                val a = access.getJSONObject(id)
                require(a.has("bufferView") && !a.has("sparse")) {
                    "Sparse accessors are not yet supported in Geometry Lab"
                }
                val (data, stride) = viewData(a.getInt("bufferView"))
                val offset = a.optInt("byteOffset", 0)
                require(offset >= 0 && offset <= data.limit()) { "Invalid accessor byte offset" }
                data.position(offset)
                return AccessorView(a, data.slice().order(ByteOrder.LITTLE_ENDIAN), stride)
            }
            fun identity(): FloatArray = FloatArray(16) { if (it % 5 == 0) 1f else 0f }
            fun multiply(a: FloatArray, b: FloatArray): FloatArray {
                val result = FloatArray(16)
                for (col in 0..3) for (row in 0..3) for (k in 0..3) {
                    result[col * 4 + row] += a[k * 4 + row] * b[col * 4 + k]
                }
                return result
            }
            fun local(node: JSONObject): FloatArray {
                if (node.has("matrix")) {
                    val matrix = node.getJSONArray("matrix")
                    return FloatArray(16) { matrix.getDouble(it).toFloat() }
                }
                val t = node.optJSONArray("translation")
                val scl = node.optJSONArray("scale")
                val rot = node.optJSONArray("rotation")
                val x = rot?.optDouble(0, 0.0)?.toFloat() ?: 0f
                val y = rot?.optDouble(1, 0.0)?.toFloat() ?: 0f
                val z = rot?.optDouble(2, 0.0)?.toFloat() ?: 0f
                val w = rot?.optDouble(3, 1.0)?.toFloat() ?: 1f
                val m = identity()
                m[0] = 1f - 2f * (y * y + z * z)
                m[1] = 2f * (x * y + z * w)
                m[2] = 2f * (x * z - y * w)
                m[4] = 2f * (x * y - z * w)
                m[5] = 1f - 2f * (x * x + z * z)
                m[6] = 2f * (y * z + x * w)
                m[8] = 2f * (x * z + y * w)
                m[9] = 2f * (y * z - x * w)
                m[10] = 1f - 2f * (x * x + y * y)
                for (col in 0..2) {
                    val scale = scl?.optDouble(col, 1.0)?.toFloat() ?: 1f
                    for (row in 0..2) m[col * 4 + row] *= scale
                }
                for (col in 0..2) m[12 + col] = t?.optDouble(col, 0.0)?.toFloat() ?: 0f
                return m
            }

            val verts = ArrayList<Float>()
            val faces = ArrayList<Int>()
            val vertexColors = ArrayList<Int>()
            var hasAnyColors = false
            val uv0 = ArrayList<Float>()
            val uv1 = ArrayList<Float>()
            var hasAnyUv0 = false
            var hasAnyUv1 = false
            val parts = ArrayList<GeometryPart>()
            fun add(meshId: Int, transform: FloatArray, nodePath: String) {
                val meshName = meshes.getJSONObject(meshId).optString("name", "Mesh $meshId")
                val mesh = meshes.getJSONObject(meshId)
                val primitives = mesh.getJSONArray("primitives")
                for (p in 0 until primitives.length()) {
                    val primitive = primitives.getJSONObject(p)
                    val firstTriangle = faces.size / 3
                    if (primitive.optInt("mode", 4) != 4) continue
                    if (primitive.optJSONObject("extensions")?.has("KHR_draco_mesh_compression") == true) {
                        error("KHR_draco_mesh_compression is unsupported")
                    }
                    val attributes = primitive.getJSONObject("attributes")
                    if (!attributes.has("POSITION")) continue
                    val pos = accessor(attributes.getInt("POSITION"))
                    val pa = pos.meta
                    require(pa.getInt("componentType") == 5126 && pa.getString("type") == "VEC3") {
                        "Only FLOAT VEC3 geometry positions supported"
                    }
                    val count = pa.getInt("count")
                    require(count in 1..650_000) { "Mesh exceeds native 650k vertex limit" }
                    val start = verts.size / 3
                    require(start + count <= 650_000) { "Combined model exceeds 650k vertices" }
                    val stride = if (pos.stride > 0) pos.stride else 12
                    require(stride >= 12) { "Invalid position vertex stride" }
                    val vertexBuffer = pos.bytes
                    for (i in 0 until count) {
                        val at = i * stride
                        require(at >= 0 && at + 12 <= vertexBuffer.limit()) { "Position outside GLB buffer" }
                        val x = vertexBuffer.getFloat(at)
                        val y = vertexBuffer.getFloat(at + 4)
                        val z = vertexBuffer.getFloat(at + 8)
                        verts.add(transform[0] * x + transform[4] * y + transform[8] * z + transform[12])
                        verts.add(transform[1] * x + transform[5] * y + transform[9] * z + transform[13])
                        verts.add(transform[2] * x + transform[6] * y + transform[10] * z + transform[14])
                    }
                    // glTF UVs are linear floats or normalized integer vectors,
                    // with independent strides, including Meshopt-compressed views.
                    fun appendUv(semantic: String, target: ArrayList<Float>): Boolean {
                        if (!attributes.has(semantic)) {
                            repeat(count * 2) { target.add(0f) }
                            return false
                        }
                        val view = accessor(attributes.getInt(semantic))
                        val desc = view.meta
                        require(desc.getString("type") == "VEC2" && desc.getInt("count") == count) {
                            "$semantic must be a VEC2 for every vertex"
                        }
                        val componentType = desc.getInt("componentType")
                        val bytesPerValue = when(componentType) {
                            5126 -> 4
                            5123 -> 2
                            5121 -> 1
                            else -> error("Unsupported $semantic componentType $componentType")
                        }
                        val step = if(view.stride>0) view.stride else bytesPerValue*2
                        require(step >= bytesPerValue*2) { "Invalid UV accessor stride" }
                        val data = view.bytes
                        val normalized = desc.optBoolean("normalized",false)
                        fun component(offset:Int):Float = when(componentType) {
                            5126 -> data.getFloat(offset)
                            5123 -> (data.getShort(offset).toInt() and 0xffff).toFloat()/
                                (if(normalized)65535f else 1f)
                            else -> (data.get(offset).toInt() and 255).toFloat()/
                                (if(normalized)255f else 1f)
                        }
                        for (i in 0 until count) {
                            val at = i * step
                            require(at>=0 && at + bytesPerValue*2<=data.limit()) {
                                "$semantic outside buffer"
                            }
                            target.add(component(at))
                            target.add(component(at+bytesPerValue))
                        }
                        return true
                    }
                    if (appendUv("TEXCOORD_0",uv0)) hasAnyUv0=true
                    if (appendUv("TEXCOORD_1",uv1)) hasAnyUv1=true
                    // Import glTF COLOR_0 so derived patch GLBs retain their
                    // diagnostic color labels in the native Android inspector.
                    // Supports normalized unsigned bytes and float RGB(A).
                    if (attributes.has("COLOR_0")) {
                        val colorAccessor = accessor(attributes.getInt("COLOR_0"))
                        val colorMeta = colorAccessor.meta
                        val kind = colorMeta.getInt("componentType")
                        val components = when (colorMeta.getString("type")) {
                            "VEC3" -> 3
                            "VEC4" -> 4
                            else -> error("Unsupported vertex color type")
                        }
                        require(colorMeta.getInt("count") == count) {
                            "Vertex color and position counts do not match"
                        }
                        require(kind == 5121 || kind == 5126) {
                            "Only byte or float vertex colors supported"
                        }
                        val bytesPerComponent = if (kind == 5121) 1 else 4
                        val naturalStride = components * bytesPerComponent
                        val colorStride = if (colorAccessor.stride > 0) colorAccessor.stride else naturalStride
                        val colorBuffer = colorAccessor.bytes
                        require(colorStride >= naturalStride) { "Invalid vertex color stride" }
                        for (i in 0 until count) {
                            val offset = i * colorStride
                            require(offset >= 0 && offset + naturalStride <= colorBuffer.limit()) {
                                "Vertex colors outside GLB binary"
                            }
                            fun channel(c: Int): Int {
                                val value = if (kind == 5121) {
                                    colorBuffer.get(offset + c).toInt() and 255
                                } else {
                                    (colorBuffer.getFloat(offset + c * 4).coerceIn(0f, 1f) * 255f).toInt()
                                }
                                return value.coerceIn(0, 255)
                            }
                            val r = channel(0)
                            val g = channel(1)
                            val b = channel(2)
                            vertexColors.add((255 shl 24) or (r shl 16) or (g shl 8) or b)
                        }
                        hasAnyColors = true
                    } else {
                        repeat(count) { vertexColors.add(0xff8eaebc.toInt()) }
                    }
                    if (primitive.has("indices")) {
                        val indices = accessor(primitive.getInt("indices"))
                        val ia = indices.meta
                        require(ia.getString("type") == "SCALAR") { "Invalid index accessor" }
                        val unit = when (ia.getInt("componentType")) {
                            5121 -> 1
                            5123 -> 2
                            5125 -> 4
                            else -> error("Unsupported triangle index format")
                        }
                        val indexStride = if (indices.stride > 0) indices.stride else unit
                        require(indexStride >= unit) { "Invalid triangle index stride" }
                        val n = ia.getInt("count")
                        require(n % 3 == 0 && n <= 3_000_000) { "Invalid triangle indices" }
                        val indexBuffer = indices.bytes
                        for (i in 0 until n) {
                            val at = i * indexStride
                            require(at >= 0 && at + unit <= indexBuffer.limit()) { "Index outside GLB buffer" }
                            val ix = when (unit) {
                                1 -> indexBuffer.get(at).toInt() and 255
                                2 -> indexBuffer.getShort(at).toInt() and 65535
                                else -> indexBuffer.getInt(at)
                            }
                            require(ix in 0 until count) { "Triangle references missing vertex" }
                            faces.add(start + ix)
                        }
                    } else {
                        require(count % 3 == 0) { "Unindexed triangles have invalid vertex count" }
                        for (i in 0 until count) faces.add(start + i)
                    }
                    val trianglesAdded = faces.size / 3 - firstTriangle
                    if (trianglesAdded > 0) {
                        val primitiveLabel = primitive.optString("name", "").takeIf { it.isNotBlank() }
                            ?: if (primitives.length() > 1) "Primitive $p" else ""
                        val displayName = listOf(nodePath, meshName, primitiveLabel)
                            .filter { it.isNotBlank() }
                            .distinct()
                            .joinToString(" / ")
                        parts.add(GeometryPart(
                            parts.size, displayName, "$nodePath / $meshName / primitive[$p]",
                            firstTriangle, trianglesAdded, start, count,
                            primitive.optInt("material",-1)
                        ))
                    }
                }
            }

            val nodes = root.optJSONArray("nodes")
            val scenes = root.optJSONArray("scenes")
            var visited = 0
            if (nodes != null && nodes.length() > 0) {
                fun walk(nodeId: Int, parent: FloatArray, depth: Int, parentPath: String) {
                    require(depth < 64) { "Scene node hierarchy too deep" }
                    val node = nodes.getJSONObject(nodeId)
                    val nodeName = node.optString("name", "Node $nodeId")
                    val path = if (parentPath.isEmpty()) nodeName else "$parentPath / $nodeName"
                    val transform = multiply(parent, local(node))
                    if (node.has("mesh")) {
                        add(node.getInt("mesh"), transform, path)
                        visited++
                    }
                    val children = node.optJSONArray("children")
                    if (children != null) for (j in 0 until children.length()) {
                        walk(children.getInt(j), transform, depth + 1, path)
                    }
                }
                if (scenes != null && scenes.length() > 0) {
                    val scene = scenes.getJSONObject(root.optInt("scene", 0))
                    val roots = scene.optJSONArray("nodes")
                    if (roots != null) for (i in 0 until roots.length()) {
                        walk(roots.getInt(i), identity(), 0, "")
                    }
                } else {
                    val childIds = HashSet<Int>()
                    for (i in 0 until nodes.length()) {
                        val children = nodes.getJSONObject(i).optJSONArray("children")
                        if (children != null) for (j in 0 until children.length()) childIds.add(children.getInt(j))
                    }
                    for (i in 0 until nodes.length()) if (i !in childIds) walk(i, identity(), 0, "")
                }
            }
            if (visited == 0) for (i in 0 until meshes.length()) add(i, identity(), "Mesh $i")
            require(verts.size >= 9 && faces.size >= 3) { "No triangle mesh found in GLB" }
            return GeometryMesh(
                name, verts.toFloatArray(), faces.toIntArray(),
                if (hasAnyColors) vertexColors.toIntArray() else null, parts,
                if (hasAnyUv0) uv0.toFloatArray() else null,
                if (hasAnyUv1) uv1.toFloatArray() else null,
                surfaceAssets
            )
        }
    }
}
