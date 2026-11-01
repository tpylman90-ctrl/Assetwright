package com.assetwright.app.mini

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import kotlin.math.cos
import kotlin.math.sin

private data class Projected(val location: Offset, val depth: Float)
private data class Face(val a: Projected, val b: Projected,
                        val c: Projected, val depth: Float, val color: Color)

/** Touch-draggable, shaded triangle preview of the *actual generated mesh*. */
@Composable
fun MiniPreview(asset: GeneratedAsset, modifier: Modifier = Modifier) {
    var angle by remember(asset) { mutableFloatStateOf(0.72f) }
    Canvas(modifier = modifier.pointerInput(asset) {
        detectDragGestures { change, delta ->
            change.consume()
            angle += delta.x * 0.013f
        }
    }) {
        val ca = cos(angle)
        val sa = sin(angle)
        val scale = minOf(
            size.width / (asset.spec.length * 1.45f),
            size.height / (asset.spec.length * .95f + asset.spec.roofHeight)
        )
        fun project(v: Vec3): Projected {
            val rx = v.x * ca - v.y * sa
            val ry = v.x * sa + v.y * ca
            return Projected(
                Offset(size.width * .5f + rx * scale,
                    size.height * .63f + (ry * .46f - v.z * .84f) * scale),
                ry * .86f + v.z * .18f
            )
        }

        val faces = ArrayList<Face>(asset.triangleCount)
        for (part in asset.parts) {
            val verts = part.vertices.map(::project)
            val base = Color(part.color or 0xFF000000.toInt())
            for (i in part.indices.indices step 3) {
                val ia = part.indices[i]
                val ib = part.indices[i + 1]
                val ic = part.indices[i + 2]
                val a = verts[ia]
                val b = verts[ib]
                val c = verts[ic]
                val v0 = part.vertices[ia]
                val v1 = part.vertices[ib]
                val v2 = part.vertices[ic]
                val n = (v1 - v0).cross(v2 - v0)
                val brightness = (0.72f + (n.z * .24f) /
                    (kotlin.math.sqrt(n.x*n.x + n.y*n.y + n.z*n.z) + .001f))
                    .coerceIn(.45f, .98f)
                val color = base.copy(
                    red = (base.red * brightness).coerceIn(0f, 1f),
                    green = (base.green * brightness).coerceIn(0f, 1f),
                    blue = (base.blue * brightness).coerceIn(0f, 1f)
                )
                faces += Face(a, b, c, (a.depth + b.depth + c.depth) / 3f, color)
            }
        }
        faces.sortBy { it.depth }
        for (face in faces) {
            val path = Path().apply {
                moveTo(face.a.location.x, face.a.location.y)
                lineTo(face.b.location.x, face.b.location.y)
                lineTo(face.c.location.x, face.c.location.y)
                close()
            }
            drawPath(path, face.color)
            drawPath(path, Color.Black.copy(alpha = .07f),
                style = Stroke(width = .32f))
        }
    }
}
