package com.assetwright.app.mini

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

/**
 * Explicitly paired shared-folder transport for approved example files.
 *
 * Assetwright neither runs a public server nor uploads to a cloud provider.
 * A separate local sync utility may replicate this selected folder over LAN.
 * Nothing is shared until the user selects a writable folder.
 */
object TrainingSync {
    private const val PREFS = "mini_ai_local_sync_v1"
    private const val KEY_FOLDER = "tree_uri"
    private const val KEY_PACK_HASH = "pack_hash"
    private const val SYNC_WORK = "assetwright-approved-training-import"
    private const val APPROVED_FILE = "approved-phone.jsonl"
    private const val PACK_FILE = "approved_pack.json"
    private const val MAX_PACK_BYTES = 350_000

    fun configured(context: Context): Boolean = uri(context) != null

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun uri(context: Context): Uri? = prefs(context).getString(KEY_FOLDER, null)
        ?.let(Uri::parse)

    private fun folder(context: Context): DocumentFile? =
        uri(context)?.let { DocumentFile.fromTreeUri(context, it) }
            ?.takeIf { it.canRead() && it.isDirectory }

    fun connect(context: Context, selected: Uri) {
        context.contentResolver.takePersistableUriPermission(
            selected,
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )
        val folder = DocumentFile.fromTreeUri(context, selected)
        require(folder != null && folder.isDirectory && folder.canWrite() && folder.canRead()) {
            "Select a folder with read and write permission"
        }
        prefs(context).edit().putString(KEY_FOLDER, selected.toString())
            .remove(KEY_PACK_HASH).apply()
        schedule(context)
        publishApproved(context)
    }

    fun disconnect(context: Context) {
        val old = uri(context)
        prefs(context).edit().remove(KEY_FOLDER).remove(KEY_PACK_HASH).apply()
        WorkManager.getInstance(context).cancelUniqueWork(SYNC_WORK)
        if (old != null) {
            try {
                context.contentResolver.releasePersistableUriPermission(
                    old,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                // Permission might have already been revoked in Android Settings.
            }
        }
    }

    /** Publish only user-approved prompt/parameter examples; no GLBs or images. */
    fun publishApproved(context: Context): Boolean {
        val folder = folder(context) ?: return false
        val data = TrainingStore.approvedJsonl(context).toByteArray(StandardCharsets.UTF_8)
        val destination = folder.findFile(APPROVED_FILE)
            ?: folder.createFile("application/x-ndjson", APPROVED_FILE)
            ?: error("Unable to create approved feedback file")
        require(destination.canWrite()) { "Approved feedback file is read-only" }
        val stream = context.contentResolver.openOutputStream(destination.uri, "wt")
            ?: error("Unable to write synced feedback")
        stream.use { it.write(data) }
        return true
    }

    /**
     * Only read a pack that the local home worker has already validated.
     * The imported file is data, never executable code.
     * Returns count of new examples, or null if nothing has changed.
     */
    fun importIfChanged(context: Context): Int? {
        val file = folder(context)?.findFile(PACK_FILE) ?: return null
        if (!file.isFile || !file.canRead()) return null
        val bytes = context.contentResolver.openInputStream(file.uri)?.use { input ->
            val raw = input.readNBytes(MAX_PACK_BYTES + 1)
            require(raw.size <= MAX_PACK_BYTES) { "Training pack exceeds size limit" }
            raw
        } ?: return null
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        if (digest == prefs(context).getString(KEY_PACK_HASH, null)) return null
        val count = TrainingStore.importHomePack(
            context, String(bytes, StandardCharsets.UTF_8)
        )
        prefs(context).edit().putString(KEY_PACK_HASH, digest).apply()
        return count
    }

    fun schedule(context: Context) {
        if (!configured(context)) return
        // Periodic work is deferred and battery-managed by Android. It is not
        // expected to run at an exact time or while the device is powered off.
        val request = PeriodicWorkRequestBuilder<TrainingSyncWorker>(1, TimeUnit.HOURS)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            SYNC_WORK, ExistingPeriodicWorkPolicy.KEEP, request
        )
    }
}

/** Reopens a synced, validated pack without keeping Assetwright running. */
class TrainingSyncWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        return try {
            TrainingSync.importIfChanged(applicationContext)
            Result.success()
        } catch (_: Exception) {
            // Keep previous known-good local pack and recheck next cycle.
            Result.success()
        }
    }
}
