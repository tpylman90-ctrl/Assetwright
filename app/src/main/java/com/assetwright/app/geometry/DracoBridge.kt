package com.assetwright.app.geometry

/** Google Draco 1.5.7, Apache-2.0. Decoding runs offline on Android. */
internal object DracoBridge {
    init { System.loadLibrary("assetwright_draco") }

    // Attribute descriptors are triples of unique ID, component count, and glTF component type.
    // The final returned buffer contains decoded triangle indices as unsigned 32-bit values.
    external fun decode(
        compressed: ByteArray,
        pointCount: Int,
        expectedIndices: Int,
        attributes: IntArray
    ): Array<ByteArray>
}
