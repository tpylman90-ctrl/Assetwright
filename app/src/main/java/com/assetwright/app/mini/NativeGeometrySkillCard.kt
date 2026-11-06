package com.assetwright.app.mini

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Aqua = Color(0xFF45E0C1)
private val Panel = Color(0xFF19212C)
private val Raised = Color(0xFF202B38)
private val Muted = Color(0xFF99A8B6)
private val Ink = Color(0xFF10151D)
private val Main = Color(0xFFF1F5F7)

/**
 * Visible, user-approved training and generation on the actual Android device.
 * Separate from ordinary vehicle generation and experimental DINO checkpoint
 * promotion; every generated GLB is ORIGINAL indexed Kotlin native geometry.
 */
@Composable
fun NativeGeometrySkillCard(prompt: String, onStatus: (String) -> Unit) {
    val context = LocalContext.current
    var operation by remember { mutableStateOf(AdvancedFormOperation.SECTION_LOFT) }
    var strength by remember { mutableStateOf(.53f) }
    var archetype by remember { mutableStateOf(NativeFormArchetype.SPINDLE) }
    var preview by remember { mutableStateOf<GeneratedAsset?>(null) }
    var lessons by remember(context) { mutableStateOf(NativeSkillMemory.lessons(context).size) }

    LaunchedEffect(context, prompt) {
        preview = null
        if (prompt.isNotBlank()) {
            val recalled = NativeSkillMemory.infer(context, prompt)
            operation = recalled.operation
            strength = recalled.strength
            archetype = recalled.archetype
        }
    }
    val export = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("model/gltf-binary")
    ) { uri ->
        val model = preview
        if (uri != null && model != null) {
            try {
                val output = context.contentResolver.openOutputStream(uri)
                    ?: error("Unable to write the chosen GLB file")
                output.use { it.write(GlbWriter.encode(model)) }
                onStatus("Original Forge Mini geometry exported as a Godot-ready GLB.")
            } catch (ex: Exception) {
                onStatus("Geometry GLB export failed: " + (ex.message ?: "unknown error"))
            }
        }
    }
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Panel)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            Text("FORGE MINI · GEOMETRY SKILLS", color = Aqua,
                fontWeight = FontWeight.Bold, fontSize = 12.sp)
            Text("Eight actual original shape families with different silhouettes " +
                 "and topology. Select a form and native operation, inspect its " +
                 "real GLB, then approve the shape, operation and strength.",
                 color = Muted, fontSize = 12.sp)
            Text("Saved native technique + form lessons: " + lessons,
                color = Main, fontSize = 12.sp)
            Text("SHAPE FAMILY",color=Aqua,
                fontWeight=FontWeight.Bold,fontSize=11.sp)
            for (group in NativeFormArchetype.values().toList().chunked(2)) {
                Row(horizontalArrangement=Arrangement.spacedBy(5.dp)) {
                    for(choice in group) {
                        OutlinedButton(
                            onClick={ archetype=choice;preview=null },
                            modifier=Modifier.weight(1f),
                            shape=RoundedCornerShape(10.dp),
                            colors=ButtonDefaults.outlinedButtonColors(
                                containerColor=if(choice==archetype)
                                    Aqua.copy(alpha=.13f) else Raised,
                                contentColor=if(choice==archetype) Aqua else Muted
                            )
                        ) {
                            Text(choice.name.replace('_',' ').lowercase()
                                .replaceFirstChar { it.uppercase() },
                                fontSize=11.sp,maxLines=1)
                        }
                    }
                }
            }
            Text("NATIVE DEFORMATION",color=Aqua,
                fontWeight=FontWeight.Bold,fontSize=11.sp)
            for (group in AdvancedFormOperation.values().toList().chunked(3)) {
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    for (choice in group) {
                        OutlinedButton(
                            onClick = {
                                operation = choice
                                preview = null
                            },
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = if (choice == operation)
                                    Aqua.copy(alpha = .13f) else Raised,
                                contentColor = if (choice == operation) Aqua else Muted
                            )
                        ) {
                            Text(when (choice) {
                                AdvancedFormOperation.SECTION_LOFT -> "Loft"
                                AdvancedFormOperation.TANGENT_SWEEP -> "Sweep"
                                AdvancedFormOperation.SECTION_TWIST -> "Twist"
                                AdvancedFormOperation.SUPERELLIPSE_PROFILE -> "Profile"
                                AdvancedFormOperation.LOWER_RECESS -> "Recess"
                                AdvancedFormOperation.RIBBED_FAIRING -> "Ribs"
                            }, fontSize = 10.sp, maxLines = 1)
                        }
                    }
                }
            }
            Text("Native deformation strength: " + (strength * 100).toInt() + "%",
                color = Main, fontSize = 12.sp)
            Slider(
                value = strength,
                onValueChange = { strength = it; preview = null },
                valueRange = 0f..1f
            )
            OutlinedButton(
                onClick = {
                    try {
                        require(prompt.isNotBlank()) {
                            "Enter a description above before generating geometry."
                        }
                        preview = NativeSkillMemory.generateDiverse(
                            prompt,operation,strength,archetype)
                        onStatus("Original Kotlin " + archetype.name + " / " +
                            operation.name + " geometry built. " +
                            "Inspect the actual GLB before approving it.")
                    } catch (error: Exception) {
                        onStatus("Geometry lab: " + (error.message ?: "invalid form"))
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Aqua)
            ) { Text("Create original geometry preview") }

            val model = preview
            if (model != null) {
                Box(
                    modifier = Modifier.fillMaxWidth().height(210.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Raised)
                ) {
                    MiniPreview(model, Modifier.fillMaxSize())
                }
                Text(model.triangleCount.toString() +
                     " indexed original triangles · Drag to rotate",
                    color = Muted, fontSize = 11.sp)
                OutlinedButton(
                    onClick = { export.launch("forge-mini-native-" +
                        System.currentTimeMillis() + ".glb") },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Aqua)
                ) { Text("Export real native GLB") }
                Button(
                    onClick = {
                        try {
                            require(prompt.trim() == model.spec.sourcePrompt.trim()) {
                                "The prompt changed; preview again before teaching."
                            }
                            lessons = NativeSkillMemory.approve(
                                context,prompt,operation,strength,archetype)
                            onStatus("Forge Mini retained " + archetype.name +
                                " geometry, " + operation.name + " at " +
                                (strength * 100).toInt() + "% strength. " +
                                "It will recall this form on matching prompts.")
                        } catch (error: Exception) {
                            onStatus("Skill approval failed: " +
                                (error.message ?: "invalid approved form"))
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Aqua, contentColor = Ink)
                ) { Text("Approve geometry · Teach Forge Mini") }
            }
            Text(
                "This is a real native geometry skill, not the research DINO " +
                "model running on Android. Vehicle generation stays unchanged.",
                color = Muted, fontSize = 11.sp
            )
            if (lessons > 0) {
                TextButton(onClick = {
                    NativeSkillMemory.clear(context)
                    lessons = 0
                    preview = null
                    onStatus("Local native geometry skill lessons cleared.")
                }) { Text("Clear native geometry skill memory", color = Muted) }
            }
        }
    }
}
