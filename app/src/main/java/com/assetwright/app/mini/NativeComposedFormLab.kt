package com.assetwright.app.mini

/**
 * First original, research-only MULTI-OPERATION native geometry lab.
 *
 * Every geometric displacement originates from our own AdvancedFormLab,
 * with shared exact mesh vertex IDs, closed topology and bounded controls.
 * A program composes distinct, known native deformation fields on a SINGLE
 * connected shell. This is additive native displacement composition, NOT
 * Boolean CAD, a general text-to-3D model, or a pretrained 3D generator.
 *
 * The operation grammar and command program are explicit training labels.
 * A future OWN student can learn to predict these programs and compare
 * the resulting actual GLBs; this class never claims it learned them yet.
 */
object NativeComposedFormLab {
    data class Command(val operation: AdvancedFormOperation, val strength: Float)
    data class Program(
        val length: Float,
        val width: Float,
        val height: Float,
        val commands: List<Command>,
        val segments: Int = 24,
        val stations: Int = 24
    )

    // A canonical additive construction grammar prevents duplicate or
    // inconsistent operation program ordering in source supervision.
    val canonicalOrder = listOf(
        AdvancedFormOperation.SUPERELLIPSE_PROFILE,
        AdvancedFormOperation.SECTION_LOFT,
        AdvancedFormOperation.RIBBED_FAIRING,
        AdvancedFormOperation.LOWER_RECESS,
        AdvancedFormOperation.SECTION_TWIST,
        AdvancedFormOperation.TANGENT_SWEEP
    )

    fun generate(program: Program): MeshPart {
        require(program.commands.size in 2..4) {
            "Research grammar needs two to four distinct native operations"
        }
        val commands = program.commands
        val identities = commands.map { it.operation }
        require(identities.size == identities.toSet().size) {
            "Repeated native operation is not a valid compound lesson"
        }
        require(identities == identities.sortedBy { canonicalOrder.indexOf(it) }) {
            "Original native construction program violates canonical order"
        }
        require(commands.all { it.strength.isFinite() &&
            it.strength in 0.02f..0.72f }) {
            "All compound native deformation strengths must be bounded"
        }
        require(commands.sumOf { it.strength.toDouble() } <= 2.15) {
            "Compound native shell deformation exceeds conservative budget"
        }
        val originSpec = AdvancedFormSpec(
            AdvancedFormOperation.SECTION_LOFT,
            program.length, program.width, program.height,
            0f, program.segments, program.stations
        )
        val base = AdvancedFormLab.generate(originSpec)
        // Source domain: exact same vertices/triangle ordering in all
        // original advanced-form operations, with zero deformation base.
        val edits = commands.map { entry ->
            val native = AdvancedFormLab.generate(originSpec.copy(
                operation = entry.operation,strength = entry.strength))
            require(native.indices == base.indices &&
                native.vertices.size == base.vertices.size) {
                "Cannot compose unmatched original native mesh topology"
            }
            native
        }
        val vertices = base.vertices.indices.map { i ->
            val v = base.vertices[i]
            var xx = v.x
            var yy = v.y
            var zz = v.z
            for (part in edits) {
                val changed = part.vertices[i]
                xx += changed.x-v.x
                yy += changed.y-v.y
                zz += changed.z-v.z
            }
            Vec3(xx,yy,zz)
        }
        var volume6 = 0.0
        for (i in base.indices.indices step 3) {
            val aa=vertices[base.indices[i]]
            val bb=vertices[base.indices[i+1]]
            val cc=vertices[base.indices[i+2]]
            val u=bb-aa
            val v=cc-aa
            val cross=u.cross(v)
            val area2=cross.x*cross.x+cross.y*cross.y+cross.z*cross.z
            require(area2.isFinite() && area2>1e-11f) {
                "Compound original indexed geometry contains collapsed triangles"
            }
            volume6 += (aa.x*cross.x+aa.y*cross.y+aa.z*cross.z).toDouble()
        }
        require(volume6.isFinite() && volume6>1e-5) {
            "Compound deformation lost positive closed shell orientation"
        }
        require(vertices.all { it.x.isFinite() && it.y.isFinite() && it.z.isFinite() }) {
            "Compound original geometry contains unbounded positions"
        }
        return MeshPart(
            "Original multi-operation form",0x98B8D4,vertices,base.indices)
    }

    /** Only an ORIGINAL native GLB is emitted; never an outside model. */
    fun asGeneratedAsset(program: Program): GeneratedAsset {
        val part=generate(program)
        val spec=VehicleSpec(
            title="Native compounded geometry research",
            length=program.length,
            width=program.width,
            roofHeight=program.height,
            canopyLength=1.8f,
            noseTaper=.55f,
            rearHaunch=1.07f,
            quality="Mobile",
            sourcePrompt="Research only: original additive native compound geometry"
        )
        return GeneratedAsset(spec,listOf(part))
    }
}
