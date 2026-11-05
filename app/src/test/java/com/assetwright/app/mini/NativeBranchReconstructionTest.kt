package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/** Rebuilds unfamiliar native branch targets from the OWN student's commands. */
class NativeBranchReconstructionTest {
    @Test
    fun rebuild160HeldoutBranchesFromStudentCommands() {
        val input=System.getenv("ASSETWRIGHT_BRANCH_PREDICTIONS")
            ?.takeIf { it.isNotBlank() } ?: return
        val output=System.getenv("ASSETWRIGHT_BRANCH_RECON")
            ?.takeIf { it.isNotBlank() } ?: return
        val commands=Files.readAllLines(Path.of(input))
        assertEquals("Exactly 160 source-disjoint student instructions",160,commands.size)
        val root=Path.of(output)
        Files.createDirectories(root)
        for(line in commands) {
            val chunks=line.split("\t")
            assertEquals("Target ID, site, three strengths, dimensions",4,chunks.size)
            val stem=chunks[0]
            assertTrue("Training examples must not leak into reconstruction",
                stem.startsWith("validation__")||stem.startsWith("aspect_shift__"))
            val site=chunks[1].toInt()
            val strengths=chunks[2].split(",").map { it.toFloat() }
            val dimensions=chunks[3].split(",").map { it.toFloat() }
            assertEquals(3,strengths.size)
            assertEquals(3,dimensions.size)
            val mesh=NativeBranchLab.generate(NativeBranchSpec(
                dimensions[0],dimensions[1],dimensions[2],site,
                strengths[0],strengths[1],strengths[2]))
            val carrier=VehicleSpec("Student-directed native blind socket",4f,
                2f,1.4f,1.7f,.5f,1f,"Mobile","research-only source reconstruction")
            val bytes=GlbWriter.encode(GeneratedAsset(carrier,listOf(mesh)))
            val sha=MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            Files.write(root.resolve(stem+".glb"),bytes)
            Files.write(root.resolve(stem+".sha256"),sha.toByteArray(Charsets.UTF_8))
        }
    }
}
