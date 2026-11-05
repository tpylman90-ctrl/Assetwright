package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/** 
 * Execute 192 OWN student proposals on 96 never-used-before native targets.
 * Original source op/strength NEVER become reconstruction inputs.
 */
class DinoStrengthReconstructionTest {
    private fun sha(bytes:ByteArray)=MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }

    @Test
    fun rebuildBothIndependentMultiSessionResearchWinners() {
        val input=System.getenv("ASSETWRIGHT_DINO_STRENGTH_PREDICTIONS")
            ?.takeIf { it.isNotBlank() } ?: return
        val folder=System.getenv("ASSETWRIGHT_DINO_STRENGTH_RECON")
            ?.takeIf { it.isNotBlank() } ?: return
        val props=Properties()
        Files.newBufferedReader(Path.of(input)).use { props.load(it) }
        require(props.getProperty("schema")=="assetwright-multisession-native-strength-proposals-v2")
        require(props.getProperty("external_mesh_used")=="false")
        require(props.getProperty("count")=="96")
        val variants=listOf("teacher_free","DINO_guided")
        val fields=listOf("case","source_glb_sha256","baseline_glb_sha256",
            "predicted_operation","predicted_strength","length","width","height")
        val required=mutableSetOf("schema","external_mesh_used","count")
        for (variant in variants) for (i in 0 until 96) for (key in fields)
            required.add(variant+"."+i+"."+key)
        require(props.stringPropertyNames()==required) {
            "Unexpected field or missing original native calibration source case"
        }
        val root=Path.of(folder)
        Files.createDirectories(root)
        val cases=mutableSetOf<String>()
        var generated=0
        for (index in 0 until 96) {
            fun field(variant:String,key:String)=props.getProperty(
                variant+"."+index+"."+key)
            val stem=field("teacher_free","case")
            require(Regex("validation__bs_blind0[1-4]__[a-z_]+__s[0-9]{3}").matches(stem))
            require(cases.add(stem)) { "Duplicate native strength test target" }
            for (key in listOf("source_glb_sha256","baseline_glb_sha256")) {
                require(Regex("[0-9a-f]{64}").matches(field("teacher_free",key)))
            }
            val dims=listOf("length","width","height").map{
                field("teacher_free",it).toFloat()
            }
            require(dims[0].isFinite() && dims[0] in 1f..12f)
            require(dims[1].isFinite() && dims[1] in .5f..7f)
            require(dims[2].isFinite() && dims[2] in .5f..7f)
            for (variant in variants) {
                for (key in listOf("case","source_glb_sha256","baseline_glb_sha256",
                             "length","width","height")) {
                    require(field(variant,key)==field("teacher_free",key)) {
                        "Control and teacher model comparison uses unequal original GLBs"
                    }
                }
                val op=AdvancedFormOperation.valueOf(field(variant,"predicted_operation"))
                val strength=field(variant,"predicted_strength").toFloat()
                require(strength.isFinite() && strength in 0f..1f)
                val shell=AdvancedFormLab.generate(AdvancedFormSpec(
                    op,dims[0],dims[1],dims[2],strength))
                val spec=VehicleSpec("Original strength research",4f,2f,1.4f,
                    1.7f,.5f,1f,"Mobile","AssetWright own Kotlin construction")
                val bytes=GlbWriter.encode(GeneratedAsset(spec,listOf(shell)))
                assertTrue("Reconstruction must be original indexed mesh",bytes.size>2000 &&
                    shell.indices.size/3 in 900..3000)
                val stemOut=stem+"__"+variant
                Files.write(root.resolve(stemOut+".glb"),bytes)
                val record="{\"schema\":\"assetwright-native-before-after-reconstruction-v1\","+
                    "\"case\":\""+stem+"\","+
                    "\"variant\":\""+variant+"\","+
                    "\"source_engine\":\"AssetWright-AdvancedFormLab\","+
                    "\"reference_glb_sha256\":\""+field(variant,"source_glb_sha256")+"\","+
                    "\"baseline_glb_sha256\":\""+field(variant,"baseline_glb_sha256")+"\","+
                    "\"chosen_operation\":\""+op.name+"\","+
                    "\"chosen_strength\":"+strength+","+
                    "\"generated_glb_sha256\":\""+sha(bytes)+"\"}"
                Files.write(root.resolve(stemOut+".json"),record.toByteArray(Charsets.UTF_8))
                generated++
            }
        }
        assertEquals(96,cases.size)
        assertEquals(192,generated)
        assertEquals(192,Files.list(root).use { stream ->
            stream.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
