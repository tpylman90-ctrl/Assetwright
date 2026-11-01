package com.assetwright.app.mini

import java.io.ByteArrayOutputStream
import kotlin.math.sqrt

/** Dependency-free binary glTF 2.0 exporter for locally generated meshes. */
object GlbWriter {
    private fun ByteArrayOutputStream.leInt(value: Int) {
        write(value and 255)
        write((value ushr 8) and 255)
        write((value ushr 16) and 255)
        write((value ushr 24) and 255)
    }
    private fun ByteArrayOutputStream.leFloat(value: Float) =
        leInt(java.lang.Float.floatToIntBits(value))
    private fun ByteArrayOutputStream.pad4(fill: Int = 0) {
        while (size() % 4 != 0) write(fill)
    }
    private fun Vec3.normalized(): Vec3 {
        val n = sqrt(x * x + y * y + z * z)
        return if (n < 1.0e-7f) Vec3(0f, 0f, 1f)
        else Vec3(x / n, y / n, z / n)
    }
    private fun normals(part: MeshPart): List<Vec3> {
        val sums = Array(part.vertices.size) { Vec3(0f, 0f, 0f) }
        for (i in part.indices.indices step 3) {
            val a = part.indices[i]
            val b = part.indices[i + 1]
            val c = part.indices[i + 2]
            val n = (part.vertices[b] - part.vertices[a])
                .cross(part.vertices[c] - part.vertices[a])
            sums[a] = sums[a] + n
            sums[b] = sums[b] + n
            sums[c] = sums[c] + n
        }
        return sums.map { it.normalized() }
    }
    private fun esc(input: String): String =
        input.replace("\\", "\\\\").replace("\"", "\\\"")

    fun encode(asset: GeneratedAsset): ByteArray {
        require(asset.parts.isNotEmpty()) { "Nothing to export." }
        val binary = ByteArrayOutputStream()
        val views = mutableListOf<String>()
        val accessors = mutableListOf<String>()
        val meshes = mutableListOf<String>()
        val nodes = mutableListOf<String>()
        val materials = mutableListOf<String>()
        fun addView(start: Int, bytes: Int, target: Int): Int {
            val index = views.size
            views += """{"buffer":0,"byteOffset":$start,"byteLength":$bytes,"target":$target}"""
            return index
        }
        for ((index, part) in asset.parts.withIndex()) {
            require(part.indices.size % 3 == 0 && part.vertices.isNotEmpty())
            val posStart = binary.size()
            var minX = Float.POSITIVE_INFINITY
            var minY = Float.POSITIVE_INFINITY
            var minZ = Float.POSITIVE_INFINITY
            var maxX = Float.NEGATIVE_INFINITY
            var maxY = Float.NEGATIVE_INFINITY
            var maxZ = Float.NEGATIVE_INFINITY
            // Procedural source is Z-up. glTF is Y-up: (x, y, z) -> (x, z, -y).
            // This is a proper rotation (not a reflection), so winding is preserved.
            for (original in part.vertices) {
                val v = Vec3(original.x, original.z, -original.y)
                require(v.x.isFinite() && v.y.isFinite() && v.z.isFinite())
                binary.leFloat(v.x)
                binary.leFloat(v.y)
                binary.leFloat(v.z)
                minX = minOf(minX, v.x)
                minY = minOf(minY, v.y)
                minZ = minOf(minZ, v.z)
                maxX = maxOf(maxX, v.x)
                maxY = maxOf(maxY, v.y)
                maxZ = maxOf(maxZ, v.z)
            }
            val posView = addView(posStart, binary.size() - posStart, 34962)
            val posAccessor = accessors.size
            accessors += """{"bufferView":$posView,"componentType":5126,"count":${part.vertices.size},"type":"VEC3","min":[$minX,$minY,$minZ],"max":[$maxX,$maxY,$maxZ]}"""
            val normalsStart = binary.size()
            for (n in normals(part)) {
                binary.leFloat(n.x)
                binary.leFloat(n.z)
                binary.leFloat(-n.y)
            }
            val normalView = addView(normalsStart, binary.size() - normalsStart, 34962)
            val normalAccessor = accessors.size
            accessors += """{"bufferView":$normalView,"componentType":5126,"count":${part.vertices.size},"type":"VEC3"}"""
            val indexStart = binary.size()
            for (vertexIndex in part.indices) {
                require(vertexIndex in part.vertices.indices)
                binary.leInt(vertexIndex)
            }
            val indexView = addView(indexStart, binary.size() - indexStart, 34963)
            val indexAccessor = accessors.size
            accessors += """{"bufferView":$indexView,"componentType":5125,"count":${part.indices.size},"type":"SCALAR"}"""
            val r = ((part.color shr 16) and 255) / 255f
            val g = ((part.color shr 8) and 255) / 255f
            val b = (part.color and 255) / 255f
            val glow = if (part.name.contains("light", true) ||
                part.name.contains("energy", true) ||
                part.name.contains("field", true))
                ""","emissiveFactor":[${r * .6f},${g * .6f},${b * .6f}]""" else ""
            materials += """{"name":"${esc(part.name)}","pbrMetallicRoughness":{"baseColorFactor":[$r,$g,$b,1],"metallicFactor":0.28,"roughnessFactor":0.48},"doubleSided":true$glow}"""
            meshes += """{"name":"${esc(part.name)}","primitives":[{"attributes":{"POSITION":$posAccessor,"NORMAL":$normalAccessor},"indices":$indexAccessor,"material":$index,"mode":4}]}"""
            nodes += """{"mesh":$index,"name":"${esc(part.name)}"}"""
        }
        binary.pad4()
        val json = """{"asset":{"version":"2.0","generator":"Assetwright Mini AI v0.1"},"scene":0,"scenes":[{"nodes":[${asset.parts.indices.joinToString(",")}]}],"nodes":[${nodes.joinToString(",")}],"meshes":[${meshes.joinToString(",")}],"materials":[${materials.joinToString(",")}],"buffers":[{"byteLength":${binary.size()}}],"bufferViews":[${views.joinToString(",")}],"accessors":[${accessors.joinToString(",")}]}"""
        val jsonChunk = ByteArrayOutputStream()
        jsonChunk.write(json.toByteArray(Charsets.UTF_8))
        jsonChunk.pad4(32)
        val totalBytes = 12 + 8 + jsonChunk.size() + 8 + binary.size()
        val out = ByteArrayOutputStream(totalBytes)
        out.leInt(0x46546C67)
        out.leInt(2)
        out.leInt(totalBytes)
        out.leInt(jsonChunk.size())
        out.leInt(0x4E4F534A)
        out.write(jsonChunk.toByteArray())
        out.leInt(binary.size())
        out.leInt(0x004E4942)
        out.write(binary.toByteArray())
        return out.toByteArray()
    }
}
