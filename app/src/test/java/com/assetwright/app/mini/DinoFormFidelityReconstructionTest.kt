package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/**
 * Student outputs choose the original geometric FORM, operation and strength.
 * No test-set correct archetype, topology, operation or strength is used in
 * constructing the student's output. Only dimensions are known inputs.
 */
class DinoFormFidelityReconstructionTest {
    private val variants=listOf("parent_v7_hard","supervised_replay",
        "physical_replay","hard_physical")
    private val fields=listOf(
        "case","source_glb_sha256","baseline_glb_sha256",
        "predicted_operation","predicted_strength",
        "predicted_archetype","length","width","height")
    private fun hash(b:ByteArray):String=
        MessageDigest.getInstance("SHA-256").digest(b).joinToString("") {
            "%02x".format(it.toInt() and 255)
        }

    private fun sourceForm(
        name:String,op:AdvancedFormOperation,power:Float,
        length:Float,width:Float,height:Float):MeshPart {
        if(name=="LEGACY_SHELL") return AdvancedFormLab.generate(
            AdvancedFormSpec(op,length,width,height,power))
        val form=NativeFormArchetype.valueOf(name)
        // Fixed ORIGINAL production grammar by chosen form, not test
        // target tessellation. Supports variable object topology.
        val mesh=when(form) {
            NativeFormArchetype.SPINDLE -> 24 to 24
            NativeFormArchetype.WEDGE -> 32 to 24
            NativeFormArchetype.BOX_MODULE -> 40 to 24
            NativeFormArchetype.BARREL -> 24 to 32
            NativeFormArchetype.ARCH -> 32 to 32
            NativeFormArchetype.BLADE -> 40 to 32
            NativeFormArchetype.CANOPY_POD -> 24 to 32
            NativeFormArchetype.TRUSS_BEAM -> 40 to 24
        }
        return NativeDiverseFormLab.generate(NativeDiverseFormSpec(
            form,op,length,width,height,power,mesh.first,mesh.second))
    }

    @Test fun generateOriginalShapeSelectedByActualNeuralFormHead() {
        val input=System.getenv("ASSETWRIGHT_FORM_FIDELITY_PREDICTIONS")
            ?.takeIf { it.isNotBlank() } ?: return
        val location=System.getenv("ASSETWRIGHT_FORM_FIDELITY_RECON")
            ?.takeIf { it.isNotBlank() } ?: return
        val props=Properties()
        Files.newBufferedReader(Path.of(input)).use { props.load(it) }
        require(props.getProperty("schema")==
            "assetwright-original-v8-geometry-fidelity-predictions")
        require(props.getProperty("external_mesh_used")=="false")
        require(props.getProperty("study_id")=="form_fidelity_v8")
        require(props.getProperty("count")=="288")
        val required=mutableSetOf(
            "schema","external_mesh_used","study_id","count")
        for(name in variants) for(i in 0 until 288) for(key in fields)
            required.add(name+"."+i+"."+key)
        require(props.stringPropertyNames()==required) {
            "Neural proposals do not have exact source-aligned data fields"
        }
        val out=Path.of(location)
        Files.createDirectories(out)
        val cases=mutableSetOf<String>()
        var generated=0
        for(i in 0 until 288) {
            fun field(mode:String,name:String)=
                props.getProperty(mode+"."+i+"."+name)
            val case=field("parent_v7_hard","case")
            require(Regex("validation__sf_blind(0[1-9]|1[0-6])__[a-z_]+__s[0-9]{3}")
                .matches(case))
            require(cases.add(case))
            val dims=listOf("length","width","height").map{
                field("parent_v7_hard",it).toFloat()
            }
            require(dims.all { it.isFinite()&&it in .5f..12f })
            for(name in variants) {
                for(key in listOf(
                    "case","source_glb_sha256","baseline_glb_sha256",
                    "length","width","height")) {
                    require(field(name,key)==field("parent_v7_hard",key)) {
                        "Original source cases unfairly changed between models"
                    }
                }
                val form=field(name,"predicted_archetype")
                require(form=="LEGACY_SHELL" ||
                    NativeFormArchetype.values().any { it.name==form })
                val op=AdvancedFormOperation.valueOf(
                    field(name,"predicted_operation"))
                val strength=field(name,"predicted_strength").toFloat()
                require(strength.isFinite()&&strength in 0f..1f)
                val mesh=sourceForm(
                    form,op,strength,dims[0],dims[1],dims[2])
                val spec=VehicleSpec(
                    "Owned neural "+form,dims[0],dims[1],dims[2],
                    1.7f,.55f,1.07f,"Mobile",
                    "Original native multi-form student proposal")
                val bytes=GlbWriter.encode(GeneratedAsset(spec,listOf(mesh)))
                assertTrue("Real indexed original native GLB",bytes.size>2000 &&
                    mesh.indices.size/3 in 900..3000)
                val nameOut=case+"__"+name
                Files.write(out.resolve(nameOut+".glb"),bytes)
                val metadata="{\"schema\":\"assetwright-neural-multiform-source-reconstruction-v8\","+
                    "\"case\":\""+case+"\","+
                    "\"variant\":\""+name+"\","+
                    "\"source_engine\":\"AssetWright-NativeDiverseFormLab\","+
                    "\"reference_glb_sha256\":\""+field(name,"source_glb_sha256")+"\","+
                    "\"baseline_glb_sha256\":\""+field(name,"baseline_glb_sha256")+"\","+
                    "\"predicted_archetype\":\""+form+"\","+
                    "\"predicted_operation\":\""+op.name+"\","+
                    "\"predicted_strength\":"+strength+","+
                    "\"triangles\":"+mesh.indices.size/3+","+
                    "\"vertices\":"+mesh.vertices.size+","+
                    "\"generated_glb_sha256\":\""+hash(bytes)+"\"}"
                Files.write(out.resolve(nameOut+".json"),
                    metadata.toByteArray(Charsets.UTF_8))
                generated++
            }
        }
        assertEquals(288,cases.size)
        assertEquals(1152,generated)
        assertEquals(1152,Files.list(out).use { stream ->
            stream.filter { it.fileName.toString().endsWith(".glb") }
                .count().toInt()
        })
    }
}
