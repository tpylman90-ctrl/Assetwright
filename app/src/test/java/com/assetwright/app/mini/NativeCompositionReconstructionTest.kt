package com.assetwright.app.mini

import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest

/**
 * Follow-up only: reconstruct unseen target shapes from a student-predicted
 * operation/strength TSV, never from original target plan metadata.
 * Does not execute unless the preceding inverse-learning gate passed.
 */
class NativeCompositionReconstructionTest {
    @Test
    fun exportPredictedProgramsWithOwnKotlinGenerator() {
        val predictionPath=System.getenv("ASSETWRIGHT_COMPOSED_PREDICTIONS")
            ?.takeIf { it.isNotBlank() } ?: return
        val output=System.getenv("ASSETWRIGHT_COMPOSED_RECON")
            ?.takeIf { it.isNotBlank() } ?: return
        val root=Path.of(output)
        Files.createDirectories(root)
        val lines=Files.readAllLines(Path.of(predictionPath))
        assertTrue("Expected 320 original heldout predicted programs",lines.size==320)
        for(line in lines) {
            val parts=line.split("\t")
            assertTrue("Malformed predicted construction",parts.size==4)
            val stem=parts[0]
            assertTrue("Training source cannot be reconstructed as holdout",
                stem.startsWith("validation__") || stem.startsWith("aspect_shift__"))
            val names=parts[1].split(",")
            val strengths=parts[2].split(",").map { it.toFloat() }
            val dimensions=parts[3].split(",").map { it.toFloat() }
            assertTrue(names.size==3 && strengths.size==3 && dimensions.size==3)
            val commands=names.mapIndexed { i,name ->
                NativeCompositionCommand(AdvancedFormOperation.valueOf(name),
                    strengths[i])
            }
            val shell=NativeCompositionLab.generate(NativeCompositionSpec(
                dimensions[0],dimensions[1],dimensions[2],commands))
            val carrier=VehicleSpec("Reconstructed connected form",4f,2f,
                1.4f,1.7f,.5f,1f,"Mobile","native student reconstruction")
            val raw=GlbWriter.encode(GeneratedAsset(carrier,listOf(shell)))
            val sha=MessageDigest.getInstance("SHA-256").digest(raw)
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            Files.write(root.resolve(stem+".glb"),raw)
            Files.write(root.resolve(stem+".sha256"),sha.toByteArray(Charsets.UTF_8))
        }
    }
}
