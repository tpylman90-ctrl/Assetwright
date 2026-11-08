package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.math.roundToInt

/**
 * 8 DISTINCT original geometries x 6 operators x 5 TRAIN strength values,
 * including DIFFERENT triangulation density, family proportions and profiles.
 * Unlike all preceding studies, EVERY native school is not the same shell.
 *
 * Train: 16 shape families, 2 for each archetype, 24-32 ring sections.
 * Dev: 8 disjoint families, 32x32 mesh topology.
 * Blind: 8 uninspected families, 40x32 mesh topology (zero previous use).
 */
class DinoIdentityContinuationBatchTest {
    data class Family(val id:String,val archetype:NativeFormArchetype,
        val length:Float,val width:Float,val height:Float,
        val segments:Int,val stations:Int)
    private val forms=NativeFormArchetype.values()
    // One identical set of proportions and tessellation is used for EACH
    // form archetype: dimensions CANNOT identify shape class by shortcut.
    // Five independent TRAIN proportions per form, one dev and one blind.
    /**
     * 6 balanced training dimension patterns per archetype, 2 new
     * development patterns and 2 never inspected blind patterns.
     * Different from v6/v7; no class-specific dimension shortcut.
     */
    /**
     * Eight original forms, equal proportions per category, eight distinct
     * TRAIN shape examples per form. 2 unseen dev and 2 untouched blind
     * proportions per form. No previous blind mf/si/sf families enter.
     */
    private fun family(tag:String,number:Int,phase:String):Family {
        val archetype=forms[(number-1)%8]
        val variation=(number-1)/8
        val proportions=when(phase) {
            "train" -> arrayOf(
                floatArrayOf(2.94f,1.42f,1.84f),
                floatArrayOf(4.76f,2.33f,1.36f),
                floatArrayOf(5.17f,2.72f,2.20f),
                floatArrayOf(3.68f,1.78f,2.46f),
                floatArrayOf(6.24f,2.54f,1.66f),
                floatArrayOf(4.03f,2.89f,1.22f),
                floatArrayOf(5.63f,1.73f,2.03f),
                floatArrayOf(3.27f,2.44f,1.48f))[variation]
            "development" -> arrayOf(
                floatArrayOf(5.92f,2.34f,1.81f),
                floatArrayOf(3.91f,1.62f,2.34f))[variation]
            else -> arrayOf(
                floatArrayOf(5.39f,2.12f,2.49f),
                floatArrayOf(3.49f,2.63f,1.31f))[variation]
        }
        return Family(tag+number.toString().padStart(2,'0'),
            archetype,proportions[0],proportions[1],proportions[2],
            if(phase=="train") (if(variation%2==0) 24 else 32)
                else if(phase=="development") 32 else 40,
            if(phase=="train") 24 else 32)
    }
    private val train=(1..64).map { family("if_train",it,"train") }
    private val dev=(1..16).map { family("if_dev",it,"development") }
    private val blind=(1..16).map { family("if_blind",it,"validation") }
    private val levels=mapOf(
        "train" to listOf(.08f,.45f,.92f),
        "development" to listOf(.18f,.54f,.84f),
        "validation" to listOf(.11f,.41f,.96f)
    )
    private fun sha(bytes:ByteArray):String=
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {
            "%02x".format(it.toInt() and 255)
        }

    private fun write(root:Path,phase:String,family:Family,
                      operation:AdvancedFormOperation,strength:Float,
                      baseline:Boolean) {
        val end=if(baseline) "baseline" else
            operation.name.lowercase()+"__s"+
                (strength*1000).roundToInt().toString().padStart(3,'0')
        val id=phase+"__"+family.id+"__"+end
        val native=NativeDiverseFormLab.generate(NativeDiverseFormSpec(
            family.archetype,operation,family.length,family.width,
            family.height,strength,family.segments,family.stations))
        assertTrue("Original diverse mesh triangles are bounded",
            native.indices.size/3 in 900..3000)
        val carrier=VehicleSpec(
            "Original "+family.archetype.name,family.length,family.width,
            family.height,1.7f,.55f,1.07f,"Mobile",
            "Original native archetype training source")
        val glb=GlbWriter.encode(GeneratedAsset(carrier,listOf(native)))
        Files.write(root.resolve(id+".glb"),glb)
        val json="{\"schema\":\"assetwright-native-before-after-source-v1\","+
            "\"original_engine\":\"AssetWright-AdvancedFormLab\","+
            "\"source_generator\":\"NativeDiverseFormLab-v1\","+
            "\"case\":\""+id+"\","+
            "\"split\":\""+phase+"\","+
            "\"family\":\""+family.id+"\","+
            "\"baseline\":"+baseline+","+
            "\"operation\":\""+(if(baseline) "BASELINE" else operation.name)+"\","+
            "\"strength\":"+strength+","+
            "\"length\":"+family.length+","+
            "\"width\":"+family.width+","+
            "\"height\":"+family.height+","+
            "\"archetype\":\""+family.archetype.name+"\","+
            "\"segments\":"+family.segments+","+
            "\"stations\":"+family.stations+","+
            "\"source_glb_sha256\":\""+sha(glb)+"\"}"
        Files.write(root.resolve(id+".json"),json.toByteArray(Charsets.UTF_8))
    }

    @Test fun exportUnseenMultipleArchetypesAndTopologies() {
        val out=System.getenv("ASSETWRIGHT_IDENTITY_CONTINUATION_SOURCE")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(out)
        Files.createDirectories(root)
        var changed=0
        for((phase,families) in listOf(
            "train" to train,"development" to dev,"validation" to blind)) {
            assertEquals(8,families.map { it.archetype }.toSet().size)
            for(family in families) {
                write(root,phase,family,AdvancedFormOperation.SECTION_LOFT,0f,true)
                for(op in AdvancedFormOperation.values()) for(strength in levels.getValue(phase)){
                    write(root,phase,family,op,strength,false)
                    changed++
                }
            }
        }
        assertEquals(1728,changed)
        assertEquals(1824,Files.list(root).use { files ->
            files.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
