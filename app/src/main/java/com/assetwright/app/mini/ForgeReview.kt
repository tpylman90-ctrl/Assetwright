package com.assetwright.app.mini

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Human-in-the-loop assistant review format. No upload or network operation:
 * users choose where to save/share their review package.
 */
data class ForgeProposal(
    val sourceSha256: String,
    val prompt: String,
    val notes: String,
    val target: VehicleSpec
)

object ForgeReview {
    const val REVIEW_SCHEMA = "assetwright-forge-review-v1"
    const val PROPOSAL_SCHEMA = "assetwright-forge-proposal-v1"
    private const val MAX_FEEDBACK = 2000
    private val fields = listOf("length", "width", "roofHeight", "canopyLength", "noseTaper", "rearHaunch")

    private fun sha256(data: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(data)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }

    private fun parameters(spec: VehicleSpec): JSONObject = JSONObject()
        .put("length", spec.length.toDouble())
        .put("width", spec.width.toDouble())
        .put("roofHeight", spec.roofHeight.toDouble())
        .put("canopyLength", spec.canopyLength.toDouble())
        .put("noseTaper", spec.noseTaper.toDouble())
        .put("rearHaunch", spec.rearHaunch.toDouble())

    fun reviewBundle(asset: GeneratedAsset, requestedChanges: String): ByteArray {
        require(requestedChanges.length <= MAX_FEEDBACK)
        val glb = GlbWriter.encode(asset)
        val spec = asset.spec
        val json = JSONObject()
            .put("schema", REVIEW_SCHEMA)
            .put("generator", "assetwright-mini-ai")
            .put("generator_version", "0.2")
            .put("prompt", spec.sourcePrompt)
            .put("profile", spec.quality)
            .put("triangle_count", asset.triangleCount)
            .put("mesh_parts", asset.parts.map { it.name })
            .put("parameters", parameters(spec))
            .put("model_sha256", sha256(glb))
            .put("requested_changes", requestedChanges)
            .put("share_approval", "user_exported_for_assistant_review")
        val out = ByteArrayOutputStream()
        ZipOutputStream(out).use { zip ->
            zip.putNextEntry(ZipEntry("review.json"))
            zip.write(json.toString(2).toByteArray(Charsets.UTF_8))
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("model.glb"))
            zip.write(glb)
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("README.txt"))
            zip.write(
                ("Assetwright Forge review bundle. You selected this export for review.\n" +
                 "Contains the generated GLB, its parameters, prompt and your comments.\n" +
                 "No model is trained or uploaded merely by creating this file.\n")
                    .toByteArray(Charsets.UTF_8)
            )
            zip.closeEntry()
        }
        return out.toByteArray()
    }

    /** Parse into a previewable proposal; do NOT admit to learning memory. */
    fun parseProposal(jsonText: String, current: GeneratedAsset): ForgeProposal {
        require(jsonText.length in 2..16000) { "Invalid or oversized correction" }
        val json = JSONObject(jsonText)
        require(json.getString("schema") == PROPOSAL_SCHEMA) { "Not a Forge proposal" }
        val currentHash = sha256(GlbWriter.encode(current))
        val sourceHash = json.getString("source_sha256")
        require(sourceHash.matches(Regex("[0-9a-f]{64}")) && currentHash == sourceHash) {
            "Correction belongs to another generated model; regenerate the reviewed model first"
        }
        val prompt = json.getString("prompt")
        require(prompt == current.spec.sourcePrompt) { "Prompt does not match this model" }
        val notes = json.getString("notes")
        require(notes.isNotBlank() && notes.length <= MAX_FEEDBACK)
        val obj = json.getJSONObject("target")
        require(obj.keySet() == fields.toSet()) { "Correction must specify exactly six geometry parameters" }
        val floats = fields.associateWith { key ->
            val number = obj.getDouble(key)
            require(number.isFinite()) { "Invalid value: " + key }
            number.toFloat()
        }
        val target = current.spec.copy(
            length = floats.getValue("length"),
            width = floats.getValue("width"),
            roofHeight = floats.getValue("roofHeight"),
            canopyLength = floats.getValue("canopyLength"),
            noseTaper = floats.getValue("noseTaper"),
            rearHaunch = floats.getValue("rearHaunch")
        )
        require(target.length in 3.4f..7f &&
            target.width in 1.45f..3.2f &&
            target.roofHeight in 1.05f..2.30f &&
            target.canopyLength in 0.85f..3.1f &&
            target.noseTaper in 0.25f..0.9f &&
            target.rearHaunch in 0.9f..1.3f) { "Corrected dimensions out of range" }
        require(target != current.spec) { "No shape parameters were changed" }
        return ForgeProposal(sourceHash, prompt, notes, target)
    }
}
