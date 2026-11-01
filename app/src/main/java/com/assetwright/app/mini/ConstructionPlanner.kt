package com.assetwright.app.mini

import kotlin.math.ln

/**
 * Supervised, offline semantic layout classifier trained on original,
 * reviewed prompt -> part-role labels. It does NOT infer joints from raw
 * third-party meshes. Safe explicit number requests override predictions.
 */
data class ConstructionLabel(val prompt: String, val liftCells: Int, val mount: String)
data class ConstructionPlan(val liftCells: Int, val mount: String) {
    init {
        require(liftCells in setOf(2, 4, 6))
        require(mount in setOf("tucked", "exposed"))
    }
}
data class ConstructionModel(
    val examples: Int,
    val tokens: Map<String, IntArray>,
    val classCounts: IntArray,
    val dictionarySize: Int
)

object ConstructionPlanner {
    private val ignored = setOf(
        "a", "an", "the", "of", "in", "my", "your", "with", "for", "make",
        "build", "create", "and", "car", "hover", "hoover", "vehicle",
        "craft", "suv", "racer", "coupe", "speedster"
    )
    private val wordMap = mapOf(
        "repulsor" to "lift", "repulsors" to "lift",
        "hovercell" to "lift", "hovercells" to "lift",
        "pads" to "pad", "pods" to "pod",
        "cells" to "cell", "units" to "unit",
        "concealed" to "hidden", "recessed" to "hidden",
        "integrated" to "hidden", "underbody" to "hidden",
        "visible" to "exposed", "external" to "exposed",
        "outboard" to "exposed", "outrigger" to "exposed",
        "outriggers" to "exposed",
        "minimal" to "small", "lightweight" to "small",
        "many" to "multiple", "lots" to "multiple"
    )
    private fun tokens(prompt: String): Set<String> =
        Regex("[a-z0-9]+").findAll(prompt.lowercase())
            .map { wordMap[it.value] ?: it.value }
            .filter { it !in ignored }
            .toSet()

    private fun labelIndex(x: ConstructionLabel): Int =
        listOf(2, 4, 6).indexOf(x.liftCells) * 2 +
            if (x.mount == "exposed") 1 else 0

    /** Laplace-smoothed multinomial Naive Bayes, trained on device. */
    fun train(examples: List<ConstructionLabel>): ConstructionModel {
        require(examples.size in 12..500)
        val counts = IntArray(6)
        val vocab = mutableMapOf<String, IntArray>()
        for (ex in examples) {
            require(ex.prompt.length in 6..240)
            require(ex.mount in setOf("tucked", "exposed") && ex.liftCells in setOf(2, 4, 6))
            val label = labelIndex(ex)
            counts[label]++
            for (token in tokens(ex.prompt)) {
                vocab.getOrPut(token) { IntArray(6) }[label]++
            }
        }
        require(counts.all { it >= 2 }) { "Each construction class needs >=2 examples" }
        return ConstructionModel(examples.size, vocab, counts, vocab.size)
    }

    private fun infer(model: ConstructionModel, prompt: String): ConstructionPlan {
        val words = tokens(prompt).filter { it in model.tokens }
        val totals = IntArray(6) { label ->
            model.tokens.values.sumOf { it[label] }
        }
        val score = DoubleArray(6) { label ->
            ln((model.classCounts[label] + 1.0) / (model.examples + 6.0)) +
                words.sumOf { token ->
                    ln((model.tokens.getValue(token)[label] + 1.0) /
                        (totals[label] + model.dictionarySize.toDouble()))
                }
        }
        val winner = score.indices.maxByOrNull { score[it] } ?: 2
        return ConstructionPlan(listOf(2, 4, 6)[winner / 2],
            if (winner % 2 == 0) "tucked" else "exposed")
    }

    private val explicitLift = Regex(
        "\\b(2|4|6|two|four|six|twin|dual)\\s*" +
            "(?:(?:underbody|underslung|hover|lift|magnetic|anti\\s*gravity)\\s+)*" +
            "(?:repulsors?|pods?|pads?|cells?|units?)\\b",
        RegexOption.IGNORE_CASE
    )
    private val reverseLift = Regex(
        "\\b(?:repulsors?|lift\\s+pods?|hover\\s+pads?)\\s*(?:x\\s*|:\\s*)?(2|4|6)\\b",
        RegexOption.IGNORE_CASE
    )

    fun plan(prompt: String, model: ConstructionModel?): ConstructionPlan {
        val trained = model?.let { infer(it, prompt) } ?: ConstructionPlan(4, "tucked")
        val exact = explicitLift.find(prompt)?.groupValues?.get(1)
            ?: reverseLift.find(prompt)?.groupValues?.get(1)
        val count = when(exact?.lowercase()) {
            "2", "two", "twin", "dual" -> 2
            "4", "four" -> 4
            "6", "six" -> 6
            else -> trained.liftCells
        }
        val normalized = tokens(prompt)
        // Explicit preferences are never overridden by statistical training.
        val mount = when {
            "hidden" in normalized || "tucked" in normalized -> "tucked"
            "exposed" in normalized -> "exposed"
            else -> trained.mount
        }
        return ConstructionPlan(count, mount)
    }

    fun evaluate(model: ConstructionModel, heldOut: List<ConstructionLabel>): Pair<Double, Double> {
        require(heldOut.isNotEmpty())
        val countCorrect = heldOut.count { plan(it.prompt, model).liftCells == it.liftCells }
        val mountCorrect = heldOut.count { plan(it.prompt, model).mount == it.mount }
        return countCorrect.toDouble() / heldOut.size to
            mountCorrect.toDouble() / heldOut.size
    }
}
