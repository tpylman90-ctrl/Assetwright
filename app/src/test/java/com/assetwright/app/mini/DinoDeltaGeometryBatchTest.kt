package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.math.roundToInt

/**
 * Fresh original geometry before/after learning pairs. The baseline for a
 * family is exported ONCE; all six modifications use that exact baseline.
 * Never modifies a production generator or exposes the reserved holdouts to fitting.
 */
class DinoDeltaGeometryBatchTest {
    private data class Dims(val length:Float,val width:Float,val height:Float)
    private data class Family(val id:String,val dims:Dims)
    private val train=(1..12).map { i ->
        Family("bdtrain"+i.toString().padStart(2,'0'),
            Dims(2.45f+i*.29f,1.15f+(i%4)*.36f+(i/4)*.09f,
                .78f+(i%5)*.25f+(i/5)*.07f))
    }
    private val development=listOf(
        Family("bddev01",Dims(3.62f,1.69f,1.29f)),
        Family("bddev02",Dims(5.78f,2.74f,.98f)),
        Family("bddev03",Dims(4.26f,1.42f,2.69f))
    )
    // Reserved once, never tuned based on these shape families or strengths.
    private val validation=listOf(
        Family("bdhold01",Dims(2.88f,2.32f,1.67f)),
        Family("bdhold02",Dims(6.37f,1.83f,1.13f)),
        Family("bdhold03",Dims(4.93f,2.94f,2.31f))
    )
    private val strengths=mapOf(
        "train" to listOf(.12f,.28f,.44f,.62f,.82f),
        "development" to listOf(.20f,.49f,.76f),
        "validation" to listOf(.15f,.54f,.89f)
    )
    private fun hash(bytes:ByteArray)=MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }

    private fun write(root:Path,split:String,family:Family,
                      operation:AdvancedFormOperation,strength:Float,
                      stem:String,baseline:Boolean) {
        val dims=family.dims
        val mesh=AdvancedFormLab.generate(AdvancedFormSpec(operation,
            dims.length,dims.width,dims.height,strength))
        assertTrue("Source geometry triangle budget",mesh.indices.size/3 in 900..3000)
        val carrier=VehicleSpec("Owned transformation school",4f,2f,1.4f,
            1.7f,.5f,1f,"Mobile","Research-only original Kotlin geometry")
        val bytes=GlbWriter.encode(GeneratedAsset(carrier,listOf(mesh)))
        val sha=hash(bytes)
        Files.write(root.resolve(stem+".glb"),bytes)
        val doc="{\"schema\":\"assetwright-native-before-after-source-v1\","+
            "\"original_engine\":\"AssetWright-AdvancedFormLab\","+
            "\"case\":\""+stem+"\","+
            "\"split\":\""+split+"\","+
            "\"family\":\""+family.id+"\","+
            "\"baseline\":"+baseline+","+
            "\"operation\":\""+(if(baseline) "BASELINE" else operation.name)+"\","+
            "\"strength\":"+strength+","+
            "\"length\":"+dims.length+","+
            "\"width\":"+dims.width+","+
            "\"height\":"+dims.height+","+
            "\"source_glb_sha256\":\""+sha+"\"}"
        Files.write(root.resolve(stem+".json"),doc.toByteArray(Charsets.UTF_8))
    }

    @Test
    fun exportOriginalTransformationPairs() {
        val dir=System.getenv("ASSETWRIGHT_DINO_DELTA_SOURCE")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(dir)
        Files.createDirectories(root)
        val groups=listOf(Triple("train",train,strengths.getValue("train")),
            Triple("development",development,strengths.getValue("development")),
            Triple("validation",validation,strengths.getValue("validation")))
        var baselines=0
        var changes=0
        for ((split,families,levels) in groups) for(family in families) {
            val baselineName=split+"__"+family.id+"__baseline"
            write(root,split,family,AdvancedFormOperation.SECTION_LOFT,
                0f,baselineName,true)
            baselines++
            for(op in AdvancedFormOperation.values()) for(strength in levels) {
                val level="s"+(strength*1000).roundToInt().toString().padStart(3,'0')
                val stem=split+"__"+family.id+"__"+op.name.lowercase()+"__"+level
                write(root,split,family,op,strength,stem,false)
                changes++
            }
        }
        assertEquals(18,baselines)
        assertEquals(468,changes)
        assertEquals(486,Files.list(root).use { stream ->
            stream.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
