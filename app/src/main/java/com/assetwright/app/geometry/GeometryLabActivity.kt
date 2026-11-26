package com.assetwright.app.geometry

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.*
import android.app.AlertDialog
import org.json.JSONObject
import android.graphics.Typeface
import androidx.activity.ComponentActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.activity.result.contract.ActivityResultContracts
import java.io.ByteArrayOutputStream
import java.util.Locale
import kotlin.concurrent.thread
import kotlin.math.*

/** Fully native Android geometry inspection. All source GLBs are read-only. */
class GeometryLabActivity : ComponentActivity() {
    private val modes=arrayOf(
        "1. Slicer: true triangle sections",
        "2. Curvature scanner",
        "3. Edge flow / crease scanner",
        "4. Connected geometry separator",
        "5. Shape difference scanner",
        "6. Surface reconstruction guides",
        "7. Recess / depth envelope",
        "8. Orthographic silhouettes",
        "9. Candidate feature detector",
        "10. Imported colored patch GLB"
    )
    private var model: GeometryMesh?=null
    private var reference:GeometryMesh?=null
    private var modelName="No model loaded"
    private var currentMode=0
    private var axis=2
    private var fraction=0.5f
    private var yaw=35f
    private var zoom=1f
    private lateinit var info:TextView
    private lateinit var drawing:ScanView
    private lateinit var viewAxis:Spinner
    private lateinit var wholeModel:ComponentModelView
    private lateinit var partPicker:Spinner
    private lateinit var partDetails:TextView
    private var reports:List<PartHealth> = emptyList()
    private val userPartLabels=mutableMapOf<Int,String>()
    private var selectedPart=-1
    private var expandedPreview=false

    private val selectModel=registerForActivityResult(ActivityResultContracts.OpenDocument()){uri->
        if(uri!=null)load(uri,false)
    }
    private val selectReference=registerForActivityResult(ActivityResultContracts.OpenDocument()){uri->
        if(uri!=null)load(uri,true)
    }
    private val exportModelingPacket=registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")){uri->
        if(uri!=null)write(uri,"json")
    }
    private val exportComponentCsv=registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")){uri->
        if(uri!=null)write(uri,"parts-csv")
    }
    private val exportComponentJson=registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")){uri->
        if(uri!=null)write(uri,"parts-json")
    }
    private val exportCsv=registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")){uri->
        if(uri!=null)write(uri,"csv")
    }
    private val exportImage=registerForActivityResult(ActivityResultContracts.CreateDocument("image/png")){uri->
        if(uri!=null)write(uri,"png")
    }
    private val exportReport=registerForActivityResult(ActivityResultContracts.CreateDocument("text/plain")){uri->
        if(uri!=null)write(uri,"txt")
    }
    private fun button(label:String, action:()->Unit):Button {
        return Button(this).apply {
            text=label
            isAllCaps=false
            setOnClickListener{action()}
            setTextColor(Color.WHITE)
            setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.rgb(34,77,88)))
        }
    }
    private fun label(text:String,bold:Boolean=false):TextView=TextView(this).apply{
        this.text=text
        setTextColor(if(bold)Color.WHITE else Color.rgb(185,206,218))
        textSize=if(bold)18f else 13f
        if(bold)typeface=Typeface.DEFAULT_BOLD
        setPadding(4,7,4,7)
    }
    private fun darkSpinnerAdapter(options: Array<String>): ArrayAdapter<String> {
        return object : ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, options) {
            override fun getView(position: Int, convertView: View?, parent: android.view.ViewGroup): View {
                val view = super.getView(position, convertView, parent)
                (view as? TextView)?.apply {
                    setTextColor(Color.WHITE)
                    textSize = 15f
                    setPadding(14, 13, 14, 13)
                }
                return view
            }
            override fun getDropDownView(position: Int, convertView: View?, parent: android.view.ViewGroup): View {
                val view = super.getDropDownView(position, convertView, parent)
                (view as? TextView)?.apply {
                    setTextColor(Color.WHITE)
                    setBackgroundColor(Color.rgb(27, 42, 55))
                    setPadding(16, 16, 16, 16)
                }
                return view
            }
        }.apply { setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
    }
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor=Color.rgb(12,20,29)
        window.navigationBarColor=Color.rgb(12,20,29)
        val root=ScrollView(this).apply{setBackgroundColor(Color.rgb(12,20,29))}
        // Android 15/16 enforces edge-to-edge layouts; avoid placing controls
        // underneath the phone status icons and navigation bar.
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or
                WindowInsetsCompat.Type.displayCutout())
            view.setPadding(0, bars.top, 0, bars.bottom)
            insets
        }
        val content=LinearLayout(this).apply{
            orientation=LinearLayout.VERTICAL
            setPadding(18,12,18,22)
        }
        root.addView(content)
        content.addView(label("ASSETWRIGHT  /  GEOMETRY LAB",true))
        content.addView(label("Native offline analysis • originals never edited"))
        val row=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        row.addView(button("Open GLB"){selectModel.launch(arrayOf("model/gltf-binary","application/octet-stream","*/*"))},
            LinearLayout.LayoutParams(0,-2,1f))
        row.addView(button("Compare GLB"){selectReference.launch(arrayOf("model/gltf-binary","application/octet-stream","*/*"))},
            LinearLayout.LayoutParams(0,-2,1f))
        content.addView(row)
        info=label("Open any standard or Meshopt-compressed GLB. Original model is never edited.")
        content.addView(info)
        content.addView(label("FULL ASSEMBLY  •  select a component",true))
        wholeModel=ComponentModelView(this)
        content.addView(wholeModel,LinearLayout.LayoutParams(-1,(resources.displayMetrics.density*360).toInt()))
        val cameraRow=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        val expandButton=button("Expand 3D view") {
            expandedPreview=!expandedPreview
            val heightDp=if(expandedPreview)min(690f,resources.displayMetrics.heightPixels/resources.displayMetrics.density*.75f) else 360f
            wholeModel.layoutParams=wholeModel.layoutParams.apply {
                height=(heightDp*resources.displayMetrics.density).toInt()
            }
            // Don't change selection or orbit when expanding the viewport.
            wholeModel.requestRender()
        }
        cameraRow.addView(expandButton,LinearLayout.LayoutParams(0,-2,1f))
        cameraRow.addView(button("Reset 3D camera") {
            wholeModel.yaw=35f
            wholeModel.pitch=19f
            wholeModel.zoom=1f
            wholeModel.requestRender()
        },LinearLayout.LayoutParams(0,-2,1f))
        content.addView(cameraRow)
        partPicker=Spinner(this)
        partPicker.adapter=darkSpinnerAdapter(arrayOf("Whole model — no component selected"))
        partPicker.setBackgroundColor(Color.rgb(29,44,56))
        partPicker.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{
            override fun onNothingSelected(p:android.widget.AdapterView<*>?){}
            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){
                selectedPart=i-1
                wholeModel.selectedId=selectedPart
                refreshPartDetails()
            }
        }
        wholeModel.onSelected={id->partPicker.setSelection(id+1)}
        content.addView(partPicker)
        val partButtons=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        partButtons.addView(button("Show full model"){
            wholeModel.isolate=false
            partPicker.setSelection(0)
        },LinearLayout.LayoutParams(0,-2,1f))
        partButtons.addView(button("Isolate selected"){
            if(selectedPart>=0)wholeModel.isolate=!wholeModel.isolate
            refreshPartDetails()
        },LinearLayout.LayoutParams(0,-2,1f))
        partButtons.addView(button("Label part"){labelSelectedPart()},
            LinearLayout.LayoutParams(0,-2,1f))
        content.addView(partButtons)
        partDetails=label("Select a part to inspect its individual geometry.")
        content.addView(partDetails)
        val componentExports=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        componentExports.addView(button("Components JSON"){
            exportComponentJson.launch("assetwright_component_report.json")
        },LinearLayout.LayoutParams(0,-2,1f))
        componentExports.addView(button("Components CSV"){
            exportComponentCsv.launch("assetwright_component_report.csv")
        },LinearLayout.LayoutParams(0,-2,1f))
        content.addView(componentExports)
        content.addView(label("Analysis view",true))
        drawing=ScanView()
        content.addView(drawing,LinearLayout.LayoutParams(-1,(resources.displayMetrics.density*340).toInt()))
        val spinner=Spinner(this)
        spinner.adapter=darkSpinnerAdapter(modes)
        spinner.setBackgroundColor(Color.rgb(29,44,56))
        spinner.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{
            override fun onNothingSelected(p:android.widget.AdapterView<*>?) {}
            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){
                currentMode=i;drawing.invalidate();updateSummary()
            }
        }
        content.addView(spinner)
        content.addView(label("Cut orientation"))
        viewAxis=Spinner(this)
        viewAxis.adapter=darkSpinnerAdapter(
            arrayOf("X plane: front/rear","Y plane: horizontal","Z plane: left/right"))
        viewAxis.setSelection(2)
        viewAxis.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{
            override fun onNothingSelected(p:android.widget.AdapterView<*>?) {}
            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){
                axis=i;drawing.invalidate()
            }
        }
        content.addView(viewAxis)
        content.addView(label("Slice location"))
        content.addView(SeekBar(this).apply{
            max=100;progress=50
            setOnSeekBarChangeListener(object:android.widget.SeekBar.OnSeekBarChangeListener{
                override fun onStartTrackingTouch(s:SeekBar?){}
                override fun onStopTrackingTouch(s:SeekBar?){}
                override fun onProgressChanged(s:SeekBar?,p:Int,from:Boolean){
                    fraction=p/100f;drawing.invalidate()
                }
            })
        })
        content.addView(label("Rotate three-quarter view"))
        content.addView(SeekBar(this).apply{
            max=360;progress=35
            setOnSeekBarChangeListener(object:android.widget.SeekBar.OnSeekBarChangeListener{
                override fun onStartTrackingTouch(s:SeekBar?){}
                override fun onStopTrackingTouch(s:SeekBar?){}
                override fun onProgressChanged(s:SeekBar?,p:Int,from:Boolean){
                    yaw=p.toFloat();drawing.invalidate()
                }
            })
        })
        content.addView(label("Zoom"))
        content.addView(SeekBar(this).apply{
            max=200;progress=75
            setOnSeekBarChangeListener(object:android.widget.SeekBar.OnSeekBarChangeListener{
                override fun onStartTrackingTouch(s:SeekBar?){}
                override fun onStopTrackingTouch(s:SeekBar?){}
                override fun onProgressChanged(s:SeekBar?,p:Int,from:Boolean){
                    zoom=0.5f+p/100f;drawing.invalidate()
                }
            })
        })
        val out=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        out.addView(button("Export CSV"){exportCsv.launch("assetwright_geometry_"+currentMode+".csv")},
            LinearLayout.LayoutParams(0,-2,1f))
        out.addView(button("Save PNG"){exportImage.launch("assetwright_scan_"+currentMode+".png")},
            LinearLayout.LayoutParams(0,-2,1f))
        out.addView(button("Report"){exportReport.launch("assetwright_report.txt")},
            LinearLayout.LayoutParams(0,-2,1f))
        content.addView(out)
        content.addView(button("EXPORT MODELING DATA  •  JSON FOR CHATGPT"){
            exportModelingPacket.launch("assetwright_modeling_packet.json")
        })
        content.addView(label("Import surface_regions_30deg.glb or side_region_candidate_cutaway.glb, select mode 10 to display colored surface candidates. This is a wireframe diagnostic view, not a shaded CAD renderer."))
        content.addView(label("Precise slice intersections, graph-based curvature, crease severity, mesh islands, sampled shape differences, envelope reconstruction guides, vertical thickness, silhouettes and feature candidates. Meshopt-compressed GLBs open directly; Draco-compressed GLBs still need conversion. Exports are diagnostic, not automatically retopologized surfaces."))
        setContentView(root)
    }
    override fun onPause() {
        if(::wholeModel.isInitialized) wholeModel.onPause()
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        if(::wholeModel.isInitialized) wholeModel.onResume()
    }

    private fun refreshPartDetails() {
        val m=model ?: return
        val report=reports.getOrNull(selectedPart)
        partDetails.text=if(report==null) {
            "Full assembly • "+reports.size+" source components • "+m.count+
                " triangles. Select or tap a part for independent diagnostics."
        } else report.humanSummary(userPartLabels[selectedPart])+
            "\nPreview: "+if(wholeModel.isolate)"isolated component" else "full assembly, selected part highlighted"
    }
    private fun labelSelectedPart() {
        if(selectedPart<0 || reports.getOrNull(selectedPart)==null) {
            Toast.makeText(this,"Choose a component first",Toast.LENGTH_SHORT).show()
            return
        }
        val options=arrayOf("Robotic arm","Gripper","Battery cassette","Enclosure",
            "Control cabinet","Custom label")
        AlertDialog.Builder(this).setTitle("Identify this component")
            .setItems(options){_,choice->
                if(choice==5) {
                    val input=EditText(this)
                    input.setText(userPartLabels[selectedPart]?:reports[selectedPart].source.sourceName)
                    AlertDialog.Builder(this).setTitle("Custom part label")
                        .setView(input).setPositiveButton("Save"){_,_->
                            userPartLabels[selectedPart]=input.text.toString().trim()
                            refreshPartPicker()
                        }.setNegativeButton("Cancel",null).show()
                }else {
                    userPartLabels[selectedPart]=options[choice]
                    refreshPartPicker()
                }
            }.show()
    }
    private fun refreshPartPicker() {
        val current=selectedPart
        val names=arrayOf("Whole model — no component selected")+
            reports.map { r->
                val alias=userPartLabels[r.source.id]
                val name=alias?.takeIf{it.isNotBlank()}?:r.source.sourceName
                (r.source.id+1).toString()+". "+name+" ("+r.triangles+" tris)"
            }.toTypedArray()
        partPicker.adapter=darkSpinnerAdapter(names)
        partPicker.setSelection(current+1)
        refreshPartDetails()
    }
    private fun componentsCsv():String=buildString {
        append("id,name,source_name,triangles,vertices,triangle_density,degenerate_faces,boundary_edges,nonmanifold_edges,sharp_vertex_fraction,high_bending_fraction,flags\n")
        for(r in reports) {
            fun quote(v:String)="\""+v.replace("\"","\"\"")+"\""
            append(r.source.id).append(',').append(quote(userPartLabels[r.source.id]?:r.source.sourceName))
            append(',').append(quote(r.source.sourceName)).append(',')
            append(r.triangles).append(',').append(r.vertices).append(',').append(r.triangleDensity)
            append(',').append(r.degenerateTriangles).append(',').append(r.boundaryEdges?:"")
            append(',').append(r.nonmanifoldEdges?:"").append(',')
            append(r.sharpVertexFraction).append(',').append(r.highCurvatureFraction)
            append(',').append(quote(r.flags.joinToString("; "))).append('\n')
        }
    }
    private fun updateSummary(){
        val m=model?:return
        info.text=modelName+" • "+m.n+" vertices • "+m.count+" triangles\n"+
            when(currentMode){
                0->"Exact triangle-plane cuts"
                1->"Signed local bending proxy"
                2->"Adjacent face-normal crease angles"
                3->"Connected mesh islands (not semantic parts)"
                4->"Normalized nearest-vertex approximation"+if(reference==null)" • load compare GLB" else " • reference loaded"
                5->"Section-contour reconstruction guides"
                6->"Vertical outer-envelope depth proxy"
                7->"Side, top and front silhouettes"
                9->"Reads actual GLB COLOR_0 vertex colors; load the derived patch scan GLB"
                else->"Candidates only: ridges, valleys, boundaries"
            }
    }
    private fun load(uri:Uri,comparison:Boolean){
        info.text="Opening and analyzing model locally…"
        thread(name="Assetwright Geometry Lab Import"){
            try {
                val bytes=contentResolver.openInputStream(uri)?.use{it.readBytes()}?:error("Cannot read selected file")
                val name=uri.lastPathSegment?.substringAfterLast('/')?:"model.glb"
                val parsed=GeometryMesh.parse(bytes,name)
                // Do the heavy graph analyses away from the UI thread.
                parsed.sharpness;parsed.curvature;parsed.islands
                val perPart=if(comparison)emptyList() else parsed.partHealth()
                runOnUiThread{
                    if(comparison)reference=parsed else {
                        model=parsed;modelName=name
                        reports=perPart
                        userPartLabels.clear()
                        selectedPart=-1
                        wholeModel.mesh=parsed
                        wholeModel.isolate=false
                        refreshPartPicker()
                    }
                    updateSummary();drawing.invalidate()
                }
            } catch(ex:Exception){
                runOnUiThread {
                    info.text="Import failed: "+(ex.message?:"unknown error")+
                        "\nOriginal files remain unchanged."
                }
            }
        }
    }
    private fun write(uri:Uri,kind:String){
        val m=model?:return
        thread(name="Assetwright Geometry Lab Export"){
            try {
                contentResolver.openOutputStream(uri)?.use{stream->
                    when(kind){
                        "csv"->stream.write(m.csv(currentMode,axis,fraction).toByteArray(Charsets.UTF_8))
                        "txt"->stream.write((m.report(reference)+"\n\nCOMPONENT DIAGNOSTICS\n"+
                            reports.joinToString("\n\n"){it.humanSummary(userPartLabels[it.source.id])}
                        ).toByteArray(Charsets.UTF_8))
                        "json"-> {
                            val combined=JSONObject(m.modelingPacket(axis,reference))
                            combined.put("component_inspection",JSONObject(m.componentInspectionJson(
                                reports,userPartLabels,selectedPart.takeIf{it>=0})))
                            stream.write(combined.toString(2).toByteArray(Charsets.UTF_8))
                        }
                        "parts-json"->stream.write(m.componentInspectionJson(
                            reports,userPartLabels,selectedPart.takeIf{it>=0}).toByteArray(Charsets.UTF_8))
                        "parts-csv"->stream.write(componentsCsv().toByteArray(Charsets.UTF_8))
                        else -> {
                            val bmp=Bitmap.createBitmap(drawing.width.coerceAtLeast(1),drawing.height.coerceAtLeast(1),Bitmap.Config.ARGB_8888)
                            val c=Canvas(bmp);drawing.draw(c)
                            bmp.compress(Bitmap.CompressFormat.PNG,100,stream);bmp.recycle()
                        }
                    }
                }?:error("Cannot save file")
                runOnUiThread{Toast.makeText(this,"Saved geometry analysis",Toast.LENGTH_SHORT).show()}
            }catch(ex:Exception){
                runOnUiThread{Toast.makeText(this,"Export failed: "+ex.message,Toast.LENGTH_LONG).show()}
            }
        }
    }
    private inner class ScanView:View(this@GeometryLabActivity){
        private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{strokeWidth=1.2f}
        private val bg=Color.rgb(17,28,40)
        private val cyan=Color.rgb(88,234,235)
        private fun tone(x:Float):Int {
            val z=x.coerceIn(-1f,1f)
            return if(z>0)Color.rgb((110+145*z).toInt(),(187-95*z).toInt(),(225-185*z).toInt())
            else Color.rgb((75+50*(1+z)).toInt(),(80+120*(1+z)).toInt(),(170+65*(1+z)).toInt())
        }
        override fun onDraw(canvas:Canvas) {
            super.onDraw(canvas);canvas.drawColor(bg)
            val m=model?:run {
                paint.color=Color.LTGRAY;paint.textSize=32f
                canvas.drawText("Import a GLB to begin inspection",24f,height/2f,paint);return
            }
            val b=m.limits
            val span=(0..2).maxOf{b[it+3]-b[it]}.coerceAtLeast(0.00001f)
            val center=FloatArray(3){(b[it]+b[it+3])/2f}
            val c=cos(yaw*PI.toFloat()/180f);val s=sin(yaw*PI.toFloat()/180f)
            val scale=min(width,height)*0.82f/span*zoom
            fun position(x:Float,y:Float,z:Float):Pair<Float,Float>{
                val side=x*c+z*s
                return Pair(width/2f+side*scale,height*0.52f-(y*0.86f-(x*s-z*c)*0.18f)*scale)
            }
            fun project(a:FloatArray): Pair<Float, Float> = position(a[0]-center[0],a[1]-center[1],a[2]-center[2])
            if(currentMode==6){
                // Top-projection per-cell height span: interpretable as an envelope, not ray-cast.
                val grid=30;val thickness=m.depth(grid)
                val dx=(b[3]-b[0])/grid;val dz=(b[5]-b[2])/grid
                for(i in thickness.indices){
                    val z=i/grid;val x=i%grid
                    val d=thickness[i];if(!d.isFinite())continue
                    val p=position(b[0]+(x+0.5f)*dx-center[0],0f,b[2]+(z+0.5f)*dz-center[2])
                    paint.color=tone((d/span*5f-0.4f).coerceIn(-1f,1f))
                    paint.style=Paint.Style.FILL
                    canvas.drawCircle(p.first,p.second,max(2f,scale*max(dx,dz)*0.35f),paint)
                }
            } else if(currentMode==0 || currentMode==5) {
                val lines=m.slice(axis,fraction)
                paint.color=cyan;paint.style=Paint.Style.STROKE;paint.strokeWidth=2f
                for(l in lines) {
                    val a=project(l.a);val d=project(l.b)
                    canvas.drawLine(a.first,a.second,d.first,d.second,paint)
                }
                paint.style=Paint.Style.FILL
                paint.textSize=23f;paint.color=Color.WHITE
                canvas.drawText("Cut segments: "+lines.size,12f,30f,paint)
            } else if(currentMode==7){
                val sides=intArrayOf(0,1,2)
                for((k,axis0) in sides.withIndex()){
                    val outline=m.silhouette(axis0)
                    val x0=width*(0.17f+k*0.33f)
                    val y0=height*0.55f
                    val sorted=outline.chunked(2)
                    val u=if(axis0==0)2 else 0
                    val v=if(axis0==1)2 else 1
                    val cx=(b[u]+b[u+3])/2f
                    val cy=(b[v]+b[v+3])/2f
                    paint.color=when(k){0->cyan;1->Color.rgb(248,174,72);else->Color.rgb(226,108,161)}
                    paint.strokeWidth=2f
                    val local=min(width / 3f, height.toFloat()) * 0.75f / span
                    for(pair in sorted) if(pair.size==2) {
                        val lo=pair[0];val hi=pair[1]
                        canvas.drawLine(x0+(lo[0]-cx)*local,y0-(lo[1]-cy)*local,
                            x0+(hi[0]-cx)*local,y0-(hi[1]-cy)*local,paint)
                    }
                }
            } else {
                // Sample real triangle mesh; camera is orthographic and rotatable.
                val step=max(1,m.count/7000)
                val sharp=if(currentMode==2||currentMode==8)m.sharpness else null
                val curve=if(currentMode==1||currentMode==8)m.curvature else null
                val groups=if(currentMode==3)m.islands else null
                paint.style=Paint.Style.STROKE;paint.strokeWidth=1.15f
                val points=m.xyz;val inds=m.triangles
                for(t in 0 until m.count step step) {
                    val a=inds[t*3];val d=inds[t*3+1];val e=inds[t*3+2]
                    val mid=(sharp?.get(a)?:0f)/90f
                    paint.color=when(currentMode){
                        1->tone(curve?.get(a)?:0f)
                        2->tone((mid*2f-0.4f).coerceIn(-1f,1f))
                        3->{
                            val k=groups?.get(a)?:0
                            Color.rgb(70+(k*83)%165,85+(k*127)%150,110+(k*61)%135)
                        }
                        8->if((sharp?.get(a)?:0f)>35f)Color.rgb(246,149,68)
                            else tone(curve?.get(a)?:0f)
                        9->m.importedVertexColors?.get(a)?:Color.rgb(132,190,198)
                        else->Color.rgb(132,190,198)
                    }
                    val p=position(points[a*3]-center[0],points[a*3+1]-center[1],points[a*3+2]-center[2])
                    val q=position(points[d*3]-center[0],points[d*3+1]-center[1],points[d*3+2]-center[2])
                    val r=position(points[e*3]-center[0],points[e*3+1]-center[1],points[e*3+2]-center[2])
                    canvas.drawLine(p.first,p.second,q.first,q.second,paint)
                    canvas.drawLine(q.first,q.second,r.first,r.second,paint)
                    canvas.drawLine(r.first,r.second,p.first,p.second,paint)
                }
                if(currentMode==4 && reference!=null){
                    val ref=reference!!;val rb=ref.limits
                    val refc=FloatArray(3){(rb[it]+rb[it+3])/2f}
                    val stepRef=max(1,ref.n/1300)
                    paint.color=Color.rgb(255,110,100)
                    paint.style=Paint.Style.FILL
                    for(v in 0 until ref.n step stepRef){
                        val p=position((ref.xyz[v*3]-refc[0])*(b[3]-b[0])/(rb[3]-rb[0]).coerceAtLeast(1e-6f),
                            (ref.xyz[v*3+1]-refc[1])*(b[4]-b[1])/(rb[4]-rb[1]).coerceAtLeast(1e-6f),
                            (ref.xyz[v*3+2]-refc[2])*(b[5]-b[2])/(rb[5]-rb[2]).coerceAtLeast(1e-6f))
                        canvas.drawCircle(p.first,p.second,1.5f,paint)
                    }
                }
            }
            paint.style=Paint.Style.FILL
            paint.color=Color.WHITE
            paint.textSize=18f
            canvas.drawText(modes[currentMode].substringAfter(". "),12f,height-17f,paint)
        }
    }
}
