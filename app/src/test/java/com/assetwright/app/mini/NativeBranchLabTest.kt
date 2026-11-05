package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** New research-only placement families; no old source evaluation reuse. */
class NativeBranchLabTest {
    private data class Dims(val length:Float,val width:Float,val height:Float)
    private val training=(0 until 6).map { i ->
        Dims(3.15f+i*.61f,1.35f+(i%3)*.37f,.92f+(i%4)*.22f)
    }
    private val validation=listOf(
        Dims(3.57f,2.16f,1.15f),Dims(5.83f,1.86f,1.63f))
    private val aspect=listOf(
        Dims(8.15f,1.01f,.82f),Dims(2.66f,3.40f,1.04f))
    private fun controls(phase:String,family:Int,site:Int,variant:Int):Triple<Float,Float,Float> {
        val offset=if(phase=="train")0f else if(phase=="validation").005f else .008f
        return Triple(
            .15f+((family*17+site*13+variant*29)%69)/100f+offset,
            .14f+((family*23+site*19+variant*31)%70)/100f+offset,
            .13f+((family*31+site*17+variant*37)%72)/100f+offset)
    }
    private fun sample(phase:String,family:Int,site:Int,variant:Int,d:Dims):NativeBranchSpec {
        val c=controls(phase,family,site,variant)
        return NativeBranchSpec(d.length,d.width,d.height,site,c.first,c.second,c.third)
    }
    @Test
    fun everyBranchSiteHasRealOneShellManifoldTopology() {
        for(site in 0 until NativeBranchLab.SITES) {
            val spec=sample("train",1,site,0,Dims(4.3f,2.0f,1.4f))
            val part=NativeBranchLab.generate(spec)
            assertEquals(NativeBranchLab.VERTICES,part.vertices.size)
            assertEquals(NativeBranchLab.TRIANGLES,part.indices.size/3)
            val edgeCounts=HashMap<Pair<Int,Int>,MutableList<Pair<Int,Int>>>()
            for(i in part.indices.indices step 3) for((a,b) in listOf(
                part.indices[i] to part.indices[i+1],
                part.indices[i+1] to part.indices[i+2],
                part.indices[i+2] to part.indices[i])) {
                val edge=minOf(a,b) to maxOf(a,b)
                edgeCounts.getOrPut(edge) { ArrayList() }.add(a to b)
            }
            assertEquals(NativeBranchLab.EDGES,edgeCounts.size)
            assertTrue("No open, nonmanifold or inverted junction edges",edgeCounts.values.all {
                it.size==2 && it[0].first==it[1].second &&
                    it[0].second==it[1].first
            })
            assertEquals("Parent genus-one through-bore is preserved",
                0,part.vertices.size-edgeCounts.size+part.indices.size/3)
            assertEquals("All vertices must be indexed",part.vertices.size,
                part.indices.toSet().size)
        }
        val s=sample("train",1,9,1,Dims(4f,1.7f,1.3f))
        val old=NativeBranchLab.generate(s)
        assertTrue(NativeBranchLab.generate(s.copy(rise=.99f)).vertices!=old.vertices)
        assertTrue(NativeBranchLab.generate(s.copy(blend=.99f)).vertices!=old.vertices)
        assertTrue(NativeBranchLab.generate(s.copy(socketDepth=.99f)).vertices!=old.vertices)
        for(bad in listOf(Float.NaN,Float.POSITIVE_INFINITY,-.1f,1.1f)) {
            var rejected=false
            try {NativeBranchLab.generate(s.copy(blend=bad))}
            catch(_:IllegalArgumentException){rejected=true}
            assertTrue(rejected)
        }
    }
    private fun export(root:Path,phase:String,family:Int,site:Int,
                       variant:Int,dimensions:Dims) {
        val spec=sample(phase,family,site,variant,dimensions)
        val source=NativeBranchLab.generate(spec)
        val carrier=VehicleSpec("Native integrated branch",4f,2f,1.4f,
            1.7f,.5f,1f,"Mobile","original integrated blind socket")
        val bytes=GlbWriter.encode(GeneratedAsset(carrier,listOf(source)))
        val hash=MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        val stem=phase+"__b"+family.toString().padStart(2,'0')+
            "__site"+site.toString().padStart(2,'0')+"__v"+variant
        Files.write(root.resolve(stem+".glb"),bytes)
        val metadata="{\"schema\":\"assetwright-native-branch-v1\","+
            "\"case\":\""+stem+"\",\"phase\":\""+phase+"\","+
            "\"family\":"+family+",\"site\":"+site+",\"variant\":"+variant+
            ",\"generator\":\"AssetWright-NativeBranchLab\","+
            "\"length\":"+spec.length+",\"width\":"+spec.width+
            ",\"height\":"+spec.height+",\"rise\":"+spec.rise+
            ",\"socket_depth\":"+spec.socketDepth+
            ",\"blend\":"+spec.blend+
            ",\"source_glb_sha256\":\""+hash+"\"}"
        Files.write(root.resolve(stem+".json"),metadata.toByteArray(Charsets.UTF_8))
    }
    @Test
    fun export520NativeConnectedBranchShapes() {
        val dir=System.getenv("ASSETWRIGHT_BRANCH_SOURCE")?.takeIf { it.isNotBlank() } ?:return
        val root=Path.of(dir)
        Files.createDirectories(root)
        for((phase,families,variants) in listOf(
            Triple("train",training,3),
            Triple("validation",validation,2),
            Triple("aspect_shift",aspect,2))) {
            for((i,d) in families.withIndex())
                for(site in 0 until NativeBranchLab.SITES)
                    for(v in 0 until variants)
                        export(root,phase,i+1,site,v,d)
        }
        assertEquals(520,Files.list(root).use { it.filter { p ->
            p.fileName.toString().endsWith(".glb") }.count().toInt() })
    }
}
