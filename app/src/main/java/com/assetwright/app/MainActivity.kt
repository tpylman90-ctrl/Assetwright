package com.assetwright.app

import android.net.Uri
import androidx.compose.ui.platform.LocalContext
import com.assetwright.app.mini.GeneratedAsset
import com.assetwright.app.mini.GlbWriter
import com.assetwright.app.mini.MiniAi
import com.assetwright.app.mini.MiniGeometry
import com.assetwright.app.mini.MiniPreview
import com.assetwright.app.mini.TrainingStore
import com.assetwright.app.mini.VehicleSpec
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

private val Ink = Color(0xFF10151D)
private val Panel = Color(0xFF19212C)
private val PanelRaised = Color(0xFF202B38)
private val Teal = Color(0xFF45E0C1)
private val TextMain = Color(0xFFF1F5F7)
private val TextMuted = Color(0xFF99A8B6)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                AssetwrightScreen()
            }
        }
    }
}

@Composable
private fun AssetwrightScreen() {
    var prompt by remember { mutableStateOf("") }
    var selectedImage by remember { mutableStateOf<Uri?>(null) }
    var selectedQuality by remember { mutableStateOf("Mobile") }
    var status by remember { mutableStateOf("Offline Mini AI v0.1: describe a hover SUV, coupe, or racer to generate an editable-spec 3D mesh.") }
    var generatedAsset by remember { mutableStateOf<GeneratedAsset?>(null) }
    val context = LocalContext.current
    var localExamples by remember(context) {
        mutableStateOf(TrainingStore.approved(context))
    }
    var acceptedCount by remember(context) { mutableStateOf(localExamples.size) }
    var homeExamples by remember(context) {
        mutableStateOf(TrainingStore.home(context))
    }
    val trainingExamples = remember(context, localExamples, homeExamples) {
        localExamples.asReversed() + homeExamples.asReversed() + TrainingStore.bundled(context)
    }
    val homeImport = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
        onResult = { uri ->
            if (uri != null) {
                try {
                    val source = context.contentResolver.openInputStream(uri)
                        ?.bufferedReader()?.use { it.readText() }
                        ?: error("Unable to read the selected model pack")
                    val count = TrainingStore.importHomePack(context, source)
                    homeExamples = TrainingStore.home(context)
                    status = "Imported " + count + " approved home training examples. " +
                        "They will influence the next offline generation."
                } catch (ex: Exception) {
                    status = "Model pack was not accepted: " + (ex.message ?: "unknown error")
                }
            }
        }
    )
    val trainingExport = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/x-ndjson"),
        onResult = { uri ->
            if (uri != null) {
                try {
                    val output = context.contentResolver.openOutputStream(uri)
                        ?: error("Unable to open selected file")
                    output.use { it.write(TrainingStore.approvedJsonl(context).toByteArray()) }
                    status = "Approved learning examples exported. Copy this file to your home training inbox."
                } catch (ex: Exception) {
                    status = "Training export failed: " + (ex.message ?: "unknown error")
                }
            }
        }
    )
    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("model/gltf-binary"),
        onResult = { uri ->
            val asset = generatedAsset
            if (uri != null && asset != null) {
                try {
                    val output = context.contentResolver.openOutputStream(uri)
                        ?: error("Could not open export destination")
                    output.use { it.write(GlbWriter.encode(asset)) }
                    status = "GLB exported successfully. Ready to import into Godot."
                } catch (ex: Exception) {
                    status = "Export failed: " + (ex.message ?: "unknown error")
                }
            }
        }
    )

    val imagePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent(),
        onResult = { selectedImage = it }
    )

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Ink
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 18.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(RoundedCornerShape(13.dp))
                            .background(Teal),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("A", color = Ink, fontSize = 22.sp, fontWeight = FontWeight.Black)
                    }
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text("ASSETWRIGHT", color = TextMain, fontSize = 15.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.4.sp)
                        Text("AI GAME ASSET BUILDER", color = TextMuted, fontSize = 10.sp, letterSpacing = 1.3.sp)
                    }
                    Spacer(Modifier.weight(1f))
                    Text("BETA", color = Teal, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Make a game asset", color = TextMain, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                    Text("Start with a prompt or a reference image. Export for real-time games.", color = TextMuted, fontSize = 14.sp, lineHeight = 20.sp)
                }
            }

            item {
                PreviewCard(generatedAsset)
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SectionLabel("DESCRIBE YOUR MODEL")
                    Card(
                        shape = RoundedCornerShape(18.dp),
                        colors = CardDefaults.cardColors(containerColor = Panel)
                    ) {
                        Box(modifier = Modifier.fillMaxWidth().height(126.dp).padding(15.dp)) {
                            if (prompt.isBlank()) {
                                Text("Example: a wide hover SUV with a panoramic canopy and muscular rear body", color = TextMuted, fontSize = 14.sp, lineHeight = 20.sp)
                            }
                            BasicTextField(
                                value = prompt,
                                onValueChange = { prompt = it.take(1000) },
                                modifier = Modifier.fillMaxSize(),
                                textStyle = MaterialTheme.typography.bodyMedium.copy(color = TextMain, lineHeight = 20.sp),
                                cursorBrush = androidx.compose.ui.graphics.SolidColor(Teal)
                            )
                        }
                    }
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = { imagePicker.launch("image/*") },
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = TextMain)
                        ) {
                            Text(if (selectedImage == null) "＋  Add reference image" else "✓  Change reference image")
                        }
                        if (selectedImage != null) {
                            TextButton(onClick = { selectedImage = null }) {
                                Text("Remove", color = TextMuted)
                            }
                        }
                    }
                    Text(
                        "Reference images are not processed by the offline mini AI yet.",
                        color = TextMuted, fontSize = 11.sp
                    )
                    Text(
                        "${prompt.length}/1000 characters",
                        modifier = Modifier.align(Alignment.End),
                        color = TextMuted,
                        fontSize = 11.sp
                    )
                }
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SectionLabel("GAME PERFORMANCE TARGET")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("Mobile", "Balanced", "High detail").forEach { quality ->
                            val selected = selectedQuality == quality
                            OutlinedButton(
                                onClick = { selectedQuality = quality },
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.outlinedButtonColors(
                                    containerColor = if (selected) Teal.copy(alpha = 0.12f) else Panel,
                                    contentColor = if (selected) Teal else TextMuted
                                ),
                                modifier = Modifier.weight(1f)
                            ) {
                                Text(quality, fontSize = 12.sp, maxLines = 1)
                            }
                        }
                    }
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(Panel)
                            .padding(13.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("EXPORT", color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                        Spacer(Modifier.weight(1f))
                        Text("Godot-ready  ·  GLB", color = TextMain, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(
                        onClick = {
                            try {
                                val spec = MiniAi.predict(prompt, selectedQuality, trainingExamples)
                                val built = MiniGeometry.generate(spec)
                                generatedAsset = built
                                status = "Generated offline: " + spec.title + " • " +
                                    built.triangleCount + " triangles. Drag the model to rotate it." +
                                    if (selectedImage != null) " Reference image not yet used." else ""
                            } catch (ex: Exception) {
                                generatedAsset = null
                                status = ex.message ?: "Could not generate this asset."
                            }
                        },
                        enabled = prompt.isNotBlank(),
                        modifier = Modifier.fillMaxWidth().height(54.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Teal,
                            contentColor = Ink,
                            disabledContainerColor = PanelRaised,
                            disabledContentColor = TextMuted
                        )
                    ) {
                        Text("Generate offline 3D asset", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    }
                    val current = generatedAsset
                    if (current != null) {
                        OutlinedButton(
                            onClick = { exportLauncher.launch("assetwright-mini-" +
                                System.currentTimeMillis() + ".glb") },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Teal)
                        ) {
                            Text("Export GLB to device")
                        }
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = Panel)
                        ) {
                            Column(
                                modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(7.dp)
                            ) {
                                Text("TEACH THE MINI AI", color = Teal,
                                    fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                Text(
                                    "Correct the proportions below. When you approve them, " +
                                        "the AI learns this prompt immediately on your phone.",
                                    color = TextMuted, fontSize = 12.sp, lineHeight = 17.sp
                                )
                                VehicleParameterSlider("Body length", current.spec.length, 3.4f..7.0f) {
                                    generatedAsset = MiniGeometry.generate(current.spec.copy(length = it))
                                }
                                VehicleParameterSlider("Body width", current.spec.width, 1.45f..3.2f) {
                                    generatedAsset = MiniGeometry.generate(current.spec.copy(width = it))
                                }
                                VehicleParameterSlider("Roof height", current.spec.roofHeight, 1.05f..2.30f) {
                                    generatedAsset = MiniGeometry.generate(current.spec.copy(roofHeight = it))
                                }
                                VehicleParameterSlider("Canopy length", current.spec.canopyLength, 0.85f..3.1f) {
                                    generatedAsset = MiniGeometry.generate(current.spec.copy(canopyLength = it))
                                }
                                VehicleParameterSlider("Nose taper", current.spec.noseTaper, 0.25f..0.9f) {
                                    generatedAsset = MiniGeometry.generate(current.spec.copy(noseTaper = it))
                                }
                                VehicleParameterSlider("Rear haunch", current.spec.rearHaunch, 0.9f..1.3f) {
                                    generatedAsset = MiniGeometry.generate(current.spec.copy(rearHaunch = it))
                                }
                                Button(
                                    onClick = {
                                        try {
                                            val count = TrainingStore.approve(context, current.spec)
                                            localExamples = TrainingStore.approved(context)
                                            acceptedCount = count
                                            status = "Approved and learned locally. Your next " +
                                                "generation can use this corrected design."
                                        } catch (ex: Exception) {
                                            status = "Couldn't save feedback: " +
                                                (ex.message ?: "unknown error")
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = ButtonDefaults.buttonColors(containerColor = Teal, contentColor = Ink)
                                ) {
                                    Text("Approve design · Teach Mini AI")
                                }
                            }
                        }
                    }
                    OutlinedButton(
                        onClick = { homeImport.launch(arrayOf("application/json", "text/plain", "application/octet-stream")) },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = TextMain)
                    ) {
                        Text("Import home-trained model pack")
                    }
                    if (homeExamples.isNotEmpty()) {
                        Text("Home training: " + homeExamples.size + " approved examples active",
                            color = TextMuted, fontSize = 12.sp)
                    }
                    if (acceptedCount > 0) {
                        OutlinedButton(
                            onClick = {
                                trainingExport.launch("assetwright-approved-examples.jsonl")
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Teal)
                        ) {
                            Text("Export " + acceptedCount + " approved learning examples")
                        }
                    }
                    Text(status, color = TextMuted, fontSize = 12.sp, lineHeight = 17.sp)
                    Spacer(Modifier.height(18.dp))
                }
            }
        }
    }
}

@Composable
private fun PreviewCard(asset: GeneratedAsset?) {
    Card(
        modifier = Modifier.fillMaxWidth().height(255.dp),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = Panel)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            if (asset != null) {
                MiniPreview(asset, Modifier.fillMaxSize())
            } else {
                Text(
                    "◇",
                    modifier = Modifier.align(Alignment.Center),
                    color = Teal, fontSize = 80.sp
                )
            }
            Text(
                "OFFLINE MINI AI  •  V0.1",
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp),
                color = Teal, fontSize = 10.sp,
                fontWeight = FontWeight.Bold, letterSpacing = 1.sp
            )
            Column(
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    if (asset == null) "3D PREVIEW" else asset.spec.title.uppercase(),
                    color = TextMain, fontSize = 11.sp, fontWeight = FontWeight.Bold
                )
                Text(
                    if (asset == null) "Describe a hover vehicle to create a real mesh"
                    else "Drag to rotate  ·  " + asset.triangleCount + " triangles  ·  GLB export",
                    color = TextMuted, fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun VehicleParameterSlider(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onChange: (Float) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, color = TextMain, fontSize = 12.sp)
            Text(String.format(Locale.US, "%.2f", value), color = TextMuted, fontSize = 12.sp)
        }
        Slider(value = value, onValueChange = onChange, valueRange = range)
    }
}

@Composable
private fun SectionLabel(label: String) {
    Text(label, color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
}
