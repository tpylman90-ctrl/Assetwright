package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Native geometry curriculum. No external model supplies these mesh vertices. */
class NativeFormLabTest {
    private data class Dimensions(val length:Float,val width:Float,val height:Float)
    private val train = listOf(
        Dimensions(2.4f,1.35f,.85f),
        Dimensions(3.7f,1.62f,1.30f),
        Dimensions(5.1f,2.75f,1.82f))
    private val validation = listOf(
        Dimensions(2.9f,2.15f,1.18f),
        Dimensions(4.4f,1.92f,1.56f))

    @Test
    fun formsAreClosedBoundedNativeGeometryWithActualStrengthResponse() {
        for (kind in NativeFormKind.values()) {
            val original=NativeFormLab.generate(NativeFormSpec(kind,3.7f,2.1f,1.3f,.35f))
            val changed=NativeFormLab.generate(NativeFormSpec(kind,3.7f,2.1f,1.3f,.90f))
            assertEquals(original.indices.size, changed.indices.size)
            assertTrue(original.indices.size/3 < 5000)
            assertEquals(0,original.indices.size%3)
            assertTrue(original.indices.all { it in original.vertices.indices })
            assertTrue(changed.indices.all { it in changed.vertices.indices })
            if(kind != NativeFormKind.CYLINDER)
                assertTrue("Control must alter real source geometry: $kind",
                    original.vertices != changed.vertices)
        }
        val sample=NativeFormSpec(NativeFormKind.TAPERED_LOFT,2f,1f,1f,.5f)
        for (bad in listOf(Float.NaN,Float.POSITIVE_INFINITY,-.1f,1.01f)) {
            var refused=false
            try {NativeFormLab.generate(sample.copy(strength=bad))}
            catch (_:IllegalArgumentException) {refused=true}
            assertTrue("Unbounded strength accepted",refused)
        }
    }

    private fun export(root:Path, phase:String, family:String, dims:Dimensions,
                       kind:NativeFormKind, strength:Float, level:String) {
        val form=NativeFormSpec(kind,dims.length,dims.width,dims.height,strength)
        val shell=NativeFormLab.generate(form)
        val carrier=VehicleSpec("Native form research",4f,2f,1.4f,1.7f,.5f,1f,
            "Mobile","original native geometry research carrier")
        val glb=GlbWriter.encode(GeneratedAsset(carrier,listOf(shell)))
        val stem=phase+"__"+family+"__"+kind.name.lowercase()+"__"+level
        val sha=MessageDigest.getInstance("SHA-256").digest(glb)
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        Files.write(root.resolve(stem+".glb"),glb)
        val meta="{\"schema\":\"assetwright-native-form-foundation-v1\","+
            "\"phase\":\""+phase+"\",\"family\":\""+family+"\","+
            "\"case\":\""+stem+"\",\"kind\":\""+kind.name+"\","+
            "\"control\":"+strength+",\"length\":"+dims.length+
            ",\"width\":"+dims.width+",\"height\":"+dims.height+
            ",\"original_generator\":\"AssetWright-Kotlin-NativeFormLab\","+
            "\"source_glb_sha256\":\""+sha+"\"}"
        Files.write(root.resolve(stem+".json"),meta.toByteArray(Charsets.UTF_8))
    }

    @Test
    fun exportSourceHashedTrainAndUntouchedValidationForms() {
        val folder=System.getenv("ASSETWRIGHT_FORM_FOUNDATION_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(folder)
        Files.createDirectories(root)
        for ((phase, families, levels) in listOf(
            Triple("train",train,listOf("s350" to .35f,"s600" to .60f,"s900" to .90f)),
            Triple("validation",validation,listOf("s450" to .45f,"s750" to .75f)))) {
            for ((index,dims) in families.withIndex()) {
                val family=phase+(index+1)
                for (kind in NativeFormKind.values())
                    for ((level,strength) in levels)
                        export(root,phase,family,dims,kind,strength,level)
            }
        }
    }
}
