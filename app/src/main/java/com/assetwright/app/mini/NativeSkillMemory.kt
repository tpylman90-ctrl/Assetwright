package com.assetwright.app.mini

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.math.sqrt

/**
 * Forge Mini's FIRST persistent native-operation learning memory.
 *
 * A reviewed lesson changes subsequent geometry LAB generation, not merely
 * a research score. All sources are the user's explicitly approved native
 * operations; downloaded DINO research weights NEVER bypass review.
 * This memory is independent of vehicle proportion correction memory.
 */
object NativeSkillMemory {
    private const val SCHEMA = "assetwright-mini-native-skill-memory-v1"
    private const val FILE = "forge_mini_native_skills_v1.json"
    private const val LIMIT = 180
    private val ignored = setOf("a", "an", "the", "with", "for", "my", "make",
        "build", "create", "some", "and", "of", "a", "model", "shape", "asset")

    data class Lesson(val prompt: String, val operation: AdvancedFormOperation,
                      val strength: Float)
    data class Prediction(val operation: AdvancedFormOperation, val strength: Float,
                          val origin: String, val similarity: Float)

    fun tokens(prompt: String): Set<String> =
        Regex("[a-z0-9]+").findAll(prompt.lowercase()).map { it.value }
            .filter { it !in ignored }.toSet()

    /**
     * When no reviewed lesson matches, use transparent geometry vocabulary.
     * These are REAL existing Kotlin operations, not claims of DINO learning.
     */
    fun propose(prompt: String, approved: List<Lesson>): Prediction {
        val normalized = prompt.trim()
        val exact = approved.asReversed().firstOrNull {
            it.prompt.trim().equals(normalized, ignoreCase = true)
        }
        if (exact != null)
            return Prediction(exact.operation, exact.strength, "approved exact lesson", 1f)

        val words = tokens(prompt)
        val ranked = approved.map { lesson ->
            val sample = tokens(lesson.prompt)
            val overlap = sample.intersect(words).size.toFloat()
            val similarity = if (overlap == 0f || words.isEmpty() || sample.isEmpty()) 0f
                else overlap / sqrt((sample.size * words.size).toFloat())
            lesson to similarity
        }.sortedByDescending { it.second }
        val closest = ranked.firstOrNull()
        if (closest != null && closest.second >= .55f)
            return Prediction(closest.first.operation, closest.first.strength,
                "approved similar lesson", closest.second)

        val choice = when {
            words.any { it in setOf("twist", "twisted", "torsion", "spiral", "helical") } ->
                AdvancedFormOperation.SECTION_TWIST
            words.any { it in setOf("curved", "sweep", "swept", "bent", "bend") } ->
                AdvancedFormOperation.TANGENT_SWEEP
            words.any { it in setOf("recess", "groove", "channel", "undercut", "inset") } ->
                AdvancedFormOperation.LOWER_RECESS
            words.any { it in setOf("ribs", "ribbed", "corrugated", "fluted", "ridged") } ->
                AdvancedFormOperation.RIBBED_FAIRING
            words.any { it in setOf("square", "squared", "boxy", "angular", "rounded") } ->
                AdvancedFormOperation.SUPERELLIPSE_PROFILE
            else -> AdvancedFormOperation.SECTION_LOFT
        }
        val power = when {
            words.any { it in setOf("subtle", "slight", "mild", "gentle") } -> .24f
            words.any { it in setOf("dramatic", "deep", "strong", "extreme", "large") } -> .82f
            else -> .53f
        }
        return Prediction(choice, power, "native operation vocabulary", 0f)
    }

    private fun destination(context: Context) =
        AtomicFile(File(context.filesDir, FILE))

    private fun readVerified(context: Context): List<Lesson> {
        val file = destination(context)
        if (!file.baseFile.exists()) return emptyList()
        val root = JSONObject(file.openRead().bufferedReader().use { it.readText() })
        require(root.getString("schema") == SCHEMA)
        val rows = root.getJSONArray("lessons")
        require(rows.length() <= LIMIT)
        val parsed = (0 until rows.length()).map { index ->
            val item = rows.getJSONObject(index)
            val example = Lesson(item.getString("prompt"),
                AdvancedFormOperation.valueOf(item.getString("operation")),
                item.getDouble("strength").toFloat())
            validate(example)
            example
        }
        require(root.getInt("count") == parsed.size) {
            "Existing native skill memory count mismatch"
        }
        require(parsed.map { it.prompt.lowercase() }.toSet().size == parsed.size) {
            "Existing native skills contain duplicate approved prompts"
        }
        return parsed
    }

    @Synchronized
    fun lessons(context: Context): List<Lesson> = try {
        readVerified(context)
    } catch (_: Exception) {
        // Bad local data must never be silently deleted or promoted.
        emptyList()
    }

    fun infer(context: Context, prompt: String): Prediction =
        propose(prompt, lessons(context))

    private fun validate(item: Lesson) {
        require(item.prompt.isNotBlank() && item.prompt.length <= 1000)
        require(item.strength.isFinite() && item.strength in 0f..1f)
    }

    /** Persist a single inspected lesson with atomic replacement. */
    @Synchronized
    fun approve(context: Context, prompt: String, operation: AdvancedFormOperation,
                strength: Float): Int {
        val next = Lesson(prompt.trim(), operation, strength)
        validate(next)
        val memory = readVerified(context).toMutableList()
        memory.removeAll { it.prompt.trim().equals(next.prompt, ignoreCase = true) }
        memory.add(next)
        while (memory.size > LIMIT) memory.removeAt(0)
        val array = JSONArray()
        for (item in memory) {
            array.put(JSONObject().put("prompt", item.prompt)
                .put("operation", item.operation.name)
                .put("strength", item.strength.toDouble()))
        }
        val payload = JSONObject().put("schema", SCHEMA)
            .put("count", memory.size).put("lessons", array)
        val store = destination(context)
        val stream = store.startWrite()
        try {
            stream.write(payload.toString().toByteArray(Charsets.UTF_8))
            store.finishWrite(stream)
        } catch (error: Exception) {
            store.failWrite(stream)
            throw error
        }
        return memory.size
    }

    /** Give the user an explicit way to delete locally learned native lessons. */
    @Synchronized
    fun clear(context: Context) {
        destination(context).delete()
    }

    fun generate(prompt: String, operation: AdvancedFormOperation, strength: Float,
                 length: Float = 4.8f, width: Float = 2.1f,
                 height: Float = 1.5f): GeneratedAsset {
        require(prompt.isNotBlank() && prompt.length <= 1000)
        val spec = VehicleSpec(
            title = "Forge Mini native form · " + operation.name.replace('_', ' '),
            length = length, width = width, roofHeight = height,
            canopyLength = 1.8f, noseTaper = .55f, rearHaunch = 1.07f,
            quality = "Mobile", sourcePrompt = prompt)
        val native = AdvancedFormLab.generate(
            AdvancedFormSpec(operation, length, width, height, strength))
        return GeneratedAsset(spec, listOf(native))
    }
}
