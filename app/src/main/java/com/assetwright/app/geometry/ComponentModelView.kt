package com.assetwright.app.geometry

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import kotlin.math.*

/**
 * Read-only whole-model preview: solid triangle fill, orbit/pinch and tap selection.
 * To protect Android memory this rasterizes a sampled set of source faces,
 * but component health and numeric exports always analyze the full GLB.
 * Canvas painter sorting is approximate; it is not a hardware Z-buffer.
 */
class ComponentModelView(context: Context): View(context) {
    var mesh:GeometryMesh?=null
        set(value){field=value;previewFaces=value?.let(::sample)?:IntArray(0);selectedId=-1;invalidate()}
    var selectedId:Int=-1
        set(value){field=value;invalidate()}
    var isolate=false
        set(value){field=value;invalidate()}
    var onSelected:((Int)->Unit)?=null
    var yaw=35f
        set(value){field=value;invalidate()}
    var pitch=22f
        set(value){field=value.coerceIn(-75f,75f);invalidate()}
    var zoom=1f
        set(value){field=value.coerceIn(.3f,3.3f);invalidate()}
    private val painter=Paint(Paint.ANTI_ALIAS_FLAG)
    private val path=Path()
    private var previewFaces=IntArray(0)
    private var previousX=0f
    private var previousY=0f
    private var moved=false
    private data class Face(val xy:FloatArray,val depth:Float,val id:Int,val color:Int)
    private var hitFaces:List<Face> = emptyList()
    private val pinch=ScaleGestureDetector(context,object:ScaleGestureDetector.SimpleOnScaleGestureListener(){
        override fun onScale(d:ScaleGestureDetector):Boolean{zoom*=d.scaleFactor;return true}
    })
    private fun sample(m:GeometryMesh):IntArray{
        val totalBudget=9500
        if(m.count<=totalBudget)return IntArray(m.count){it}
        val chosen=ArrayList<Int>(totalBudget)
        // Always include at least some faces from every source primitive.
        val count=m.parts.size.coerceAtLeast(1)
        val quota=(totalBudget/count).coerceAtLeast(1)
        for(p in m.parts){
            val n=min(p.triangleCount,quota)
            for(j in 0 until n) {
                val ix=p.firstTriangle+(j.toLong()*p.triangleCount/n).toInt()
                if(ix in 0 until m.count)chosen.add(ix)
            }
        }
        return chosen.toIntArray()
    }
    private fun partForTriangle(t:Int,parts:List<GeometryPart>):Int{
        var lo=0;var hi=parts.lastIndex
        while(lo<=hi){
            val mid=(lo+hi) ushr 1
            val p=parts[mid]
            if(t<p.firstTriangle)hi=mid-1
            else if(t>=p.firstTriangle+p.triangleCount)lo=mid+1
            else return p.id
        };return -1
    }
    private fun contains(f:Face,x:Float,y:Float):Boolean{
        val p=f.xy
        fun side(ax:Float,ay:Float,bx:Float,by:Float)=
            (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        val a=side(p[0],p[1],p[2],p[3])
        val b=side(p[2],p[3],p[4],p[5])
        val c=side(p[4],p[5],p[0],p[1])
        return !(a<0f||b<0f||c<0f)||!(a>0f||b>0f||c>0f)
    }
    override fun onTouchEvent(e:MotionEvent):Boolean {
        pinch.onTouchEvent(e)
        when(e.actionMasked){
            MotionEvent.ACTION_DOWN->{previousX=e.x;previousY=e.y;moved=false;return true}
            MotionEvent.ACTION_POINTER_DOWN->{moved=true;return true}
            MotionEvent.ACTION_MOVE->{
                if(e.pointerCount==1 && !pinch.isInProgress){
                    val dx=e.x-previousX;val dy=e.y-previousY
                    if(abs(dx)>1||abs(dy)>1){
                        yaw+=dx*.45f;pitch+=dy*.35f;moved=true
                    }
                    previousX=e.x;previousY=e.y
                } else moved=true
                return true
            }
            MotionEvent.ACTION_UP->{
                if(!moved) {
                    val hit=hitFaces.asReversed().firstOrNull{contains(it,e.x,e.y)}
                    if(hit!=null && hit.id>=0){selectedId=hit.id;onSelected?.invoke(hit.id)}
                }
                performClick();return true
            }
            MotionEvent.ACTION_CANCEL->return true
        }
        return true
    }
    override fun performClick():Boolean{super.performClick();return true}
    override fun onDraw(canvas:Canvas){
        super.onDraw(canvas);canvas.drawColor(Color.rgb(15,27,39))
        val m=mesh?:run{
            painter.color=Color.LTGRAY;painter.textSize=21f
            canvas.drawText("Open a GLB to view the entire assembly",14f,height*.5f,painter)
            return
        }
        val b=m.limits
        val xc=(b[0]+b[3])*.5f;val yc=(b[1]+b[4])*.5f;val zc=(b[2]+b[5])*.5f
        val span=maxOf(b[3]-b[0],b[4]-b[1],b[5]-b[2]).coerceAtLeast(.00001f)
        val scale=min(width.toFloat(),height.toFloat())*.73f/span*zoom
        val a=yaw*PI.toFloat()/180f;val q=pitch*PI.toFloat()/180f
        val ca=cos(a);val sa=sin(a);val cq=cos(q);val sq=sin(q)
        fun project(i:Int):FloatArray{
            val x=m.xyz[3*i]-xc;val y=m.xyz[3*i+1]-yc;val z=m.xyz[3*i+2]-zc
            val u=ca*x-sa*z;val d=sa*x+ca*z
            val v=cq*y-sq*d;val depth=sq*y+cq*d
            return floatArrayOf(width*.5f+u*scale,height*.52f-v*scale,depth)
        }
        val faces=ArrayList<Face>(previewFaces.size)
        for(t in previewFaces){
            val id=partForTriangle(t,m.parts)
            if(isolate && selectedId>=0 && id!=selectedId)continue
            val a0=project(m.triangles[3*t])
            val b0=project(m.triangles[3*t+1])
            val c0=project(m.triangles[3*t+2])
            val area=abs((b0[0]-a0[0])*(c0[1]-a0[1])-(b0[1]-a0[1])*(c0[0]-a0[0]))
            if(area<.75f)continue
            val original=m.importedVertexColors?.get(m.triangles[3*t])?:Color.rgb(162,185,197)
            faces.add(Face(floatArrayOf(a0[0],a0[1],b0[0],b0[1],c0[0],c0[1]),
                (a0[2]+b0[2]+c0[2])/3f,id,original))
        }
        faces.sortBy{it.depth}
        hitFaces=faces
        for(f in faces){
            val active=selectedId>=0&&f.id==selectedId
            val dim=selectedId>=0&&!active
            painter.style=Paint.Style.FILL
            val base=f.color
            painter.color=if(active)Color.rgb(34,209,223) else Color.rgb(
                (Color.red(base)*.75f).toInt(),(Color.green(base)*.75f).toInt(),
                (Color.blue(base)*.75f).toInt())
            painter.alpha=if(dim)92 else 255
            path.reset();path.moveTo(f.xy[0],f.xy[1]);path.lineTo(f.xy[2],f.xy[3])
            path.lineTo(f.xy[4],f.xy[5]);path.close()
            canvas.drawPath(path,painter)
            if(active){
                painter.alpha=255;painter.color=Color.rgb(150,250,255)
                painter.style=Paint.Style.STROKE;painter.strokeWidth=.7f
                canvas.drawPath(path,painter)
            }
        }
        painter.style=Paint.Style.FILL;painter.color=Color.WHITE;painter.alpha=255
        painter.textSize=16f
        canvas.drawText("FULL MODEL • drag orbit • pinch zoom • tap part",10f,22f,painter)
        painter.textSize=13f
        canvas.drawText("Preview " + previewFaces.size + "/" + m.count +
            " triangles • reports use all geometry",10f,height-12f,painter)
    }
}
