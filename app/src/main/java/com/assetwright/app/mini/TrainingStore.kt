package com.assetwright.app.mini

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.charset.StandardCharsets

/**
 * A private, opt-in learning memory. A corrected vehicle is admitted only
 * when the user explicitly taps "Teach Mini AI". New examples work offline
 * immediately through the existing nearest-neighbor prediction algorithm.
 */
object TrainingStore {
    private const val FILE_NAME = "approved_mini_ai_v1.json"
    private const val HOME_FILE = "home_mini_ai_pack_v1.json"
    private const val MAX_EXAMPLES = 500

    fun bundled(context: Context): List<TrainingExample> {
        val source = context.assets.open("mini_ai/training_examples.json")
            .bufferedReader().use { it.readText() }
        return parseExamples(JSONArray(source))
    }

    fun approved(context: Context): List<TrainingExample> {
        val file = File(context.filesDir, FILE_NAME)
        if (!file.exists()) return emptyList()
        val source = AtomicFile(file).openRead().bufferedReader().use { it.readText() }
        return parseExamples(JSONArray(source))
    }

    /** Most recent local corrections win, then home-trained examples, then seeds. */
    fun trainingSet(context: Context): List<TrainingExample> =
        approved(context).asReversed() + home(context).asReversed() + bundled(context)

    fun home(context: Context): List<TrainingExample> {
        val file = File(context.filesDir, HOME_FILE)
        if (!file.exists()) return emptyList()
        val data = JSONObject(AtomicFile(file).openRead().bufferedReader().use { it.readText() })
        return parseExamples(data.getJSONArray("examples"))
    }

    /**
     * Imports a locally trained and explicitly selected model pack.
     * Does not accept arbitrary GLBs or download/upload anything.
     */
    @Synchronized
    fun importHomePack(context: Context, source: String): Int {
        require(source.length in 2..350_000) { "Invalid or oversized training pack" }
        val data = JSONObject(source)
        require(data.getString("schema") == "assetwright-mini-ai-pack-v1")
        require(data.getString("model_type") == "approved-example-memory")
        val examples = parseExamples(data.getJSONArray("examples"))
        require(examples.size in 1..MAX_EXAMPLES)
        require(data.getInt("approved_count") == examples.size)
        require(examples.all { MiniAi.supports(it.prompt) })
        val file = AtomicFile(File(context.filesDir, HOME_FILE))
        val output = file.startWrite()
        try {
            output.write(source.toByteArray(StandardCharsets.UTF_8))
            file.finishWrite(output)
        } catch (error: Exception) {
            file.failWrite(output)
            throw error
        }
        return examples.size
    }

    @Synchronized
    fun approve(context: Context, spec: VehicleSpec): Int {
        require(MiniAi.supports(spec.sourcePrompt))
        require(spec.sourcePrompt.isNotBlank() && spec.sourcePrompt.length <= 1000)
        val example = TrainingExample(
            spec.sourcePrompt, spec.length, spec.width, spec.roofHeight,
            spec.canopyLength, spec.noseTaper, spec.rearHaunch
        )
        validate(example)
        val all = approved(context).toMutableList()
        // Re-approving a prompt replaces its previous correction.
        all.removeAll { it.prompt.trim().equals(example.prompt.trim(), ignoreCase = true) }
        all += example
        while (all.size > MAX_EXAMPLES) all.removeAt(0)
        val data = JSONArray()
        for (item in all) data.put(json(item))
        val file = AtomicFile(File(context.filesDir, FILE_NAME))
        val output = file.startWrite()
        try {
            output.write(data.toString().toByteArray(StandardCharsets.UTF_8))
            file.finishWrite(output)
        } catch (error: Exception) {
            file.failWrite(output)
            throw error
        }
        return all.size
    }

    /** Deliberately user-initiated backup; never uploads training data. */
    fun approvedJsonl(context: Context): String =
        approved(context).joinToString(separator = "\n", postfix = "\n") { example ->
            val record = json(example)
            record.put("schema", "assetwright-approved-example-v1")
            record.put("approved_by_user", true)
            record.put("origin", "android-corrected-vehicle")
            record.toString()
        }

    private fun parseExamples(array: JSONArray): List<TrainingExample> =
        (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            val ex = TrainingExample(
                obj.getString("prompt"),
                obj.getDouble("length").toFloat(),
                obj.getDouble("width").toFloat(),
                obj.getDouble("roofHeight").toFloat(),
                obj.getDouble("canopyLength").toFloat(),
                obj.getDouble("noseTaper").toFloat(),
                obj.getDouble("rearHaunch").toFloat()
            )
            validate(ex)
            ex
        }

    private fun validate(ex: TrainingExample) {
        require(ex.prompt.isNotBlank() && ex.prompt.length <= 1000)
        require(ex.length.isFinite() && ex.length in 3.4f..7.0f)
        require(ex.width.isFinite() && ex.width in 1.45f..3.2f)
        require(ex.roofHeight.isFinite() && ex.roofHeight in 1.05f..2.30f)
        require(ex.canopyLength.isFinite() && ex.canopyLength in 0.85f..3.1f)
        require(ex.noseTaper.isFinite() && ex.noseTaper in 0.25f..0.9f)
        require(ex.rearHaunch.isFinite() && ex.rearHaunch in 0.9f..1.3f)
    }

    private fun json(ex: TrainingExample): JSONObject {
        val spec = VehicleSpec(
            title = "Hover Vehicle", length = ex.length, width = ex.width,
            roofHeight = ex.roofHeight, canopyLength = ex.canopyLength,
            noseTaper = ex.noseTaper, rearHaunch = ex.rearHaunch,
            quality = "Mobile", sourcePrompt = ex.prompt
        )
        return JSONObject()
            .put("prompt", ex.prompt)
            .put("length", ex.length.toDouble())
            .put("width", ex.width.toDouble())
            .put("roofHeight", ex.roofHeight.toDouble())
            .put("canopyLength", ex.canopyLength.toDouble())
            .put("noseTaper", ex.noseTaper.toDouble())
            .put("rearHaunch", ex.rearHaunch.toDouble())
            .put("construction_recipe", ShapeProgram.toJson(spec))
    }
}
