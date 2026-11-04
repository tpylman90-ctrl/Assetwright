package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.math.abs
import kotlin.math.roundToInt

/** Fresh independent research families, not the earlier vehicle or loft holdouts. */
class NativeInterfaceLabTest {
    private data class Shape(val length: Float, val width: Float, val height: Float)
    private val train = (0 until 12).map { i ->
        Shape(2.75f+i*.34f,1.25f+(i%5)*.18f+(i/5)*.05f,
            .82f+(i%4)*.20f+(i/4)*.05f)
    }
    private val holdout = listOf(
        // Retired if01..if04 were inspected diagnosing a provenance mismatch.
        Shape(3.32f,2.08f,1.17f),Shape(4.83f,2.28f,1.53f),
        Shape(6.03f,1.77f,1.80f),Shape(2.41f,1.73f,1.95f))
    private val aspect = listOf(
        // New uninspected aspect families; initial if01..if04 retired.
        Shape(7.91f,.93f,.69f),Shape(2.63f,3.61f,1.02f),
        Shape(3.49f,1.01f,3.28f),Shape(6.97f,1.24f,2.54f))

    private fun strength(split: String, family: Int, sample: Int, seed: Int) =
        when (split) {
            "train" -> (.12f + ((sample*seed+family*11)%79)/100f)
            "validation" -> (.125f + ((sample*seed+family*13)%77)/100f)
            else -> (.137f + ((sample*seed+family*17)%75)/100f)
        }

    private fun spec(split:String,family:Int,index:Int,shape:Shape) =
        NativeInterfaceSpec(shape.length,shape.width,shape.height,
            strength(split,family,index,19),
            strength(split,family,index,31),
            strength(split,family,index,47))

    @Test
    fun nativeBoreIsOneClosedGenusOneShellNotADecorativeHole() {
        val a=NativeInterfaceLab.generate(NativeInterfaceSpec(
            4.2f,2.3f,1.4f,.24f,.5f,.6f))
        assertEquals(2624,a.vertices.size)
        assertEquals(5248,a.indices.size/3)
        val edgeCounts=HashMap<Pair<Int,Int>,Int>()
        for (i in a.indices.indices step 3) for ((x,y) in listOf(
            a.indices[i] to a.indices[i+1],
            a.indices[i+1] to a.indices[i+2],
            a.indices[i+2] to a.indices[i])) {
            val key=minOf(x,y) to maxOf(x,y)
            edgeCounts[key]=(edgeCounts[key]?:0)+1
        }
        assertTrue("Every source mesh edge must join exactly two faces",
            edgeCounts.values.all { it==2 })
        assertEquals("One true through-passage must have genus-one topology",
            0,a.vertices.size-edgeCounts.size+a.indices.size/3)
        val b=NativeInterfaceLab.generate(NativeInterfaceSpec(
            4.2f,2.3f,1.4f,.89f,.8f,.2f))
        assertTrue(a.vertices!=b.vertices)
        assertEquals(a.indices.size,b.indices.size)
        val invalid=listOf(Float.NaN,Float.POSITIVE_INFINITY,-.1f,1.1f)
        for (value in invalid) {
            var rejected=false
            try {
                NativeInterfaceLab.generate(NativeInterfaceSpec(
                    4.2f,2.3f,1.4f,value,.5f,.5f))
            } catch (_:IllegalArgumentException) { rejected=true }
            assertTrue("Invalid through-bore control accepted",rejected)
        }
    }

    private fun export(root:Path,phase:String,family:Int,index:Int,shape:Shape) {
        val parameters=spec(phase,family,index,shape)
        val shell=NativeInterfaceLab.generate(parameters)
        val carrier=VehicleSpec("Native interface teaching shape",4f,2f,1.4f,
            1.7f,.5f,1f,"Mobile","original one-shell structural interface")
        val raw=GlbWriter.encode(GeneratedAsset(carrier,listOf(shell)))
        val digest=MessageDigest.getInstance("SHA-256").digest(raw)
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        val name=phase+"__if"+family.toString().padStart(2,'0')+
            "__s"+index.toString().padStart(2,'0')
        Files.write(root.resolve(name+".glb"),raw)
        val meta="{\"schema\":\"assetwright-native-interface-v1\","+
            "\"phase\":\""+phase+"\",\"family\":"+family+
            ",\"case\":\""+name+"\",\"generator\":\"AssetWright-NativeInterfaceLab\","+
            "\"length\":"+shape.length+",\"width\":"+shape.width+
            ",\"height\":"+shape.height+",\"segments\":32,\"stations\":40,"+
            "\"bore_strength\":"+parameters.boreStrength+
            ",\"flange_strength\":"+parameters.flangeStrength+
            ",\"blend_strength\":"+parameters.blendStrength+
            ",\"source_glb_sha256\":\""+digest+"\"}"
        Files.write(root.resolve(name+".json"),meta.toByteArray(Charsets.UTF_8))
    }

    @Test
    fun export480OriginalConnectedInterfaceGlbs() {
        val output=System.getenv("ASSETWRIGHT_INTERFACE_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(output)
        Files.createDirectories(root)
        for ((phase,shapes,count) in listOf(
            Triple("train",train,30),
            Triple("validation",holdout,15),
            Triple("aspect_shift",aspect,15))) {
            for ((family,shape) in shapes.withIndex()) for(index in 0 until count)
                export(root,phase,if(phase=="train")family+1 else family+5,
                    index,shape)
        }
        assertEquals(480,Files.list(root).use { stream ->
            stream.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
