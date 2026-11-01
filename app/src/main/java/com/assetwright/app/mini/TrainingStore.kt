package com.assetwright.app.mini

import android.content.Context
import org.json.JSONArray

object TrainingStore {
    /**
     * Bundled examples are original, parameter-labeled synthetic designs.
     * They are not external GLBs and do not imply we have learned topology.
     */
    fun bundled(context: Context): List<TrainingExample> {
        val source = context.assets.open("mini_ai/training_examples.json")
            .bufferedReader().use { it.readText() }
        val array = JSONArray(source)
        return (0 until array.length()).map { index ->
            val item = array.getJSONObject(index)
            TrainingExample(
                prompt = item.getString("prompt"),
                length = item.getDouble("length").toFloat(),
                width = item.getDouble("width").toFloat(),
                roofHeight = item.getDouble("roofHeight").toFloat(),
                canopyLength = item.getDouble("canopyLength").toFloat(),
                noseTaper = item.getDouble("noseTaper").toFloat(),
                rearHaunch = item.getDouble("rearHaunch").toFloat()
            )
        }
    }
}
