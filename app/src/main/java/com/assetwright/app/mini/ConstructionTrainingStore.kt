package com.assetwright.app.mini

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Trains the semantic planner in memory from bundled, original, labeled
 * construction examples. No external geometry, network, or user files needed.
 * Re-trains after an APK update if the approved corpus changes.
 */
object ConstructionTrainingStore {
    private var cached: ConstructionModel? = null
    private var cachedVersion = -1
    private var status: String = "Not evaluated"

    @Synchronized
    fun model(context: Context): ConstructionModel? {
        val feedVersion = ForgeLessonStore.version(context)
        if (cached != null && cachedVersion == feedVersion) return cached
        return try {
            val root = context.assets.open("mini_ai/construction_labels.json")
                .bufferedReader().use { JSONObject(it.readText()) }
            require(root.getString("schema") == "assetwright-semantic-construction-corpus-v1")
            require(root.getInt("version") >= 1)
            fun parse(items: JSONArray): List<ConstructionLabel> =
                (0 until items.length()).map { i ->
                    val ex = items.getJSONObject(i)
                    ConstructionLabel(
                        ex.getString("prompt"),
                        ex.getInt("lift_cells"),
                        ex.getString("mount")
                    )
                }
            val train = parse(root.getJSONArray("train"))
            val heldOut = parse(root.getJSONArray("heldout"))
            require(train.map { it.prompt.lowercase() }.toSet().size == train.size)
            require(heldOut.none { row ->
                train.any { it.prompt.equals(row.prompt, ignoreCase = true) }
            })
            val candidate = ConstructionPlanner.train(train)
            val (countScore, mountScore) = ConstructionPlanner.evaluate(candidate, heldOut)
            // Must exceed a constant four/tucked baseline on held-out original
            // phrasing variants before activating learned layouts.
            require(countScore >= .80 && mountScore >= .80) {
                "Planner validation failed: count=" + countScore + ", mount=" + mountScore
            }
            val remote = ForgeLessonStore.semanticLessons(context)
                .filterNot { row ->
                    (train + heldOut).any { existing ->
                        existing.prompt.equals(row.prompt, ignoreCase = true)
                    }
                }
            var chosen = candidate
            var acceptedRemote = 0
            if (remote.isNotEmpty()) {
                val combined = ConstructionPlanner.train(train + remote)
                val (newCount, newMount) = ConstructionPlanner.evaluate(combined, heldOut)
                if (newCount >= .80 && newMount >= .80 &&
                    newCount >= countScore - .02 && newMount >= mountScore - .02) {
                    chosen = combined
                    acceptedRemote = remote.size
                }
            }
            cached = chosen
            cachedVersion = feedVersion
            status = "Held-out validation " + heldOut.size + " prompts: count " +
                (countScore * 100).toInt() + "%, mount " +
                (mountScore * 100).toInt() + "%; accepted Forge construction lessons " +
                acceptedRemote
            chosen
        } catch (error: Exception) {
            status = "Conservative four-cell fallback: " +
                (error.message ?: "invalid corpus")
            null
        }
    }

    fun infer(context: Context, prompt: String): ConstructionPlan =
        ConstructionPlanner.plan(prompt, model(context))

    fun summary(context: Context): String {
        model(context)
        return status
    }
}
