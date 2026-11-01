package com.assetwright.app.mini

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.WorkManager

/**
 * Trains the small residual shape model on the phone, in a battery-managed
 * worker. Persists only learned numeric weights and approved parameter data.
 */
object DeviceShapeTrainer {
    private const val NAME = "assetwright-train-local-shape-weights"

    fun schedule(context: Context) {
        val request = OneTimeWorkRequestBuilder<DeviceShapeTrainWorker>()
            .setConstraints(Constraints.Builder().setRequiresBatteryNotLow(true).build())
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            NAME, ExistingWorkPolicy.REPLACE, request
        )
    }

    fun learn(context: Context): AdaptiveShapeModel.Snapshot? {
        val approved = TrainingStore.approved(context)
        if (approved.isEmpty()) return null
        val reference = ForgeLessonStore.lessons(context) + TrainingStore.bundled(context)
        val candidate = AdaptiveShapeModel.fit(approved, reference)
        if (candidate != null) {
            val old = AdaptiveShapeModel.read(context)
            // Older checkpoint remains if candidate fails validation.
            if (old == null || candidate.trainedCount >= old.trainedCount)
                AdaptiveShapeModel.save(context, candidate)
        }
        return candidate
    }

    /** Uses our actual parametric model rather than external GLB files. */
    fun predict(context: Context, prompt: String, quality: String): VehicleSpec {
        val local = TrainingStore.approved(context)
        val forge = ForgeLessonStore.lessons(context)
        val examples = local.asReversed() + forge + TrainingStore.home(context) +
            TrainingStore.bundled(context)
        val base = MiniAi.predict(prompt, quality, examples)
        // Explicit corrections and exact reviewed Forge lessons take priority.
        val shaped = if (local.any { it.prompt.trim().equals(prompt.trim(), ignoreCase = true) } ||
            forge.any { it.prompt.trim().equals(prompt.trim(), ignoreCase = true) })
            base
        else AdaptiveShapeModel.predict(base, AdaptiveShapeModel.read(context))
        // Semantic construction is independent of the six-dimensional body
        // predictor; exact approved dimensions cannot erase component intent.
        return shaped.copy(constructionPlan = ConstructionTrainingStore.infer(context, prompt))
    }
}

class DeviceShapeTrainWorker(context: Context, params: WorkerParameters) :
    Worker(context, params) {
    override fun doWork(): Result = try {
        DeviceShapeTrainer.learn(applicationContext)
        Result.success()
    } catch (_: Exception) {
        // Do not erase the last valid model due to a broken learning example.
        Result.retry()
    }
}
