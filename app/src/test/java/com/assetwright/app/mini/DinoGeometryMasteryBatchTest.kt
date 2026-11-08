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
class DinoGeometryMasteryBatchTest {
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
    private fun family(tag:String,number:Int,phase:String):Family {
        val shape=forms[(number-1)%8]
        val index=(number-1)/8
        // Dimensions are shared across all 8 forms for every variation.
        // New dimensions and strengths; none are from prior validation sets.
        val size=when(phase) {
            "train" -> arrayOf(
                floatArrayOf(3.17f,1.67f,2.09f),
                floatArrayOf(5.13f,2.41f,1.53f),
                floatArrayOf(4.64f,2.83f,2.21f),
                floatArrayOf(6.11f,1.99f,1.43f),
                floatArrayOf(3.73f,2.56f,1.88f),
                floatArrayOf(5.49f,2.24f,2.32f))[index]
            "development" -> arrayOf(
                floatArrayOf(4.17f,1.85f,2.17f),
                floatArrayOf(6.03f,2.76f,1.94f))[index]
            else -> arrayOf(
                floatArrayOf(5.86f,2.16f,2.51f),
                floatArrayOf(3.48f,2.31f,1.64f))[index]
        }
        return Family(tag+number.toString().padStart(2,'0'),
            shape,size[0],size[1],size[2],
            if(phase=="train") (if(index%2==0) 24 else 32)
            else if(phase=="development") 32 else 40,
            if(phase=="train") 24 else 32)
    }
    private val train=(1..48).map { family("gm_train",it,"train") }
    private val dev=(1..16).map { family("gm_dev",it,"development") }
    private val blind=(1..16).map { family("gm_blind",it,"validation") }
    private val levels=mapOf(
        "train" to listOf(.065f,.235f,.595f,.895f),
        "development" to listOf(.16f,.48f,.86f),
        "validation" to listOf(.095f,.355f,.965f)
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
        val out=System.getenv("ASSETWRIGHT_GEOMETRY_MASTERY_SOURCE")
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
        assertEquals(1808,Files.list(root).use { files ->
            files.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
