package com.assetwright.app.mini

import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Model-controlled native meshes from the learner's exported predicted TSV. */
class NativeInterfaceReconstructionTest {
    @Test
    fun regenerateHeldoutBoresAndFlangesUsingOwnEngine() {
        val predictions=System.getenv("ASSETWRIGHT_INTERFACE_PREDICTIONS")
            ?.takeIf { it.isNotBlank() } ?: return
        val destination=System.getenv("ASSETWRIGHT_INTERFACE_RECON")
            ?.takeIf { it.isNotBlank() } ?: return
        val rows=Files.readAllLines(Path.of(predictions))
        assertTrue("Expected 120 new predicted interface cases",rows.size==120)
        val root=Path.of(destination)
        Files.createDirectories(root)
        for (line in rows) {
            val fields=line.split("\t")
            assertTrue("Malformed interface reconstruction instruction",
                fields.size==3)
            val stem=fields[0]
            assertTrue("Train partition cannot leak into forward audit",
                stem.startsWith("validation__") ||
                stem.startsWith("aspect_shift__"))
            val controls=fields[1].split(",").map { it.toFloat() }
            val dimensions=fields[2].split(",").map { it.toFloat() }
            assertTrue(controls.size==3 && dimensions.size==3)
            val shell=NativeInterfaceLab.generate(NativeInterfaceSpec(
                dimensions[0],dimensions[1],dimensions[2],
                controls[0],controls[1],controls[2]))
            val asset=GeneratedAsset(VehicleSpec(
                "Student-generated native interface",4f,2f,1.4f,
                1.7f,.5f,1f,"Mobile","original source-controlled interface"),
                listOf(shell))
            val bytes=GlbWriter.encode(asset)
            val sha=MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            Files.write(root.resolve(stem+".glb"),bytes)
            Files.write(root.resolve(stem+".sha256"),sha.toByteArray(Charsets.UTF_8))
        }
    }
}
