package com.assetwright.app.mini

import kotlin.math.sqrt

/**
 * Assetwright Mini AI v0.1: an offline, example-based parameter predictor.
 * This is deliberately small: it learns from labeled specifications rather
 * than pretending to reconstruct arbitrary geometry from a text prompt.
 */
data class TrainingExample(
    val prompt: String,
    val length: Float,
    val width: Float,
    val roofHeight: Float,
    val canopyLength: Float,
    val noseTaper: Float,
    val rearHaunch: Float
)

data class VehicleSpec(
    val title: String,
    val length: Float,
    val width: Float,
    val roofHeight: Float,
    val canopyLength: Float,
    val noseTaper: Float,
    val rearHaunch: Float,
    val quality: String,
    val sourcePrompt: String
) {
    val radialSegments: Int get() = when (quality) {
        "High detail" -> 32
        "Balanced" -> 24
        else -> 16
    }
}

object MiniAi {
    private val ignored = setOf(
        "a", "an", "the", "with", "and", "for", "of", "some", "make", "create",
        "build", "design", "me", "my", "that", "has", "is", "on", "in", "it",
        "vehicle", "car", "hover", "hoover", "craft"
    )
    private val synonyms = mapOf(
        "broad" to "wide", "wider" to "wide", "large" to "big",
        "longer" to "long", "elongated" to "long",
        "shorter" to "short", "small" to "compact",
        "slender" to "narrow", "slim" to "narrow",
        "greenhouse" to "canopy", "windshield" to "canopy",
        "sporty" to "racer", "racing" to "racer",
        "haunches" to "haunch", "fenders" to "haunch",
        "cab" to "cockpit", "hoover" to "hover"
    )

    fun supports(prompt: String): Boolean {
        val s = tokens(prompt)
        return s.any { it in setOf("hover", "suv", "coupe", "racer", "car", "vehicle", "speedster") } ||
            prompt.contains("hoover", ignoreCase = true)
    }

    fun predict(prompt: String, quality: String, examples: List<TrainingExample>): VehicleSpec {
        require(prompt.isNotBlank()) { "Describe a vehicle first." }
        require(supports(prompt)) {
            "The offline Mini AI currently supports hover vehicles, SUVs, coupes, and racers."
        }
        val query = tokens(prompt).filterNot { it in ignored }.toSet()
        // An explicitly approved correction for the same prompt must be
        // reproduced exactly, rather than diluted by the synthetic seed set.
        val exact = examples.firstOrNull {
            it.prompt.trim().equals(prompt.trim(), ignoreCase = true)
        }
        val nearest = examples.map { example ->
            val sample = tokens(example.prompt).filterNot { it in ignored }.toSet()
            val intersection = query.intersect(sample).size.toFloat()
            val similarity = if (query.isEmpty() || sample.isEmpty()) 0f
                else intersection / sqrt((query.size * sample.size).toFloat())
            example to similarity
        }.filter { it.second > 0f }.sortedByDescending { it.second }.take(4)

        fun estimate(selector: (TrainingExample) -> Float, default: Float): Float {
            if (exact != null) return selector(exact)
            if (nearest.isEmpty()) return default
            val total = nearest.sumOf { (it.second * it.second).toDouble() }.toFloat()
            val prediction = nearest.sumOf {
                (selector(it.first) * it.second * it.second).toDouble()
            }.toFloat() / total
            // Stay close to known geometry when the prompt has few recognizable terms.
            return (0.90f * prediction + 0.10f * default)
        }

        val lower = prompt.lowercase()
        val title = when {
            "suv" in lower -> "Hover SUV"
            "coupe" in lower -> "Hover Coupe"
            "racer" in lower || "race" in lower || "speedster" in lower -> "Hover Racer"
            else -> "Hover Vehicle"
        }
        return VehicleSpec(
            title = title,
            length = estimate({ it.length }, 4.8f).coerceIn(3.4f, 7.0f),
            width = estimate({ it.width }, 2.05f).coerceIn(1.45f, 3.2f),
            roofHeight = estimate({ it.roofHeight }, 1.52f).coerceIn(1.05f, 2.30f),
            canopyLength = estimate({ it.canopyLength }, 1.8f).coerceIn(0.85f, 3.1f),
            noseTaper = estimate({ it.noseTaper }, 0.55f).coerceIn(0.25f, 0.9f),
            rearHaunch = estimate({ it.rearHaunch }, 1.07f).coerceIn(0.9f, 1.3f),
            quality = quality,
            sourcePrompt = prompt
        )
    }

    private fun tokens(input: String): List<String> =
        Regex("[a-z0-9]+").findAll(input.lowercase()).map {
            synonyms[it.value] ?: it.value
        }.toList()
}
