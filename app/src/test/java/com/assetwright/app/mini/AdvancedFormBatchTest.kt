package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * New, strictly research-only source GLBs. The five-form v1 heldout families,
 * exposed vehicle families and checkpoint are never consulted by this test.
 */
class AdvancedFormBatchTest {
    private data class Dimensions(val length: Float,val width: Float,val height: Float)
    private data class Family(val id:String,val dims:Dimensions)

    private val training=(0 until 12).map { i ->
        Family("advtrain"+(i+1).toString().padStart(2,'0'),
            Dimensions(2.65f+i*.29f,1.22f+(i%5)*.22f+(i/5)*.06f,
                .87f+(i%4)*.15f+(i/4)*.045f))
    }
    private val validation=listOf(
        Dimensions(3.14f,2.04f,1.08f),
        Dimensions(4.79f,1.72f,1.47f),
        Dimensions(5.94f,2.81f,1.76f),
        Dimensions(2.21f,1.54f,2.13f)
    ).mapIndexed { i,d -> Family("advval"+(i+1),d) }
    private val aspectShift=listOf(
        Dimensions(7.45f,1.08f,.86f),
        Dimensions(2.16f,3.46f,1.32f),
        Dimensions(3.38f,1.45f,3.21f),
        Dimensions(5.85f,1.06f,2.57f)
    ).mapIndexed { i,d -> Family("advshift"+(i+1),d) }

    private val trainLevels=listOf(.08f,.17f,.26f,.35f,.44f,
        .53f,.62f,.71f,.80f,.89f)
    private val valLevels=listOf(.135f,.365f,.595f,.825f)
    private val shiftLevels=listOf(.21f,.41f,.61f,.81f)

    @Test
    fun sixAdvancedOperationsHaveRealMeasuredGeometryAndSafeBounds() {
        for (operation in AdvancedFormOperation.values()) {
            val old=AdvancedFormLab.generate(AdvancedFormSpec(
                operation,4.1f,2.3f,1.3f,.15f))
            val changed=AdvancedFormLab.generate(AdvancedFormSpec(
                operation,4.1f,2.3f,1.3f,.85f))
            assertEquals("Same sealed topology across strength",old.indices.size,changed.indices.size)
            assertTrue("Native operation must actually move vertices",old.vertices!=changed.vertices)
            assertTrue(old.indices.all { it in old.vertices.indices })
            assertTrue(changed.indices.all { it in changed.vertices.indices })
            assertTrue(old.indices.size/3 in 900..3000)
        }
        val s=AdvancedFormSpec(AdvancedFormOperation.SECTION_LOFT,4f,2f,1f,.5f)
        for(value in listOf(Float.NaN,Float.POSITIVE_INFINITY,-.01f,1.01f)) {
            var refused=false
            try {AdvancedFormLab.generate(s.copy(strength=value))}
            catch (_:IllegalArgumentException){refused=true}
            assertTrue("Invalid geometry strength was allowed",refused)
        }
    }

    private fun write(root:Path,split:String,family:Family,
                      op:AdvancedFormOperation,strength:Float) {
        val dims=family.dims
        val shell=AdvancedFormLab.generate(AdvancedFormSpec(
            op,dims.length,dims.width,dims.height,strength))
        assertTrue(shell.indices.size/3 <= 3000)
        val carrier=VehicleSpec("Original advanced form",4f,2f,1.4f,
            1.7f,.5f,1f,"Mobile","native form research carrier")
        val bytes=GlbWriter.encode(GeneratedAsset(carrier,listOf(shell)))
        val digest=MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        val level="s"+(strength*1000).roundToInt().toString().padStart(3,'0')
        val stem=split+"__"+family.id+"__"+op.name.lowercase()+"__"+level
        Files.write(root.resolve(stem+".glb"),bytes)
        val meta="{\"schema\":\"assetwright-advanced-native-forms-v1\","+
            "\"phase\":\""+split+"\",\"family\":\""+family.id+"\","+
            "\"case\":\""+stem+"\",\"operation\":\""+op.name+"\","+
            "\"strength\":"+strength+",\"length\":"+dims.length+
            ",\"width\":"+dims.width+",\"height\":"+dims.height+
            ",\"segments\":24,\"stations\":24,"+
            "\"native_generator\":\"AssetWright-AdvancedFormLab\","+
            "\"source_glb_sha256\":\""+digest+"\"}"
        Files.write(root.resolve(stem+".json"),meta.toByteArray(Charsets.UTF_8))
    }

    @Test
    fun exportLargeOriginalAdvancedFormBatchForIndependentAudit() {
        val out=System.getenv("ASSETWRIGHT_ADVANCED_FORMS_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(out)
        Files.createDirectories(root)
        val batches=listOf(
            Triple("train",training,trainLevels),
            Triple("validation",validation,valLevels),
            Triple("aspect_shift",aspectShift,shiftLevels))
        var count=0
        for ((split,families,levels) in batches) {
            for(family in families) for(op in AdvancedFormOperation.values())
                for(strength in levels) {
                    write(root,split,family,op,strength)
                    count++
                }
        }
        assertEquals(912,count)
        assertEquals(count,Files.list(root).use { s ->
            s.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
