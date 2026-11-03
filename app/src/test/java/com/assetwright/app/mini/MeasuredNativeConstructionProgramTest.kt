package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import java.util.Properties

/** Export original native GLBs; never import third-party geometry. */
class MeasuredNativeConstructionProgramTest {
    private val order = NativeCadOperationBridge.constructionOrder

    private fun sample(family:String):VehicleSpec {
        val dims = when(family) {
            "coupe" -> listOf(4.45f,2.18f,1.27f,1.55f,.42f,1.08f)
            "utility" -> listOf(5.32f,2.58f,1.62f,1.82f,.55f,1.15f)
            "blindfamily" -> listOf(5.06f,2.43f,1.40f,1.73f,.52f,1.18f)
            else -> error("Unknown vehicle family")
        }
        return VehicleSpec("Original "+family,dims[0],dims[1],dims[2],
            dims[3],dims[4],dims[5],"Mobile",
            "Original "+family+" hover vehicle with one rear engine",
            ConstructionPlan(2,"exposed"))
    }

    private fun write(root:Path,stem:String,phase:String,family:String,
        original:VehicleSpec,
        commands:List<NativeCadOperationBridge.Command>,
        modelSha:String="original-native-generator") {
        val spec=if(commands.isEmpty()) original else
            NativeCadOperationBridge.applyProgram(original,commands)
        val asset=MiniGeometry.generate(spec)
        assertTrue(asset.triangleCount <= 12000)
        val glb=GlbWriter.encode(asset)
        assertTrue(glb.size > 2000)
        val hash=MessageDigest.getInstance("SHA-256").digest(glb)
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        Files.write(root.resolve(stem+".glb"),glb)
        val operations=commands.map {
            "{\"operation\":\""+it.operation+"\",\"strength\":"+it.strength+"}"
        }.joinToString(",")
        val json="{\"schema\":\"assetwright-native-measured-program-v1\","+
            "\"original_generator\":\"android-native-MiniGeometry\","+
            "\"phase\":\""+phase+"\",\"family\":\""+family+"\","+
            "\"case\":\""+stem+"\",\"model_sha256\":\""+modelSha+"\","+
            "\"source_glb_sha256\":\""+hash+"\","+
            "\"commands\":["+operations+"]}"
        Files.write(root.resolve(stem+".json"),json.toByteArray(Charsets.UTF_8))
    }

    private fun rejects(action:()->Unit) {
        var thrown=false
        try { action() } catch (exc:IllegalArgumentException) { thrown=true }
        assertTrue("Invalid operation programs must fail closed",thrown)
    }

    @Test
    fun dependentNativeProgramsRefuseWrongOrderingAndDuplicateOperations() {
        val original=sample("coupe")
        assertEquals(1,original.driveCount)
        val a=NativeCadOperationBridge.Command(
            NativeCadOperationBridge.COCKPIT_SHOULDER,.5f)
        val b=NativeCadOperationBridge.Command(
            NativeCadOperationBridge.REAR_SOCKET,.5f)
        val c=NativeCadOperationBridge.Command(
            NativeCadOperationBridge.REAR_NACELLE,.5f)
        rejects { NativeCadOperationBridge.applyProgram(original,listOf(b,a)) }
        rejects { NativeCadOperationBridge.applyProgram(original,listOf(a,a)) }
        rejects { NativeCadOperationBridge.applyProgram(original,listOf(a,c,b)) }
        rejects { NativeCadOperationBridge.applyProgram(original,listOf(
            NativeCadOperationBridge.Command("execute_downloaded_cadquery",.8f))) }
        val combined=NativeCadOperationBridge.applyProgram(original,listOf(a,b,c))
        val steps=ShapeProgram.steps(combined).map { it.operation }
        assertTrue(order.all { it in steps })
        assertEquals(3,order.filter { it in steps }.size)
        assertEquals(MiniGeometry.generate(original).parts.size,
            MiniGeometry.generate(combined).parts.size)
        assertTrue(MiniGeometry.generate(combined).triangleCount <= 12000)
    }

    @Test
    fun exportMeasuredLearningExamplesAndReservedReferenceGeometry() {
        val location=System.getenv("ASSETWRIGHT_MEASURED_REFERENCE_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(location)
        Files.createDirectories(root)
        for (family in listOf("coupe","utility")) {
            val original=sample(family)
            write(root,"measure__"+family+"__baseline","train",
                family,original,emptyList())
            for(op in order) for((suffix,value) in listOf(
                "250" to .25f,"500" to .50f,"900" to .90f)) {
                write(root,"measure__"+family+"__"+op+"__s"+suffix,
                    "train",family,original,
                    listOf(NativeCadOperationBridge.Command(op,value)))
            }
        }
        val unfamiliar=sample("blindfamily")
        write(root,"measure__blindfamily__baseline","reference",
            "blindfamily",unfamiliar,emptyList())
        for(op in order) for((suffix,value) in listOf(
            "375" to .375f,"725" to .725f)) {
            write(root,"measure__blindfamily__"+op+"__s"+suffix,
                "reference","blindfamily",unfamiliar,
                listOf(NativeCadOperationBridge.Command(op,value)))
        }
        write(root,"measure__blindfamily__program_target","reference",
            "blindfamily",unfamiliar,order.map {
                NativeCadOperationBridge.Command(it,.725f)
            })
    }

    @Test
    fun exportLearnedParametersAndCompositionFromValidatedMeasuredPlan() {
        val path=System.getenv("ASSETWRIGHT_MEASURED_INVERSE_PLAN")
            ?.takeIf { it.isNotBlank() } ?: return
        val location=System.getenv("ASSETWRIGHT_MEASURED_PREDICTION_OUT")
            ?.takeIf { it.isNotBlank() } ?: return
        val props=Properties()
        Files.newBufferedReader(Path.of(path)).use { props.load(it) }
        val expected=mutableSetOf("schema","source_model_sha256",
            "geometry_training_sha256","provenance","count")
        for(i in 0..2){
            expected+="step"+i+".operation"
            expected+="step"+i+".strength"
        }
        require(props.stringPropertyNames()==expected)
        require(props.getProperty("schema")==
            "assetwright-native-measured-inverse-plan-v1")
        require(props.getProperty("provenance")==
            "OWN-classifier-and-native-GLB-measurements")
        require(props.getProperty("count")=="3")
        require(Regex("[a-f0-9]{64}").matches(
            props.getProperty("source_model_sha256")))
        require(Regex("[a-f0-9]{64}").matches(
            props.getProperty("geometry_training_sha256")))
        val commands=(0..2).map { i ->
            NativeCadOperationBridge.Command(
                props.getProperty("step"+i+".operation"),
                props.getProperty("step"+i+".strength").toFloat())
        }
        require(commands.map { it.operation }==order)
        require(commands.all { it.strength in .10f..1f })
        val root=Path.of(location)
        Files.createDirectories(root)
        val original=sample("blindfamily")
        val sha=props.getProperty("source_model_sha256")
        for(command in commands) {
            write(root,"predicted__blindfamily__"+command.operation,
                "predicted","blindfamily",original,listOf(command),sha)
        }
        write(root,"predicted__blindfamily__program","predicted",
            "blindfamily",original,commands,sha)
    }
}
