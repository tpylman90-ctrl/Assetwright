package com.assetwright.app

import android.net.Uri
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
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
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
    var status by remember { mutableStateOf("Cloud generation will be connected in the next setup pass.") }

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
                PreviewCard()
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
                                Text("Example: a compact sci-fi cargo drone with twin side engines, teal status lights, and worn alloy panels", color = TextMuted, fontSize = 14.sp, lineHeight = 20.sp)
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
                    OutlinedButton(
                        onClick = { imagePicker.launch("image/*") },
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = TextMain)
                    ) {
                        Text(if (selectedImage == null) "＋  Add reference image" else "✓  Reference image selected")
                    }
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
                        onClick = { status = "The app shell is ready. Connecting the cloud model service is the next step." },
                        enabled = prompt.isNotBlank() || selectedImage != null,
                        modifier = Modifier.fillMaxWidth().height(54.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Teal,
                            contentColor = Ink,
                            disabledContainerColor = PanelRaised,
                            disabledContentColor = TextMuted
                        )
                    ) {
                        Text("Generate game asset", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    }
                    Text(status, color = TextMuted, fontSize = 12.sp, lineHeight = 17.sp)
                    Spacer(Modifier.height(18.dp))
                }
            }
        }
    }
}

@Composable
private fun PreviewCard() {
    Card(
        modifier = Modifier.fillMaxWidth().height(220.dp),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = Panel)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Canvas(modifier = Modifier.fillMaxSize().padding(24.dp)) {
                val cx = size.width / 2f
                val cy = size.height / 2f - 5f
                val w = size.width * 0.22f
                val h = size.height * 0.27f
                val top = Path().apply {
                    moveTo(cx, cy - h)
                    lineTo(cx + w, cy - h / 2)
                    lineTo(cx, cy)
                    lineTo(cx - w, cy - h / 2)
                    close()
                }
                val left = Path().apply {
                    moveTo(cx - w, cy - h / 2)
                    lineTo(cx, cy)
                    lineTo(cx, cy + h)
                    lineTo(cx - w, cy + h / 2)
                    close()
                }
                val right = Path().apply {
                    moveTo(cx + w, cy - h / 2)
                    lineTo(cx, cy)
                    lineTo(cx, cy + h)
                    lineTo(cx + w, cy + h / 2)
                    close()
                }
                drawPath(top, Color(0xFF2B806F))
                drawPath(left, Color(0xFF1D5C55))
                drawPath(right, Color(0xFF38B99A))
                drawPath(top, Teal.copy(alpha = 0.7f), style = Stroke(width = 2.dp.toPx()))
                drawPath(left, Teal.copy(alpha = 0.45f), style = Stroke(width = 2.dp.toPx()))
                drawPath(right, Teal.copy(alpha = 0.7f), style = Stroke(width = 2.dp.toPx()))
            }
            Column(
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text("3D PREVIEW", color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.3.sp)
                Text("Your generated model will appear here", color = TextMuted, fontSize = 12.sp)
            }
            Text(
                "GAME ASSET",
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp),
                color = Teal,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp
            )
        }
    }
}

@Composable
private fun SectionLabel(label: String) {
    Text(label, color = TextMuted, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.2.sp)
}
