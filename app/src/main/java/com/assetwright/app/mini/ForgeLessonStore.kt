package com.assetwright.app.mini

import android.content.Context
import android.util.AtomicFile
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/** Opt-in lesson downloads from the exact, public Assetwright-owned GitHub path. */
object ForgeLessonStore {
    const val SCHEMA = "assetwright-forge-lessons-v1"
    private const val FILE = "forge_lessons_v1.json"
    private const val PREF = "forge_lesson_update_preferences"
    private const val ENABLED = "updates_enabled"
    private const val WORK = "assetwright-forge-lesson-updates"
    private const val NOW = "assetwright-forge-lesson-fetch-once"
    private const val MAX_BYTES = 150_000
    private const val URL_STRING =
        "https://raw.githubusercontent.com/tpylman90-ctrl/Assetwright/main/app/src/main/assets/mini_ai/forge_lessons.json"

    fun enabled(context: Context): Boolean =
        context.getSharedPreferences(PREF, Context.MODE_PRIVATE).getBoolean(ENABLED, false)

    fun setEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit()
            .putBoolean(ENABLED, enabled).apply()
        if (enabled) {
            schedule(context)
            checkNow(context)
        } else {
            WorkManager.getInstance(context).cancelUniqueWork(WORK)
            WorkManager.getInstance(context).cancelUniqueWork(NOW)
        }
    }

    private fun file(context: Context) = AtomicFile(File(context.filesDir, FILE))

    private fun validate(text: String): Pair<Int, List<TrainingExample>> {
        require(text.length in 2..MAX_BYTES)
        val root = JSONObject(text)
        require(root.getString("schema") == SCHEMA)
        require(root.getString("model_type") == "reviewed-shape-lessons")
        val version = root.getInt("version")
        require(version in 1..1_000_000)
        val records = root.getJSONArray("lessons")
        require(records.length() in 1..200)
        val seen = mutableSetOf<String>()
        val parsed = (0 until records.length()).map { index ->
            val row = records.getJSONObject(index)
            val prompt = row.getString("prompt").trim()
            require(prompt.length in 5..1000 && MiniAi.supports(prompt))
            require(seen.add(prompt.lowercase())) { "Duplicate lesson prompt" }
            val obj = row.getJSONObject("parameters")
            fun bounded(name: String, a: Float, b: Float): Float {
                val value = obj.getDouble(name).toFloat()
                require(value.isFinite() && value in a..b)
                return value
            }
            TrainingExample(
                prompt, bounded("length", 3.4f, 7f),
                bounded("width", 1.45f, 3.2f),
                bounded("roofHeight", 1.05f, 2.3f),
                bounded("canopyLength", .85f, 3.1f),
                bounded("noseTaper", .25f, .9f),
                bounded("rearHaunch", .9f, 1.3f)
            )
        }
        return version to parsed
    }

    fun lessons(context: Context): List<TrainingExample> {
        val store = file(context)
        if (!store.baseFile.exists()) return emptyList()
        return try {
            validate(store.openRead().bufferedReader().use { it.readText() }).second
        } catch (_: Exception) { emptyList() }
    }

    fun version(context: Context): Int {
        val store = file(context)
        if (!store.baseFile.exists()) return 0
        return try {
            validate(store.openRead().bufferedReader().use { it.readText() }).first
        } catch (_: Exception) { 0 }
    }

    /** Downloads public data only; no user prompts, models, or secrets go out. */
    fun refresh(context: Context): Boolean {
        if (!enabled(context)) return false
        val conn = URL(URL_STRING).openConnection() as HttpURLConnection
        conn.connectTimeout = 12000
        conn.readTimeout = 12000
        conn.instanceFollowRedirects = false
        conn.requestMethod = "GET"
        try {
            require(conn.responseCode == 200) { "Forge lesson download failed" }
            val buffer = ByteArray(4096)
            val output = ByteArrayOutputStream()
            conn.inputStream.use { stream ->
                while (true) {
                    val count = stream.read(buffer)
                    if (count == -1) break
                    output.write(buffer, 0, count)
                    require(output.size() <= MAX_BYTES) { "Forge lesson feed too large" }
                }
            }
            val text = output.toString(Charsets.UTF_8.name())
            val newVersion = validate(text).first
            if (newVersion <= version(context)) return false
            val store = file(context)
            val writer = store.startWrite()
            try {
                writer.write(text.toByteArray(Charsets.UTF_8))
                store.finishWrite(writer)
            } catch (error: Exception) {
                store.failWrite(writer)
                throw error
            }
            return true
        } finally {
            conn.disconnect()
        }
    }

    fun schedule(context: Context) {
        if (!enabled(context)) return
        val req = PeriodicWorkRequestBuilder<ForgeLessonWorker>(12, TimeUnit.HOURS)
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            WORK, ExistingPeriodicWorkPolicy.KEEP, req)
    }

    fun checkNow(context: Context) {
        if (!enabled(context)) return
        val req = OneTimeWorkRequestBuilder<ForgeLessonWorker>()
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            NOW, ExistingWorkPolicy.REPLACE, req)
    }
}

class ForgeLessonWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        if (!ForgeLessonStore.enabled(applicationContext)) return Result.success()
        return try {
            if (ForgeLessonStore.refresh(applicationContext))
                DeviceShapeTrainer.schedule(applicationContext)
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
