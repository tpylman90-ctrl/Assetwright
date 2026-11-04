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
 * Builds fresh native three-operator programs, with true source-disjoint
 * dimension and aspect families. No previous evaluation GLB is reused.
 */
class NativeCompositionBatchTest {
    private data class Dimensions(val length:Float,val width:Float,val height:Float)
    private data class Family(val id:String,val dim:Dimensions)
    private val train=(0 until 10).map { i ->
        Family("ctrain"+(i+1).toString().padStart(2,'0'),
            Dimensions(2.58f+i*.37f,1.18f+(i%5)*.27f+(i/5)*.07f,
                .86f+(i%4)*.17f+(i/4)*.045f))
    }
    private val validation=listOf(
        Dimensions(3.17f,1.97f,1.26f),Dimensions(4.76f,2.32f,1.64f),
        Dimensions(5.92f,2.08f,1.44f),Dimensions(2.27f,1.65f,1.78f)
    ).mapIndexed { i,d -> Family("cval"+(i+1),d) }
    private val shift=listOf(
        Dimensions(8.21f,1.09f,.81f),Dimensions(2.18f,3.74f,1.28f),
        Dimensions(3.58f,1.31f,3.63f),Dimensions(6.83f,1.20f,2.83f)
    ).mapIndexed { i,d -> Family("cshift"+(i+1),d) }

    private val combos=buildList {
        val ops=NativeCompositionLab.dependencyOrder
        for(a in 0 until ops.size)for(b in a+1 until ops.size)
            for(c in b+1 until ops.size)add(listOf(ops[a],ops[b],ops[c]))
    }
    private fun strength(split:String,f:Int,p:Int,slot:Int,step:Int):Float {
        val basis=when(split){
            "train" -> 17 + ((f*31+p*23+slot*13+step*19)%68)
            "validation" -> 18 + ((f*29+p*17+slot*23+step*11)%66)
            else -> 19 + ((f*19+p*29+slot*17+step*23)%65)
        }
        val fractional=if(split=="train")0f else if(split=="validation").005f else .007f
        return basis/100f+fractional
    }
    private fun recipe(split:String,f:Int,p:Int,slot:Int):List<NativeCompositionCommand> =
        combos[p].mapIndexed { k,op -> NativeCompositionCommand(op,
            strength(split,f,p,slot,k)) }

    @Test
    fun completeSingleManifoldProgramHasStrictTypedDependencies() {
        assertEquals(20,combos.size)
        val program=recipe("train",2,8,1)
        val spec=NativeCompositionSpec(4.4f,2.2f,1.3f,program)
        val mesh=NativeCompositionLab.generate(spec)
        assertEquals(32*32*2+32*2,mesh.indices.size/3)
        assertEquals(33*32+2,mesh.vertices.size)
        assertTrue(mesh.indices.all { it in mesh.vertices.indices })
        var refused=false
        try { NativeCompositionLab.generate(spec.copy(commands=program.reversed())) }
        catch (_:IllegalArgumentException) {refused=true}
        assertTrue("Order must be enforced",refused)
        refused=false
        try { NativeCompositionLab.generate(spec.copy(
            commands=listOf(program[0],program[0],program[2]))) }
        catch (_:IllegalArgumentException) {refused=true}
        assertTrue("Repeat command must be rejected",refused)
        refused=false
        try { NativeCompositionLab.generate(spec.copy(commands=
            listOf(program[0].copy(strength=Float.NaN),program[1],program[2]))) }
        catch (_:IllegalArgumentException){refused=true}
        assertTrue("Nonfinite control must be rejected",refused)
        val changed=NativeCompositionLab.generate(spec.copy(commands=
            program.map { it.copy(strength=(it.strength+.1f).coerceAtMost(.95f)) }))
        assertTrue("Three real controls must deform the source hull",
            changed.vertices!=mesh.vertices)
    }

    private fun write(root:Path,phase:String,family:Family,
                      commands:List<NativeCompositionCommand>,plan:Int,slot:Int) {
        val d=family.dim
        val mesh=NativeCompositionLab.generate(NativeCompositionSpec(
            d.length,d.width,d.height,commands))
        val carrier=VehicleSpec("Original connected form",4f,2f,1.4f,
            1.7f,.5f,1f,"Mobile","original connected three-step native hull")
        val glb=GlbWriter.encode(GeneratedAsset(carrier,listOf(mesh)))
        val hash=MessageDigest.getInstance("SHA-256").digest(glb).joinToString("") {
            "%02x".format(it.toInt() and 255)
        }
        val stem=phase+"__"+family.id+"__p"+
            plan.toString().padStart(2,'0')+"__v"+slot
        val steps=commands.joinToString(",") {
            "{\"operation\":\""+it.operation.name+"\",\"strength\":"+it.strength+"}"
        }
        val metadata="{\"schema\":\"assetwright-native-composition-v1\","+
            "\"phase\":\""+phase+"\",\"family\":\""+family.id+"\","+
            "\"case\":\""+stem+"\",\"plan_index\":"+plan+
            ",\"length\":"+d.length+",\"width\":"+d.width+
            ",\"height\":"+d.height+",\"segments\":32,\"stations\":32,"+
            "\"generator\":\"AssetWright-NativeCompositionLab\","+
            "\"source_glb_sha256\":\""+hash+"\","+
            "\"commands\":["+steps+"]}"
        Files.write(root.resolve(stem+".glb"),glb)
        Files.write(root.resolve(stem+".json"),metadata.toByteArray(Charsets.UTF_8))
    }

    @Test
    fun exportNewSourceHashedThreeStepCurriculum() {
        val location=System.getenv("ASSETWRIGHT_COMPOSED_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(location);Files.createDirectories(root)
        var total=0
        for((phase,families,slots) in listOf(
            Triple("train",train,4),Triple("validation",validation,2),
            Triple("aspect_shift",shift,2))) {
            for((f,family) in families.withIndex())
                for(plan in combos.indices)for(slot in 0 until slots) {
                    write(root,phase,family,recipe(phase,f,plan,slot),plan,slot)
                    total++
                }
        }
        assertEquals(1120,total)
        assertEquals(total,Files.list(root).use { it.filter { path ->
            path.fileName.toString().endsWith(".glb") }.count().toInt() })
    }
}
