package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/**
 * Execute the learned image-to-native-operator proposal without substituting
 * ground truth operation or strength. Also export constant-prior comparison.
 * All meshes are built by ORIGINAL AdvancedFormLab and GlbWriter in Kotlin.
 */
class DinoVisualReconstructionTest {
    private fun digest(bytes:ByteArray):String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {
            "%02x".format(it.toInt() and 255)
        }

    @Test
    fun executeAllFrozenVisualStudentProposalsAsNativeGlbs() {
        val source = System.getenv("ASSETWRIGHT_DINO_RECON_PROPERTIES")
            ?.takeIf { it.isNotBlank() } ?: return
        val destination = System.getenv("ASSETWRIGHT_DINO_RECON_OUTPUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val props=Properties()
        Files.newBufferedReader(Path.of(source)).use { props.load(it) }
        require(props.getProperty("schema")=="assetwright-native-visual-proposals-v1")
        require(props.getProperty("external_mesh_used")=="false")
        require(props.getProperty("count")=="36")
        val fields=listOf("case","source_glb_sha256","predicted_operation",
            "predicted_strength","length","width","height")
        val expected=mutableSetOf("schema","external_mesh_used","count")
        for(i in 0 until 36) for(field in fields)
            expected.add("proposal"+i+"."+field)
        require(props.stringPropertyNames()==expected) {
            "Missing or unexpected learned native construction proposal fields"
        }
        val root=Path.of(destination)
        Files.createDirectories(root)
        val observed=mutableSetOf<String>()
        var exports=0
        for(i in 0 until 36) {
            fun field(key:String)=props.getProperty("proposal"+i+"."+key)
            val case=field("case")
            require(Regex("validation__dnblind0[12]__[a-z_]+__s[0-9]{3}").matches(case))
            require(observed.add(case)) { "Repeated learned geometry source" }
            val sourceSha=field("source_glb_sha256")
            require(Regex("[0-9a-f]{64}").matches(sourceSha))
            val operation=AdvancedFormOperation.valueOf(field("predicted_operation"))
            val strength=field("predicted_strength").toFloat()
            val length=field("length").toFloat()
            val width=field("width").toFloat()
            val height=field("height").toFloat()
            require(strength.isFinite() && strength in 0f..1f)
            require(length.isFinite() && length in 1f..12f)
            require(width.isFinite() && width in .5f..7f)
            require(height.isFinite() && height in .5f..7f)

            for ((variant,actualOperation,actualStrength) in listOf(
                Triple("student",operation,strength),
                Triple("constant",AdvancedFormOperation.SECTION_LOFT,.5f)
            )) {
                val mesh=AdvancedFormLab.generate(AdvancedFormSpec(
                    actualOperation,length,width,height,actualStrength))
                val carrier=VehicleSpec(
                    "Original DINO visual reconstruction",4f,2f,1.4f,
                    1.7f,.5f,1f,"Mobile",
                    "Owned image student produces native construction controls")
                val bytes=GlbWriter.encode(GeneratedAsset(carrier,listOf(mesh)))
                assertTrue(bytes.size>2000 && mesh.indices.size/3<=3000)
                val checksum=digest(bytes)
                val stem=case+"__"+variant
                Files.write(root.resolve(stem+".glb"),bytes)
                val meta="{\"schema\":\"assetwright-native-visual-reconstruction-v1\","+
                    "\"case\":\""+case+"\","+
                    "\"variant\":\""+variant+"\","+
                    "\"source_engine\":\"AssetWright-AdvancedFormLab\","+
                    "\"reference_glb_sha256\":\""+sourceSha+"\","+
                    "\"chosen_operation\":\""+actualOperation.name+"\","+
                    "\"chosen_strength\":"+actualStrength+","+
                    "\"generated_glb_sha256\":\""+checksum+"\"}"
                Files.write(root.resolve(stem+".json"),meta.toByteArray(Charsets.UTF_8))
                exports++
            }
        }
        assertEquals(36,observed.size)
        assertEquals(72,exports)
    }
}
