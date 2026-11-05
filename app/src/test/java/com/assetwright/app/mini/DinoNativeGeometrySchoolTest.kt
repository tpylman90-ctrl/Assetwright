package com.assetwright.app.mini

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.math.roundToInt

/**
 * Research-only real native geometry for DINO visual-to-construction school.
 * Original Kotlin vertices and triangles are the ONLY construction target.
 * No pretrained model, external CAD program or image encoder runs here.
 */
class DinoNativeGeometrySchoolTest {
    private data class Dimensions(val length: Float, val width: Float, val height: Float)
    private data class Family(val name: String, val dims: Dimensions)

    private val training = listOf(
        Family("dntrain01", Dimensions(2.80f,1.42f,.95f)),
        Family("dntrain02", Dimensions(4.40f,2.20f,1.30f)),
        Family("dntrain03", Dimensions(5.50f,1.70f,1.65f)),
        Family("dntrain04", Dimensions(3.40f,2.80f,2.10f)),
        Family("dntrain05", Dimensions(6.25f,2.25f,.80f)),
        Family("dntrain06", Dimensions(3.15f,1.65f,2.55f))
    )
    private val development = listOf(
        Family("dndev01", Dimensions(3.83f,1.35f,1.60f)),
        Family("dndev02", Dimensions(5.12f,2.60f,1.02f))
    )
    private val validation = listOf(
        Family("dnblind01", Dimensions(2.73f,2.05f,1.82f)),
        Family("dnblind02", Dimensions(6.08f,2.47f,1.95f))
    )
    private val trainLevels = listOf(.12f,.30f,.50f,.70f,.90f)
    private val devLevels = listOf(.22f,.46f,.78f)
    private val blindLevels = listOf(.19f,.56f,.84f)

    private fun sha256(raw: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(raw).joinToString("") {
            "%02x".format(it.toInt() and 255)
        }

    private fun export(
        root: Path, split: String, family: Family, operation: AdvancedFormOperation,
        strength: Float
    ) {
        val d = family.dims
        val shell = AdvancedFormLab.generate(AdvancedFormSpec(
            operation,d.length,d.width,d.height,strength
        ))
        assertTrue("Native source must contain actual triangles",shell.indices.size/3 in 900..3000)
        val vehicle = VehicleSpec(
            "Original native visual school",4f,2f,1.4f,
            1.7f,.5f,1f,"Mobile","research-only owned source geometry")
        val bytes = GlbWriter.encode(GeneratedAsset(vehicle,listOf(shell)))
        val digest = sha256(bytes)
        val level = "s" + (strength*1000).roundToInt().toString().padStart(3,'0')
        val stem = "$"+"{split}__$"+"{family.name}__$"+"{operation.name.lowercase()}__$"+"{level}"
        Files.write(root.resolve("$"+"{stem}.glb"),bytes)
        val metadata = """
            {
              "schema":"assetwright-dino-native-school-v1",
              "native_generator":"AssetWright-AdvancedFormLab",
              "case":"$"+"{stem}",
              "split":"$"+"{split}",
              "family":"$"+"{family.name}",
              "operation":"$"+"{operation.name}",
              "strength":$"+"{strength}",
              "length":$"+"{d.length}",
              "width":$"+"{d.width}",
              "height":$"+"{d.height}",
              "source_glb_sha256":"$"+"{digest}"
            }
        """.trimIndent()
        Files.write(root.resolve("$"+"{stem}.json"),metadata.toByteArray(StandardCharsets.UTF_8))
    }

    @Test
    fun exportOriginalMultifamilyDinoVisualSchool() {
        val target = System.getenv("ASSETWRIGHT_DINO_NATIVE_SOURCE")
            ?.takeIf { it.isNotBlank() } ?: return
        val root = Path.of(target)
        Files.createDirectories(root)
        val plans = listOf(
            Triple("train",training,trainLevels),
            Triple("development",development,devLevels),
            Triple("validation",validation,blindLevels)
        )
        var exported=0
        for ((split,families,levels) in plans)
            for (family in families)
                for (operation in AdvancedFormOperation.values())
                    for (strength in levels) {
                        export(root,split,family,operation,strength)
                        exported++
                    }
        assertEquals(252,exported)
        assertEquals(exported,Files.list(root).use { stream ->
            stream.filter { it.fileName.toString().endsWith(".glb") }.count().toInt()
        })
    }
}
