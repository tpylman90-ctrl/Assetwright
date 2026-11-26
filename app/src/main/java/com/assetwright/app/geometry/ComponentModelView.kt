package com.assetwright.app.geometry

import android.content.Context
import android.graphics.BitmapFactory
import android.opengl.GLUtils
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
    /** False = topology-friendly gray-blue clay. True = actual GLB PBR material factors/textures. */
    @Volatile private var pbrEnabled=false
    var materialPreview:Boolean
        get()=pbrEnabled
        set(value){pbrEnabled=value;requestRender()}


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
        setEGLConfigChooser(8, 8, 8, 8, 24, 0)
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
        private var locPreview = -1
        private var locBaseFactor = -1
        private var locMetallic = -1
        private var locRoughness = -1
        private var locEmissive = -1
        private var locEmissiveStrength = -1
        private var locAlphaMode = -1
        private var locAlphaCutoff = -1
        private val textureHandles=HashMap<Pair<Int,Boolean>,Int>()
        private var gpuImageBytes=0L
        private val maxImageBytes=96L*1024*1024
        private var maxTextureDimension=2048

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
            layout(location=3) in vec2 aUV0;
            layout(location=4) in vec2 aUV1;
            uniform mat4 uMVP;
            uniform mat4 uMV;
            out vec3 vNormal;
            out vec3 vViewPosition;
            out vec4 vColor;
            out vec2 vUV0;
            out vec2 vUV1;
            void main() {
                gl_Position=uMVP*vec4(aPosition,1.0);
                vViewPosition=(uMV*vec4(aPosition,1.0)).xyz;
                vNormal=mat3(uMV)*aNormal;
                vColor=aColor;
                vUV0=aUV0;
                vUV1=aUV1;
            }
        """.trimIndent()

        private val frag = """
            #version 300 es
            precision highp float;
            in vec3 vNormal;
            in vec3 vViewPosition;
            in vec4 vColor;
            in vec2 vUV0;
            in vec2 vUV1;
            uniform int uMode;
            uniform int uMaterialPreview;
            uniform vec3 uPick;
            uniform vec4 uBaseFactor;
            uniform float uMetallic;
            uniform float uRoughness;
            uniform vec3 uEmissive;
            uniform float uEmissiveStrength;
            uniform int uAlphaMode;   // 0=opaque, 1=mask, 2=blend
            uniform float uAlphaCutoff;
            uniform int uHasBase;
            uniform int uHasMetallicRoughness;
            uniform int uHasEmissive;
            uniform int uBaseUVSet;
            uniform int uMetallicUVSet;
            uniform int uEmissiveUVSet;
            uniform mat3 uBaseTransform;
            uniform mat3 uMetallicTransform;
            uniform mat3 uEmissiveTransform;
            uniform sampler2D uBaseMap;
            uniform sampler2D uMetallicMap;
            uniform sampler2D uEmissiveMap;
            out vec4 outColor;
            const float PI=3.14159265;
            vec2 transformedUV(int setIndex, mat3 transform) {
                vec2 uv=setIndex==1?vUV1:vUV0;
                return (transform*vec3(uv,1.0)).xy;
            }
            vec3 fresnelSchlick(float theta,vec3 f0){
                return f0+(1.0-f0)*pow(clamp(1.0-theta,0.0,1.0),5.0);
            }
            float distributionGGX(vec3 n,vec3 h,float rough){
                float a=rough*rough;
                float a2=a*a;
                float ndh=max(dot(n,h),0.0);
                float d=(ndh*ndh*(a2-1.0)+1.0);
                return a2/max(PI*d*d,0.0001);
            }
            float geometrySchlick(float nDotV,float rough){
                float k=pow(rough+1.0,2.0)/8.0;
                return nDotV/(nDotV*(1.0-k)+k);
            }
            void main() {
                if(uMode==1){
                    outColor=vec4(uPick,1.0);
                    return;
                }
                vec3 n=normalize(vNormal);
                if(!gl_FrontFacing) n=-n;
                vec3 c;
                float alpha=1.0;
                if(uMaterialPreview==0){
                    // Geometry Inspection: intentionally independent from materials.
                    vec3 clay=vec3(0.54,0.66,0.74);
                    float lit=0.42+0.58*max(dot(n,normalize(vec3(0.48,0.81,0.65))),0.0);
                    c=clay*lit;
                    if(uMode==3) alpha=0.23;
                }else{
                    vec4 baseTex=uHasBase==1?
                        texture(uBaseMap,transformedUV(uBaseUVSet,uBaseTransform)):
                        vec4(1.0);
                    vec4 base=uBaseFactor*vColor*baseTex;
                    float rough=clamp(uRoughness,0.055,1.0);
                    float metal=clamp(uMetallic,0.0,1.0);
                    if(uHasMetallicRoughness==1){
                        vec4 mr=texture(uMetallicMap,
                            transformedUV(uMetallicUVSet,uMetallicTransform));
                        // glTF: green = roughness, blue = metallic
                        rough=clamp(rough*mr.g,0.055,1.0);
                        metal=clamp(metal*mr.b,0.0,1.0);
                    }
                    alpha=base.a;
                    if(uAlphaMode==0)alpha=1.0;
                    else if(uAlphaMode==1){
                        if(alpha<uAlphaCutoff) discard;
                        alpha=1.0;
                    }
                    vec3 albedo=base.rgb;
                    vec3 viewDir=normalize(-vViewPosition);
                    vec3 f0=mix(vec3(0.04),albedo,metal);
                    vec3 light=vec3(0.45,0.76,0.58);
                    light=normalize(light);
                    vec3 halfDir=normalize(viewDir+light);
                    float nl=max(dot(n,light),0.0);
                    float nv=max(dot(n,viewDir),0.001);
                    float vh=max(dot(viewDir,halfDir),0.0);
                    vec3 fresnel=fresnelSchlick(vh,f0);
                    float d=distributionGGX(n,halfDir,rough);
                    float g=geometrySchlick(nv,rough)*geometrySchlick(nl,rough);
                    vec3 spec=(d*g*fresnel)/max(4.0*nl*nv,0.001);
                    vec3 kd=(vec3(1.0)-fresnel)*(1.0-metal);
                    vec3 direct=(kd*albedo/PI+spec)*nl*2.2;
                    vec3 env=albedo*(1.0-metal)*0.27+f0*(0.16+0.16*(1.0-rough));
                    c=direct+env;
                    vec3 emissionTex=uHasEmissive==1?
                        texture(uEmissiveMap,
                          transformedUV(uEmissiveUVSet,uEmissiveTransform)).rgb:
                        vec3(1.0);
                    c+=uEmissive*emissionTex*uEmissiveStrength;
                    // Simple filmic preview exposure/tone mapping; no HDRI/IBL.
                    c=c/(c+vec3(0.75));
                    c=pow(clamp(c,0.0,1.0),vec3(1.0/2.2));
                }
                if(uMode==2) c=mix(c,vec3(0.04,0.94,0.94),0.75);
                else if(uMode==4) {
                    c=mix(c,vec3(0.05,0.98,0.99),0.85);
                    alpha=0.50;
                }
                outColor=vec4(c,alpha);
            }
        """.trimIndent()

        override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
            program = makeProgram()
            locMvp = GLES30.glGetUniformLocation(program, "uMVP")
            locMv = GLES30.glGetUniformLocation(program, "uMV")
            locMode = GLES30.glGetUniformLocation(program, "uMode")
            locPick = GLES30.glGetUniformLocation(program, "uPick")
            locPreview = GLES30.glGetUniformLocation(program,"uMaterialPreview")
            locBaseFactor = GLES30.glGetUniformLocation(program,"uBaseFactor")
            locMetallic = GLES30.glGetUniformLocation(program,"uMetallic")
            locRoughness = GLES30.glGetUniformLocation(program,"uRoughness")
            locEmissive = GLES30.glGetUniformLocation(program,"uEmissive")
            locEmissiveStrength = GLES30.glGetUniformLocation(program,"uEmissiveStrength")
            locAlphaMode = GLES30.glGetUniformLocation(program,"uAlphaMode")
            locAlphaCutoff = GLES30.glGetUniformLocation(program,"uAlphaCutoff")
            GLES30.glUseProgram(program)
            GLES30.glUniform1i(GLES30.glGetUniformLocation(program,"uBaseMap"),0)
            GLES30.glUniform1i(GLES30.glGetUniformLocation(program,"uMetallicMap"),1)
            GLES30.glUniform1i(GLES30.glGetUniformLocation(program,"uEmissiveMap"),2)
            val maxTex=IntArray(1)
            GLES30.glGetIntegerv(GLES30.GL_MAX_TEXTURE_SIZE,maxTex,0)
            maxTextureDimension=min(2048,maxTex[0].coerceAtLeast(512))
            textureHandles.clear()
            gpuImageBytes=0L
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

            // Interleaved positions, flat face normals, vertex color, UV0, UV1.
            // 3f+3f+4bytes+2f+2f = 44 bytes/vertex.
            val stride = 44
            val size = m.count.toLong()*3L*stride
            require(size <= 125L*1024*1024) { "Preview buffer exceeds mobile budget" }
            val bytes = ByteBuffer.allocateDirect(size.toInt()).order(ByteOrder.nativeOrder())
            val positions = m.xyz
            val indices = m.triangles
            val colors = m.importedVertexColors
            val uv0 = m.uv0
            val uv1 = m.uv1
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
                    val rgba=colors?.getOrNull(id) ?: 0xffffffff.toInt()
                    bytes.put(((rgba shr 16) and 255).toByte())
                    bytes.put(((rgba shr 8) and 255).toByte())
                    bytes.put((rgba and 255).toByte())
                    bytes.put(((rgba ushr 24) and 255).toByte())
                    bytes.putFloat(uv0?.getOrNull(id*2)?:0f)
                    bytes.putFloat(uv0?.getOrNull(id*2+1)?:0f)
                    bytes.putFloat(uv1?.getOrNull(id*2)?:0f)
                    bytes.putFloat(uv1?.getOrNull(id*2+1)?:0f)
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
            GLES30.glEnableVertexAttribArray(3)
            GLES30.glVertexAttribPointer(3,2,GLES30.GL_FLOAT,false,stride,28)
            GLES30.glEnableVertexAttribArray(4)
            GLES30.glVertexAttribPointer(4,2,GLES30.GL_FLOAT,false,stride,36)
            GLES30.glBindVertexArray(0)
            GLES30.glBindBuffer(GLES30.GL_ARRAY_BUFFER,0)
        }

        private fun glass(p: GeometryPart): Boolean {
            val n=p.sourceName.lowercase()
            return listOf("glass","glazing","window","windshield","transparent",
                "polycarbonate","acrylic","perspex").any { it in n }
        }

        private fun texture(m: GeometryMesh,index:Int,srgb:Boolean):Boolean {
            if(index !in m.surfaceAssets.textures.indices)return false
            val key=index to srgb
            val cached=textureHandles[key]
            if(cached!=null){
                GLES30.glBindTexture(GLES30.GL_TEXTURE_2D,cached)
                return true
            }
            val source=m.surfaceAssets.textures[index]
            val data=source.imageBytes?:return false
            val options=BitmapFactory.Options().apply{inJustDecodeBounds=true}
            BitmapFactory.decodeByteArray(data,0,data.size,options)
            if(options.outWidth<=0||options.outHeight<=0)return false
            var sample=1
            while(max(options.outWidth,options.outHeight)/sample>maxTextureDimension)
                sample*=2
            var w=(options.outWidth/sample).coerceAtLeast(1)
            var h=(options.outHeight/sample).coerceAtLeast(1)
            while(gpuImageBytes+w.toLong()*h*4>maxImageBytes &&
                max(w,h)>32){
                sample*=2
                w=(options.outWidth/sample).coerceAtLeast(1)
                h=(options.outHeight/sample).coerceAtLeast(1)
            }
            if(gpuImageBytes+w.toLong()*h*4>maxImageBytes)return false
            val decode=BitmapFactory.Options().apply{
                inSampleSize=sample
                inScaled=false
                inPreferredConfig=android.graphics.Bitmap.Config.ARGB_8888
                inPremultiplied=false
            }
            val bitmap=try{BitmapFactory.decodeByteArray(data,0,data.size,decode)}
                catch(_:OutOfMemoryError){null}
                catch(_:Exception){null}?:return false
            val handles=IntArray(1)
            GLES30.glGenTextures(1,handles,0)
            if(handles[0]==0){bitmap.recycle();return false}
            GLES30.glBindTexture(GLES30.GL_TEXTURE_2D,handles[0])
            val wrapS=if(source.wrapS in intArrayOf(33071,33648,10497))source.wrapS else 10497
            val wrapT=if(source.wrapT in intArrayOf(33071,33648,10497))source.wrapT else 10497
            GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D,GLES30.GL_TEXTURE_WRAP_S,wrapS)
            GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D,GLES30.GL_TEXTURE_WRAP_T,wrapT)
            val mag=if(source.magFilter==9728)9728 else 9729
            GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D,GLES30.GL_TEXTURE_MAG_FILTER,mag)
            val mipmap=source.minFilter in 9984..9987
            val minFilter=if(mipmap) source.minFilter else
                if(source.minFilter==9728)9728 else 9729
            GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D,GLES30.GL_TEXTURE_MIN_FILTER,minFilter)
            try{
                // Color/emissive maps are sRGB and sampled into linear space;
                // metallic-roughness maps remain linear, per glTF 2.0.
                GLUtils.texImage2D(GLES30.GL_TEXTURE_2D,0,
                    if(srgb)GLES30.GL_SRGB8_ALPHA8 else GLES30.GL_RGBA8,bitmap,0)
                if(mipmap)GLES30.glGenerateMipmap(GLES30.GL_TEXTURE_2D)
                val err=GLES30.glGetError()
                if(err!=GLES30.GL_NO_ERROR)throw IllegalStateException("Texture upload error $err")
            }catch(_:Exception){
                GLES30.glDeleteTextures(1,handles,0)
                return false
            }finally{bitmap.recycle()}
            gpuImageBytes+=bitmap.width.toLong()*bitmap.height*4
            textureHandles[key]=handles[0]
            return true
        }

        private fun texTransform(uniform:String,a:FloatArray){
            val matrix=floatArrayOf(
                a[0],a[3],0f, a[1],a[4],0f, a[2],a[5],1f)
            GLES30.glUniformMatrix3fv(
                GLES30.glGetUniformLocation(program,uniform),
                1,false,matrix,0)
        }

        private fun material(m:GeometryMesh,p:GeometryPart):GltfSurfaceMaterial {
            return m.surfaceAssets.materials.getOrNull(p.materialIndex)
                ?:GltfSurfaceMaterial("glTF default",floatArrayOf(1f,1f,1f,1f),
                    1f,1f,floatArrayOf(0f,0f,0f),1f)
        }

        private fun useMaterial(m:GeometryMesh,p:GeometryPart){
            val mat=material(m,p)
            GLES30.glUniform4fv(locBaseFactor,1,mat.baseColor,0)
            GLES30.glUniform1f(locMetallic,mat.metallic)
            GLES30.glUniform1f(locRoughness,mat.roughness)
            GLES30.glUniform3fv(locEmissive,1,mat.emissive,0)
            GLES30.glUniform1f(locEmissiveStrength,mat.emissiveStrength)
            GLES30.glUniform1i(locAlphaMode,when(mat.alphaMode){
                "BLEND"->2;"MASK"->1;else->0
            })
            GLES30.glUniform1f(locAlphaCutoff,mat.alphaCutoff)
            val specs=arrayOf(
                Triple(mat.baseColorTexture,true,mat.baseTexCoord),
                Triple(mat.metallicRoughnessTexture,false,mat.metallicTexCoord),
                Triple(mat.emissiveTexture,true,mat.emissiveTexCoord))
            val enabledNames=arrayOf("uHasBase","uHasMetallicRoughness","uHasEmissive")
            val setNames=arrayOf("uBaseUVSet","uMetallicUVSet","uEmissiveUVSet")
            val transNames=arrayOf("uBaseTransform","uMetallicTransform","uEmissiveTransform")
            val matrices=arrayOf(mat.baseTexTransform,mat.metallicTexTransform,mat.emissiveTexTransform)
            for(slot in 0..2) {
                val (index,srgb,uvSet)=specs[slot]
                GLES30.glActiveTexture(GLES30.GL_TEXTURE0+slot)
                val bound=texture(m,index,srgb)
                GLES30.glUniform1i(
                    GLES30.glGetUniformLocation(program,enabledNames[slot]),
                    if(bound)1 else 0)
                GLES30.glUniform1i(
                    GLES30.glGetUniformLocation(program,setNames[slot]),uvSet)
                texTransform(transNames[slot],matrices[slot])
            }
        }

        private fun materialIsBlended(m:GeometryMesh,p:GeometryPart):Boolean =
            material(m,p).alphaMode=="BLEND"

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
            GLES30.glUniform1i(locPreview,if(pbrEnabled && !picking)1 else 0)

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
            } else if(pbrEnabled) {
                // Actual source GLB materials. Opaque primitives first, then alpha.
                // No semantic name-based glass assumptions in this mode.
                for(p in m.parts) {
                    if(isolated && selected>=0 && p.id!=selected)continue
                    if(materialIsBlended(m,p))continue
                    mode(0)
                    useMaterial(m,p)
                    drawPart(p)
                }
                GLES30.glEnable(GLES30.GL_BLEND)
                GLES30.glBlendFunc(GLES30.GL_SRC_ALPHA,GLES30.GL_ONE_MINUS_SRC_ALPHA)
                GLES30.glDepthMask(false)
                for(p in m.parts) {
                    if(isolated && selected>=0 && p.id!=selected)continue
                    if(!materialIsBlended(m,p))continue
                    mode(0)
                    useMaterial(m,p)
                    drawPart(p)
                }
                if(selected>=0) {
                    val part=m.parts.getOrNull(selected)
                    if(part!=null){
                        mode(2)
                        useMaterial(m,part)
                        GLES30.glEnable(GLES30.GL_POLYGON_OFFSET_FILL)
                        GLES30.glPolygonOffset(-1f,-1f)
                        if(!materialIsBlended(m,part)){
                            GLES30.glDepthMask(true)
                            GLES30.glDisable(GLES30.GL_BLEND)
                        }
                        drawPart(part)
                        GLES30.glDisable(GLES30.GL_POLYGON_OFFSET_FILL)
                    }
                }
                GLES30.glDepthMask(true)
                GLES30.glDisable(GLES30.GL_BLEND)
            } else {
                mode(0)
                if (isolated && selected>=0) {
                    m.parts.getOrNull(selected)?.takeUnless(::glass)?.let(::drawPart)
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
