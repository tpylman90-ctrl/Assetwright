package com.assetwright.app.geometry

import android.content.Context
import android.opengl.GLES30
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/**
 * Native OpenGL ES 3 full-resolution assembly viewer, with a real 24-bit depth
 * buffer, shaded solids, translucent named glazing, and GPU depth-tested picking.
 *
 * All geometry is read-only. Unlike the old Canvas preview, this renders every
 * triangle, including small mechanical parts, without sparse triangle sampling.
 */
class ComponentModelView(context: Context) : GLSurfaceView(context) {
    @Volatile private var wantedMesh: GeometryMesh? = null
    @Volatile private var selected: Int = -1
    @Volatile private var isolated: Boolean = false
    @Volatile private var azimuth = 35f
    @Volatile private var elevation = 19f
    @Volatile private var magnification = 1f
    @Volatile private var pendingPick: Pair<Int, Int>? = null
    private val gpu = FullModelRenderer()
    var onSelected: ((Int) -> Unit)? = null

    var mesh: GeometryMesh?
        get() = wantedMesh
        set(value) {
            wantedMesh = value
            selected = -1
            isolated = false
            requestRender()
        }
    var selectedId: Int
        get() = selected
        set(value) { selected = value; requestRender() }
    var isolate: Boolean
        get() = isolated
        set(value) { isolated = value; requestRender() }
    var yaw: Float
        get() = azimuth
        set(value) { azimuth = value; requestRender() }
    var pitch: Float
        get() = elevation
        set(value) { elevation = value.coerceIn(-78f, 78f); requestRender() }
    var zoom: Float
        get() = magnification
        set(value) { magnification = value.coerceIn(.28f, 4f); requestRender() }

    init {
        setEGLContextClientVersion(3)
        setEGLConfigChooser(8, 8, 8, 8, 24, 8)
        setRenderer(gpu)
        renderMode = RENDERMODE_WHEN_DIRTY
        preserveEGLContextOnPause = true
    }

    private var downX = 0f
    private var downY = 0f
    private var oldX = 0f
    private var oldY = 0f
    private var moved = false
    private val scaleDetector = ScaleGestureDetector(context,
        object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(d: ScaleGestureDetector): Boolean {
                zoom *= d.scaleFactor
                moved = true
                return true
            }
        })

    override fun onTouchEvent(e: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(e)
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                parent?.requestDisallowInterceptTouchEvent(true)
                downX = e.x; downY = e.y
                oldX = e.x; oldY = e.y
                moved = false
                return true
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                moved = true
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (e.pointerCount == 1 && !scaleDetector.isInProgress) {
                    val dx = e.x - oldX
                    val dy = e.y - oldY
                    if (hypot(e.x - downX, e.y - downY) > 8f * resources.displayMetrics.density) moved = true
                    if (moved) {
                        yaw += dx * .42f
                        pitch += dy * .32f
                    }
                    oldX = e.x; oldY = e.y
                } else moved = true
                return true
            }
            MotionEvent.ACTION_UP -> {
                parent?.requestDisallowInterceptTouchEvent(false)
                if (!moved && wantedMesh != null) {
                    pendingPick = e.x.toInt() to e.y.toInt()
                    requestRender()
                }
                performClick()
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                parent?.requestDisallowInterceptTouchEvent(false)
                return true
            }
        }
        return true
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    private inner class FullModelRenderer : Renderer {
        private var loaded: GeometryMesh? = null
        private var vbo = 0
        private var vao = 0
        private var program = 0
        private var locMvp = -1
        private var locMv = -1
        private var locMode = -1
        private var locPick = -1
        private var viewportW = 1
        private var viewportH = 1
        private val mv = FloatArray(16)
        private val proj = FloatArray(16)
        private val mvp = FloatArray(16)
        private val transform = FloatArray(16)

        private val vert = """
            #version 300 es
            precision highp float;
            layout(location=0) in vec3 aPosition;
            layout(location=1) in vec3 aNormal;
            layout(location=2) in vec4 aColor;
            uniform mat4 uMVP;
            uniform mat4 uMV;
            out vec3 vNormal;
            out vec4 vColor;
            void main() {
                gl_Position=uMVP*vec4(aPosition,1.0);
                vNormal=mat3(uMV)*aNormal;
                vColor=aColor;
            }
        """.trimIndent()

        private val frag = """
            #version 300 es
            precision highp float;
            in vec3 vNormal;
            in vec4 vColor;
            uniform int uMode;
            uniform vec3 uPick;
            out vec4 outColor;
            void main() {
                if (uMode==1) {
                    outColor=vec4(uPick,1.0);
                } else {
                    vec3 n=normalize(vNormal);
                    float diffuse=abs(dot(n,normalize(vec3(0.45,0.80,0.72))));
                    float illumination=0.46+diffuse*0.54;
                    vec3 base=vColor.rgb*illumination;
                    if (uMode==2) {
                        outColor=vec4(mix(base,vec3(0.03,0.95,0.96),0.78),1.0);
                    } else if (uMode==3) {
                        outColor=vec4(mix(base,vec3(0.30,0.65,0.76),0.44),0.22);
                    } else if (uMode==4) {
                        outColor=vec4(vec3(0.06,0.94,0.97),0.46);
                    } else {
                        outColor=vec4(base,1.0);
                    }
                }
            }
        """.trimIndent()

        override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
            program = makeProgram()
            locMvp = GLES30.glGetUniformLocation(program, "uMVP")
            locMv = GLES30.glGetUniformLocation(program, "uMV")
            locMode = GLES30.glGetUniformLocation(program, "uMode")
            locPick = GLES30.glGetUniformLocation(program, "uPick")
            // A GL context can be replaced after app pause/resume.
            loaded = null
            vbo = 0
            vao = 0
            GLES30.glEnable(GLES30.GL_DEPTH_TEST)
            GLES30.glDepthFunc(GLES30.GL_LEQUAL)
            GLES30.glDisable(GLES30.GL_CULL_FACE) // Retain thin/single-sided machine parts
        }

        private fun shader(kind: Int, text: String): Int {
            val id = GLES30.glCreateShader(kind)
            GLES30.glShaderSource(id, text)
            GLES30.glCompileShader(id)
            val ok = IntArray(1)
            GLES30.glGetShaderiv(id, GLES30.GL_COMPILE_STATUS, ok, 0)
            check(ok[0] != 0) { GLES30.glGetShaderInfoLog(id) }
            return id
        }

        private fun makeProgram(): Int {
            val a = shader(GLES30.GL_VERTEX_SHADER, vert)
            val b = shader(GLES30.GL_FRAGMENT_SHADER, frag)
            val result = GLES30.glCreateProgram()
            GLES30.glAttachShader(result, a)
            GLES30.glAttachShader(result, b)
            GLES30.glLinkProgram(result)
            val ok = IntArray(1)
            GLES30.glGetProgramiv(result, GLES30.GL_LINK_STATUS, ok, 0)
            check(ok[0] != 0) { GLES30.glGetProgramInfoLog(result) }
            GLES30.glDeleteShader(a)
            GLES30.glDeleteShader(b)
            return result
        }

        override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
            viewportW = width.coerceAtLeast(1)
            viewportH = height.coerceAtLeast(1)
            GLES30.glViewport(0,0,viewportW,viewportH)
        }

        private fun upload(m: GeometryMesh?) {
            if (m === loaded) return
            if (vbo != 0) {
                GLES30.glDeleteBuffers(1, intArrayOf(vbo), 0)
                GLES30.glDeleteVertexArrays(1, intArrayOf(vao), 0)
            }
            loaded = m
            vbo = 0
            vao = 0
            if (m == null) return

            // Each triangle gets its actual face normal (preserves bevels and
            // engineered planar surfaces). Interleaved: position 3f, normal 3f,
            // color RGBA unsigned bytes = 28 bytes/vertex.
            val stride = 28
            val size = m.count.toLong()*3L*stride
            require(size <= 125L*1024*1024) { "Preview buffer exceeds mobile budget" }
            val bytes = ByteBuffer.allocateDirect(size.toInt()).order(ByteOrder.nativeOrder())
            val positions = m.xyz
            val indices = m.triangles
            val colors = m.importedVertexColors
            for (t in 0 until m.count) {
                val a = indices[3*t]; val b = indices[3*t+1]; val c = indices[3*t+2]
                val ax = positions[3*a];val ay=positions[3*a+1];val az=positions[3*a+2]
                val bx = positions[3*b];val by=positions[3*b+1];val bz=positions[3*b+2]
                val cx = positions[3*c];val cy=positions[3*c+1];val cz=positions[3*c+2]
                val ux=bx-ax;val uy=by-ay;val uz=bz-az
                val vx=cx-ax;val vy=cy-ay;val vz=cz-az
                val nx=uy*vz-uz*vy;val ny=uz*vx-ux*vz;val nz=ux*vy-uy*vx
                val mag=sqrt(nx*nx+ny*ny+nz*nz).coerceAtLeast(1e-12f)
                for (id in intArrayOf(a,b,c)) {
                    bytes.putFloat(positions[3*id]);bytes.putFloat(positions[3*id+1])
                    bytes.putFloat(positions[3*id+2])
                    bytes.putFloat(nx/mag);bytes.putFloat(ny/mag);bytes.putFloat(nz/mag)
                    val rgba=colors?.getOrNull(id) ?: 0xffa9bac8.toInt()
                    bytes.put(((rgba shr 16) and 255).toByte())
                    bytes.put(((rgba shr 8) and 255).toByte())
                    bytes.put((rgba and 255).toByte())
                    bytes.put(((rgba ushr 24) and 255).toByte())
                }
            }
            bytes.flip()
            val ids=IntArray(1)
            GLES30.glGenVertexArrays(1,ids,0)
            vao=ids[0]
            GLES30.glBindVertexArray(vao)
            GLES30.glGenBuffers(1,ids,0)
            vbo=ids[0]
            GLES30.glBindBuffer(GLES30.GL_ARRAY_BUFFER,vbo)
            GLES30.glBufferData(GLES30.GL_ARRAY_BUFFER,bytes.capacity(),
                bytes,GLES30.GL_STATIC_DRAW)
            GLES30.glEnableVertexAttribArray(0)
            GLES30.glVertexAttribPointer(0,3,GLES30.GL_FLOAT,false,stride,0)
            GLES30.glEnableVertexAttribArray(1)
            GLES30.glVertexAttribPointer(1,3,GLES30.GL_FLOAT,false,stride,12)
            GLES30.glEnableVertexAttribArray(2)
            GLES30.glVertexAttribPointer(2,4,GLES30.GL_UNSIGNED_BYTE,true,stride,24)
            GLES30.glBindVertexArray(0)
            GLES30.glBindBuffer(GLES30.GL_ARRAY_BUFFER,0)
        }

        private fun glass(p: GeometryPart): Boolean {
            val n=p.sourceName.lowercase()
            return listOf("glass","glazing","window","windshield","transparent",
                "polycarbonate","acrylic","perspex").any { it in n }
        }

        private fun matrices(m: GeometryMesh) {
            val b=m.limits
            val cx=(b[0]+b[3])*.5f
            val cy=(b[1]+b[4])*.5f
            val cz=(b[2]+b[5])*.5f
            val dx=b[3]-b[0];val dy=b[4]-b[1];val dz=b[5]-b[2]
            val radius=(sqrt(dx*dx+dy*dy+dz*dz)*.5f).coerceAtLeast(.01f)
            val aspect=viewportW.toFloat()/viewportH
            val fov=48f
            val distance=radius/(tan(Math.toRadians((fov*.5).toDouble())).toFloat())*
                1.30f*max(1f,1f/aspect)/magnification
            val near=(radius*.006f).coerceAtLeast(.0001f)
            val far=(distance+radius*10f).coerceAtLeast(near+1f)
            Matrix.perspectiveM(proj,0,fov,aspect,near,far)
            val view=FloatArray(16)
            Matrix.setLookAtM(view,0,0f,0f,distance,0f,0f,0f,0f,1f,0f)
            Matrix.setIdentityM(transform,0)
            Matrix.rotateM(transform,0,azimuth,0f,1f,0f)
            Matrix.rotateM(transform,0,elevation,1f,0f,0f)
            Matrix.translateM(transform,0,-cx,-cy,-cz)
            Matrix.multiplyMM(mv,0,view,0,transform,0)
            Matrix.multiplyMM(mvp,0,proj,0,mv,0)
        }

        private fun drawPart(p: GeometryPart) {
            if (p.triangleCount>0)
                GLES30.glDrawArrays(GLES30.GL_TRIANGLES,p.firstTriangle*3,p.triangleCount*3)
        }

        private fun drawRange(parts: List<GeometryPart>, onlyGlazing: Boolean) {
            // Merge adjacent opaque primitives into fewer draw calls.
            var start=-1
            var count=0
            fun flush() {
                if (start>=0 && count>0) {
                    GLES30.glDrawArrays(GLES30.GL_TRIANGLES,start*3,count*3)
                }
                start=-1;count=0
            }
            for (p in parts) {
                if (glass(p) != onlyGlazing) { flush();continue }
                if (start<0) {start=p.firstTriangle;count=p.triangleCount}
                else if (start+count==p.firstTriangle)count+=p.triangleCount
                else {flush();start=p.firstTriangle;count=p.triangleCount}
            }
            flush()
        }

        private fun mode(value:Int) = GLES30.glUniform1i(locMode,value)

        private fun renderScene(m: GeometryMesh, picking:Boolean) {
            GLES30.glEnable(GLES30.GL_DEPTH_TEST)
            GLES30.glDepthMask(true)
            GLES30.glDisable(GLES30.GL_BLEND)
            if (picking) GLES30.glClearColor(0f,0f,0f,1f)
            else GLES30.glClearColor(.045f,.076f,.105f,1f)
            GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT or GLES30.GL_DEPTH_BUFFER_BIT)
            GLES30.glUseProgram(program)
            GLES30.glUniformMatrix4fv(locMvp,1,false,mvp,0)
            GLES30.glUniformMatrix4fv(locMv,1,false,mv,0)
            GLES30.glBindVertexArray(vao)

            if (picking) {
                GLES30.glDisable(GLES30.GL_DITHER)
                mode(1)
                for(p in m.parts) {
                    if (isolated && selected>=0 && p.id!=selected) continue
                    val encoded=p.id+1
                    GLES30.glUniform3f(locPick,
                        (encoded and 255)/255f,((encoded shr 8) and 255)/255f,
                        ((encoded shr 16) and 255)/255f)
                    drawPart(p)
                }
                GLES30.glEnable(GLES30.GL_DITHER)
            } else {
                mode(0)
                if (isolated && selected>=0) {
                    m.parts.getOrNull(selected)?.let(::drawPart)
                } else {
                    drawRange(m.parts,false)
                }
                // Transparent source-named safety glazing is drawn after opaque
                // machinery, depth-tested but not depth-writing.
                GLES30.glEnable(GLES30.GL_BLEND)
                GLES30.glBlendFunc(GLES30.GL_SRC_ALPHA,GLES30.GL_ONE_MINUS_SRC_ALPHA)
                GLES30.glDepthMask(false)
                mode(3)
                if(isolated && selected>=0) {
                    m.parts.getOrNull(selected)?.takeIf(::glass)?.let(::drawPart)
                } else {
                    drawRange(m.parts,true)
                }
                if(selected>=0){
                    val part=m.parts.getOrNull(selected)
                    if(part!=null){
                        mode(if(glass(part))4 else 2)
                        GLES30.glEnable(GLES30.GL_POLYGON_OFFSET_FILL)
                        GLES30.glPolygonOffset(-1f,-1f)
                        if(!glass(part)){
                            GLES30.glDepthMask(true)
                            GLES30.glDisable(GLES30.GL_BLEND)
                        }
                        drawPart(part)
                        GLES30.glDisable(GLES30.GL_POLYGON_OFFSET_FILL)
                    }
                }
                GLES30.glDepthMask(true)
                GLES30.glDisable(GLES30.GL_BLEND)
            }
            GLES30.glBindVertexArray(0)
        }

        override fun onDrawFrame(gl: GL10?) {
            upload(wantedMesh)
            val m=loaded
            if(m==null) {
                GLES30.glClearColor(.045f,.076f,.105f,1f)
                GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT or GLES30.GL_DEPTH_BUFFER_BIT)
                return
            }
            matrices(m)
            val pick=pendingPick
            if(pick!=null){
                pendingPick=null
                renderScene(m,true)
                val pixel=ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder())
                val x=pick.first.coerceIn(0,viewportW-1)
                val y=(viewportH-1-pick.second).coerceIn(0,viewportH-1)
                GLES30.glReadPixels(x,y,1,1,GLES30.GL_RGBA,GLES30.GL_UNSIGNED_BYTE,pixel)
                val r=pixel.get(0).toInt() and 255
                val g=pixel.get(1).toInt() and 255
                val b=pixel.get(2).toInt() and 255
                val id=(r or (g shl 8) or (b shl 16))-1
                if(id in m.parts.indices){
                    selected=id
                    post { onSelected?.invoke(id) }
                }
            }
            renderScene(m,false)
        }
    }
}
