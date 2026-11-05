package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/** Rebuild two actual predicted variants, NEVER using the source operator label. */
class DinoDeltaReconstructionTest {
    private fun digest(bytes:ByteArray)=MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }

    @Test
    fun rebuildRealBeforeAfterStudentNativeMeshes() {
        val input=System.getenv("ASSETWRIGHT_DINO_DELTA_PREDICTIONS")
            ?.takeIf { it.isNotBlank() } ?: return
        val folder=System.getenv("ASSETWRIGHT_DINO_DELTA_RECON")
            ?.takeIf { it.isNotBlank() } ?: return
        val properties=Properties()
        Files.newBufferedReader(Path.of(input)).use { properties.load(it) }
        require(properties.getProperty("schema")=="assetwright-native-before-after-proposals-v1")
        require(properties.getProperty("external_mesh_used")=="false")
        require(properties.getProperty("count")=="54")
        val variants=listOf("teacher_free","DINO_guided")
        val fields=listOf("case","source_glb_sha256","baseline_glb_sha256",
            "predicted_operation","predicted_strength","length","width","height")
        val required=mutableSetOf("schema","external_mesh_used","count")
        for (variant in variants) for (index in 0 until 54) for (field in fields)
            required.add(variant+"."+index+"."+field)
        require(properties.stringPropertyNames()==required) {
            "Unrecognized native prediction fields or missing sample"
        }
        val root=Path.of(folder)
        Files.createDirectories(root)
        val seen=mutableSetOf<String>()
        for (index in 0 until 54) {
            fun field(variant:String,key:String)=properties.getProperty(
                variant+"."+index+"."+key)
            val stem=field("teacher_free","case")
            require(Regex("validation__bdhold0[1-3]__[a-z_]+__s[0-9]{3}").matches(stem))
            require(seen.add(stem)) { "Duplicate original validation case" }
            val sourceHash=field("teacher_free","source_glb_sha256")
            val beforeHash=field("teacher_free","baseline_glb_sha256")
            require(Regex("[0-9a-f]{64}").matches(sourceHash))
            require(Regex("[0-9a-f]{64}").matches(beforeHash))
            val dims=listOf("length","width","height").map {
                field("teacher_free",it).toFloat()
            }
            require(dims[0].isFinite() && dims[0] in 1f..12f)
            require(dims[1].isFinite() && dims[1] in .5f..7f)
            require(dims[2].isFinite() && dims[2] in .5f..7f)
            for (variant in variants) {
                for (f in listOf("case","source_glb_sha256","baseline_glb_sha256",
                                  "length","width","height")) {
                    require(field(variant,f)==field("teacher_free",f)) {
                        "Student variants do not use identical original target geometry"
                    }
                }
                val op=AdvancedFormOperation.valueOf(field(variant,"predicted_operation"))
                val strength=field(variant,"predicted_strength").toFloat()
                require(strength.isFinite() && strength in 0f..1f)
                val mesh=AdvancedFormLab.generate(
                    AdvancedFormSpec(op,dims[0],dims[1],dims[2],strength))
                val carrier=VehicleSpec("Own before-after lesson",4f,2f,1.4f,
                    1.7f,.5f,1f,"Mobile","Research-only native reconstruction")
                val bytes=GlbWriter.encode(GeneratedAsset(carrier,listOf(mesh)))
                assertTrue(bytes.size>2000 && mesh.indices.size/3 in 900..3000)
                val actualHash=digest(bytes)
                val fileStem=stem+"__"+variant
                Files.write(root.resolve(fileStem+".glb"),bytes)
                val record="{\"schema\":\"assetwright-native-before-after-reconstruction-v1\","+
                    "\"case\":\""+stem+"\","+
                    "\"variant\":\""+variant+"\","+
                    "\"source_engine\":\"AssetWright-AdvancedFormLab\","+
                    "\"reference_glb_sha256\":\""+sourceHash+"\","+
                    "\"baseline_glb_sha256\":\""+beforeHash+"\","+
                    "\"chosen_operation\":\""+op.name+"\","+
                    "\"chosen_strength\":"+strength+","+
                    "\"generated_glb_sha256\":\""+actualHash+"\"}"
                Files.write(root.resolve(fileStem+".json"),
                    record.toByteArray(Charsets.UTF_8))
            }
        }
        assertEquals(54,seen.size)
        assertEquals(108,Files.list(root).use { stream ->
            stream.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
