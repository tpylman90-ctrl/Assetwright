package com.assetwright.app.mini

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Small trainable model built entirely in Kotlin. Trains a regularized
 * text-feature -> shape-residual regressor, not a 3D diffusion network.
 *
 * The checkpoint contains ~1 KB of numeric weights rather than GLB meshes.
 * Training uses only explicit user-approved examples, and is reproduced
 * locally after every approval. Model updates are quality-gated.
 */
object AdaptiveShapeModel {
    const val SCHEMA = "assetwright-adaptive-shape-v1"
    private const val FILE = "adaptive_shape_v1.json"
    private const val FEATURES = 40
    private const val OUTPUTS = 6
    private const val EPOCHS = 70
    private val norms = floatArrayOf(3.6f, 1.75f, 1.25f, 2.25f, .65f, .40f)
    private val keywords = listOf(
        "wide", "narrow", "long", "short", "compact", "tall", "low",
        "panoramic", "canopy", "cockpit", "luxury", "suv", "racer",
        "coupe", "speedster", "nose", "front", "rear", "haunch",
        "armored", "aerodynamic", "swept", "muscular", "sharp",
        "rugged", "futuristic", "heavy", "slender", "body", "pointed",
        "extended", "passenger", "sport", "hidden", "repulsor", "roof",
        "fast", "aggressive", "frame"
    )
    // The intercept is feature 0; the other 39 dimensions are fixed,
    // transparent word-presence features, not a hidden text embedding.
    private fun features(prompt: String): FloatArray {
        val result = FloatArray(FEATURES)
        result[0] = .38f
        val words = Regex("[a-z]+").findAll(prompt.lowercase())
            .map { it.value }.toSet()
        val normalized = words.map { word ->
            when(word) {
                "broad", "wider" -> "wide"
                "longer", "elongated" -> "long"
                "shorter" -> "short"
                "slim", "slender" -> "narrow"
                "greenhouse", "windshield" -> "canopy"
                "racing", "sporty" -> "racer"
                "haunches", "fenders" -> "haunch"
                "hoover" -> "hover"
                else -> word
            }
        }.toSet()
        for (i in keywords.indices) if (keywords[i] in normalized) result[i + 1] = 1f
        return result
    }
    private fun values(ex: TrainingExample) = floatArrayOf(
        ex.length, ex.width, ex.roofHeight,
        ex.canopyLength, ex.noseTaper, ex.rearHaunch
    )
    private fun values(spec: VehicleSpec) = floatArrayOf(
        spec.length, spec.width, spec.roofHeight,
        spec.canopyLength, spec.noseTaper, spec.rearHaunch
    )
    private fun file(context: Context) = AtomicFile(File(context.filesDir, FILE))

    data class Snapshot(val weights: FloatArray, val trainedCount: Int, val meanError: Float)

    fun read(context: Context): Snapshot? {
        val store = file(context)
        if (!store.baseFile.exists()) return null
        return try {
            val json = JSONObject(store.openRead().bufferedReader().use { it.readText() })
            require(json.getString("schema") == SCHEMA)
            val raw = json.getJSONArray("weights")
            require(raw.length() == FEATURES * OUTPUTS)
            val weights = FloatArray(raw.length()) { raw.getDouble(it).toFloat() }
            require(weights.all { it.isFinite() && abs(it) <= 3f })
            val count = json.getInt("trainedCount")
            require(count in 1..500)
            Snapshot(weights, count, json.getDouble("meanError").toFloat())
        } catch (_: Exception) { null }
    }

    fun save(context: Context, snapshot: Snapshot) {
        val array = JSONArray()
        for (weight in snapshot.weights) array.put(weight.toDouble())
        val json = JSONObject().put("schema", SCHEMA)
            .put("trainedCount", snapshot.trainedCount)
            .put("meanError", snapshot.meanError.toDouble())
            .put("weights", array)
        val store = file(context)
        val out = store.startWrite()
        try {
            out.write(json.toString().toByteArray(Charsets.UTF_8))
            store.finishWrite(out)
        } catch (error: Exception) {
            store.failWrite(out)
            throw error
        }
    }

    /** Shape features contain semantic operations, not any mesh vertex data. */
    fun predict(base: VehicleSpec, snapshot: Snapshot?): VehicleSpec {
        if (snapshot == null) return base
        val x = features(base.sourcePrompt)
        val values = values(base)
        for (o in 0 until OUTPUTS) {
            var delta = 0f
            for (i in 0 until FEATURES) delta += snapshot.weights[o * FEATURES + i] * x[i]
            values[o] += delta.coerceIn(-.28f, .28f) * norms[o]
        }
        return base.copy(
            length = values[0].coerceIn(3.4f, 7f),
            width = values[1].coerceIn(1.45f, 3.2f),
            roofHeight = values[2].coerceIn(1.05f, 2.3f),
            canopyLength = values[3].coerceIn(.85f, 3.1f),
            noseTaper = values[4].coerceIn(.25f, .9f),
            rearHaunch = values[5].coerceIn(.9f, 1.3f)
        )
    }

    /**
     * Refit supervised residual weights against the fixed seed+Forge model,
     * using approved (prompt, shape) examples. No GLBs are stored or trained.
     * The baseline seed set is independent of user corrections to avoid
     * training on already-perfect exact-match nearest-neighbor outputs.
     */
    fun fit(
        approved: List<TrainingExample>,
        seedAndForge: List<TrainingExample>
    ): Snapshot? {
        if (approved.isEmpty()) return null
        val data = approved.takeLast(500)
        data class Point(val x: FloatArray, val delta: FloatArray)
        val points = data.map { example ->
            val baseline = MiniAi.predict(example.prompt, "Mobile", seedAndForge)
            val a = values(example)
            val b = values(baseline)
            Point(features(example.prompt), FloatArray(OUTPUTS) {
                ((a[it] - b[it]) / norms[it]).coerceIn(-.5f, .5f)
            })
        }
        fun mse(weights: FloatArray, rows: List<Point>): Float {
            if (rows.isEmpty()) return 0f
            var error = 0f
            for (point in rows) for (o in 0 until OUTPUTS) {
                var prediction = 0f
                for (i in 0 until FEATURES) prediction +=
                    weights[o * FEATURES + i] * point.x[i]
                val d = prediction - point.delta[o]
                error += d*d
            }
            return error / (rows.size * OUTPUTS)
        }
        // Hold out every fifth example only when the user has enough feedback.
        val train = points.filterIndexed { index, _ -> points.size < 10 || index % 5 != 0 }
        val test = if (points.size >= 10)
            points.filterIndexed { index, _ -> index % 5 == 0 }
            else points
        val weights = FloatArray(FEATURES * OUTPUTS)
        for (epoch in 0 until EPOCHS) {
            val lr = .075f / (1f + epoch * .032f)
            for (point in train) {
                for (o in 0 until OUTPUTS) {
                    val offset = o * FEATURES
                    var pred = 0f
                    for (i in 0 until FEATURES) pred += weights[offset + i] * point.x[i]
                    val error = (pred - point.delta[o]).coerceIn(-.7f, .7f)
                    for (i in 0 until FEATURES) if (point.x[i] != 0f)
                        weights[offset + i] -= lr *
                            (error * point.x[i] + .018f * weights[offset + i])
                }
            }
        }
        val after = mse(weights, test)
        val before = mse(FloatArray(weights.size), test)
        // Do not deploy a learned regressor that worsens held-out corrections.
        if (after > before + .00001f) return null
        return Snapshot(weights, data.size, sqrt(after))
    }
}
