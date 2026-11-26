package com.assetwright.app.geometry

import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject

/** Material and texture metadata from the *original* GLB; never modifies it. */
data class GltfSurfaceMaterial(
    val name: String,
    val baseColor: FloatArray,
    val metallic: Float,
    val roughness: Float,
    val emissive: FloatArray,
    val emissiveStrength: Float,
    val baseColorTexture: Int = -1,
    val metallicRoughnessTexture: Int = -1,
    val emissiveTexture: Int = -1,
    val alphaMode: String = "OPAQUE",
    val alphaCutoff: Float = .5f,
    val doubleSided: Boolean = false,
    val baseTexCoord: Int = 0,
    val metallicTexCoord: Int = 0,
    val emissiveTexCoord: Int = 0,
    val baseTexTransform: FloatArray = floatArrayOf(1f,0f,0f,0f,1f,0f),
    val metallicTexTransform: FloatArray = floatArrayOf(1f,0f,0f,0f,1f,0f),
    val emissiveTexTransform: FloatArray = floatArrayOf(1f,0f,0f,0f,1f,0f)
)

data class GltfSurfaceTexture(
    val name: String,
    val imageBytes: ByteArray?,
    val mimeType: String,
    val minFilter: Int,
    val magFilter: Int,
    val wrapS: Int,
    val wrapT: Int,
    val unsupportedReason: String? = null
)

data class GltfPreviewAssets(
    val materials: List<GltfSurfaceMaterial>,
    val textures: List<GltfSurfaceTexture>,
    val warnings: List<String>
)

internal object GltfMaterialReader {
    private fun numbers(obj: JSONObject?, name: String, default: FloatArray): FloatArray {
        val array=obj?.optJSONArray(name) ?: return default.copyOf()
        return FloatArray(default.size) { i ->
            if(i<array.length()) array.optDouble(i,default[i].toDouble()).toFloat()
            else default[i]
        }
    }

    private fun texIndex(info: JSONObject?): Int = info?.optInt("index",-1) ?: -1
    private fun texCoord(info: JSONObject?): Int {
        val fallback=info?.optInt("texCoord",0)?:0
        return info?.optJSONObject("extensions")
            ?.optJSONObject("KHR_texture_transform")
            ?.optInt("texCoord",fallback)?:fallback
    }

    /** Packed 2×3 affine transform [a,b,c,d,e,f]: [u',v'] = [a*u+b*v+c,d*u+e*v+f]. */
    private fun transform(info: JSONObject?): FloatArray {
        val t=info?.optJSONObject("extensions")?.optJSONObject("KHR_texture_transform")
            ?: return floatArrayOf(1f,0f,0f,0f,1f,0f)
        val offset=numbers(t,"offset",floatArrayOf(0f,0f))
        val scale=numbers(t,"scale",floatArrayOf(1f,1f))
        val rotation=t.optDouble("rotation",0.0)
        val co=kotlin.math.cos(rotation).toFloat()
        val si=kotlin.math.sin(rotation).toFloat()
        return floatArrayOf(
            co*scale[0], -si*scale[1], offset[0],
            si*scale[0], co*scale[1], offset[1]
        )
    }

    fun read(root: JSONObject, data: ByteArray, binaryStart: Int, binarySize: Int): GltfPreviewAssets {
        val problems=ArrayList<String>()
        val images=root.optJSONArray("images")
        val imageBytes=ArrayList<ByteArray?>()
        val imageMime=ArrayList<String>()
        if(images!=null) for(i in 0 until images.length()){
            val obj=images.getJSONObject(i)
            var mime=obj.optString("mimeType","")
            var bytes:ByteArray?=null
            val view=obj.optInt("bufferView",-1)
            if(view>=0) {
                val views=root.getJSONArray("bufferViews")
                if(view in 0 until views.length()){
                    val entry=views.getJSONObject(view)
                    val offset=entry.optInt("byteOffset",0)
                    val len=entry.optInt("byteLength",0)
                    if(entry.optInt("buffer",0)==0 && offset>=0 && len>0 &&
                        offset.toLong()+len<=binarySize.toLong() && len<=24*1024*1024) {
                        bytes=data.copyOfRange(binaryStart+offset,binaryStart+offset+len)
                    } else problems.add("Image $i has an external, invalid, or oversized bufferView")
                }
            } else {
                val uri=obj.optString("uri","")
                if(uri.startsWith("data:",ignoreCase=true)) {
                    val comma=uri.indexOf(',')
                    if(comma>0 && uri.substring(0,comma).contains(";base64",true)) {
                        if(mime.isBlank()) mime=uri.substringAfter("data:").substringBefore(';')
                        try {
                            // Do not decode unbounded data into mobile memory.
                            if(uri.length<=32*1024*1024)
                                bytes=Base64.decode(uri.substring(comma+1),Base64.DEFAULT)
                        }catch(_:Exception){}
                    }
                } else if(uri.isNotBlank()) problems.add(
                    "Image $i uses an external URI; embed images in GLB for offline preview")
            }
            if(bytes==null) problems.add("Image $i is not available for native material preview")
            imageBytes.add(bytes)
            imageMime.add(mime)
        }

        val samplers=root.optJSONArray("samplers")
        val textureList=ArrayList<GltfSurfaceTexture>()
        val textures=root.optJSONArray("textures")
        if(textures!=null)for(i in 0 until textures.length()){
            val t=textures.getJSONObject(i)
            val ext=t.optJSONObject("extensions")
            val basis=ext?.optJSONObject("KHR_texture_basisu")
            val webp=ext?.optJSONObject("EXT_texture_webp")
            val source=basis?.optInt("source",-1)
                ?:webp?.optInt("source",-1) ?:t.optInt("source",-1)
            val samplerId=t.optInt("sampler",-1)
            val sampler=if(samplers!=null && samplerId in 0 until samplers.length())
                samplers.getJSONObject(samplerId) else JSONObject()
            val mime=imageMime.getOrNull(source)?:""
            val supported=mime.isBlank()||mime=="image/jpeg"||mime=="image/png"||mime=="image/webp"
            val reason=when {
                basis!=null -> "KTX2/Basis compressed texture requires transcoding; unsupported"
                !supported -> "Unsupported image format $mime"
                imageBytes.getOrNull(source)==null -> "Image is not embedded or readable"
                else -> null
            }
            if(reason!=null) problems.add("Texture $i: $reason")
            textureList.add(GltfSurfaceTexture(
                t.optString("name","Texture $i"),
                if(reason==null)imageBytes.getOrNull(source) else null,mime,
                sampler.optInt("minFilter",9987),sampler.optInt("magFilter",9729),
                sampler.optInt("wrapS",10497),sampler.optInt("wrapT",10497),reason
            ))
        }

        val matArray=root.optJSONArray("materials")
        val materialList=ArrayList<GltfSurfaceMaterial>()
        if(matArray!=null)for(i in 0 until matArray.length()){
            val mat=matArray.getJSONObject(i)
            val pbr=mat.optJSONObject("pbrMetallicRoughness")?:JSONObject()
            val bInfo=pbr.optJSONObject("baseColorTexture")
            val mrInfo=pbr.optJSONObject("metallicRoughnessTexture")
            val eInfo=mat.optJSONObject("emissiveTexture")
            val strength=mat.optJSONObject("extensions")
                ?.optJSONObject("KHR_materials_emissive_strength")
                ?.optDouble("emissiveStrength",1.0)?.toFloat()?:1f
            val alphaMode=mat.optString("alphaMode","OPAQUE")
            materialList.add(GltfSurfaceMaterial(
                name=mat.optString("name","Material $i"),
                baseColor=numbers(pbr,"baseColorFactor",floatArrayOf(1f,1f,1f,1f)),
                metallic=pbr.optDouble("metallicFactor",1.0).toFloat(),
                roughness=pbr.optDouble("roughnessFactor",1.0).toFloat(),
                emissive=numbers(mat,"emissiveFactor",floatArrayOf(0f,0f,0f)),
                emissiveStrength=strength,
                baseColorTexture=texIndex(bInfo),
                metallicRoughnessTexture=texIndex(mrInfo),
                emissiveTexture=texIndex(eInfo),
                alphaMode=alphaMode,
                alphaCutoff=mat.optDouble("alphaCutoff",0.5).toFloat(),
                doubleSided=mat.optBoolean("doubleSided",false),
                baseTexCoord=texCoord(bInfo),
                metallicTexCoord=texCoord(mrInfo),
                emissiveTexCoord=texCoord(eInfo),
                baseTexTransform=transform(bInfo),
                metallicTexTransform=transform(mrInfo),
                emissiveTexTransform=transform(eInfo)
            ))
        }
        return GltfPreviewAssets(materialList,textureList,problems)
    }
}
