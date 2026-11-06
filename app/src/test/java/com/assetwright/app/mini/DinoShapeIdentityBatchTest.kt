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
class DinoShapeIdentityBatchTest {
    data class Family(val id:String,val archetype:NativeFormArchetype,
        val length:Float,val width:Float,val height:Float,
        val segments:Int,val stations:Int)
    private val forms=NativeFormArchetype.values()
    // One identical set of proportions and tessellation is used for EACH
    // form archetype: dimensions CANNOT identify shape class by shortcut.
    // Five independent TRAIN proportions per form, one dev and one blind.
    private fun family(tag:String,number:Int,phase:String):Family {
        val archetype=forms[(number-1)%8]
        val variation=(number-1)/8
        val length=when(phase) {
            "train" -> floatArrayOf(3.1f,4.25f,5.55f,6.35f,4.85f)[variation]
            "development" -> floatArrayOf(5.05f,4.12f)[variation]
            else -> floatArrayOf(5.95f,3.71f)[variation]
        }
        val width=when(phase) {
            "train" -> floatArrayOf(1.30f,2.18f,2.68f,1.74f,2.38f)[variation]
            "development" -> floatArrayOf(1.98f,2.27f)[variation]
            else -> floatArrayOf(2.46f,1.61f)[variation]
        }
        val height=when(phase) {
            "train" -> floatArrayOf(1.07f,1.69f,1.91f,2.35f,1.43f)[variation]
            "development" -> floatArrayOf(2.09f,1.58f)[variation]
            else -> floatArrayOf(1.78f,2.32f)[variation]
        }
        return Family(tag+number.toString().padStart(2,'0'),
            archetype,length,width,height,
            if(phase=="train") (if(variation%2==0) 24 else 32)
                else if(phase=="development") 32 else 40,
            if(phase=="train") 24 else 32)
    }
    private val train=(1..40).map { family("si_train",it,"train") }
    private val dev=(1..16).map { family("si_dev",it,"development") }
    private val blind=(1..16).map { family("si_blind",it,"validation") }
    private val levels=mapOf(
        "train" to listOf(.05f,.25f,.48f,.72f,.95f),
        "development" to listOf(.15f,.39f,.63f,.88f),
        "validation" to listOf(.09f,.32f,.69f,.975f)
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
        val out=System.getenv("ASSETWRIGHT_SHAPE_IDENTITY_SOURCE")
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
        assertEquals(1968,changed)
        assertEquals(2040,Files.list(root).use { files ->
            files.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
