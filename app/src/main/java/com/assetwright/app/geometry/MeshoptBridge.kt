package com.assetwright.app.geometry

/** Official meshoptimizer v1.3 decoder, MIT-licensed, bundled as an offline Android JNI library. */
internal object MeshoptBridge {
    init { System.loadLibrary("assetwright_meshopt") }
    external fun decode(source: ByteArray, count: Int, stride: Int, mode: String, filter: String): ByteArray
}
