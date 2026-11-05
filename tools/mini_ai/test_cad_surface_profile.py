"""Offline CAD relationship learning tests; no downloaded Python executes."""
import unittest
try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("Relative CAD research requires optional NumPy")
from cad_surface_profile_features import extract,SIZE,NAMES,SCHEMA
from cad_surface_student_v2 import fit,predict,source_x,verify
from test_cad_surface_transfer import corpus

class CadSurfaceProfileTests(unittest.TestCase):
    def test_real_numeric_relationships_are_not_only_a_bag_of_averages(self):
        source=("import cadquery as cq\n"
                "result=cq.Workplane('XY').rect(6,2).extrude(3)"
                ".faces('>Z').workplane().circle(1).cutBlind(-1)"
                ".edges().fillet(0.25)\n")
        x=extract(source)
        self.assertEqual(len(x),SIZE)
        self.assertAlmostEqual(x[NAMES.index("base_min_over_major")],2/6,places=6)
        self.assertAlmostEqual(x[NAMES.index("sketch_second_over_first")],2/6,places=6)
        self.assertAlmostEqual(x[NAMES.index("extrude_over_base")],3/6,places=6)
        self.assertAlmostEqual(x[NAMES.index("cut_depth_over_base")],1/6,places=6)
        self.assertAlmostEqual(x[NAMES.index("fillet_radius_over_base")],.25/6,places=6)
        self.assertEqual(x[NAMES.index("cut_depth_sign")],-1.)
        self.assertTrue(all(np.isfinite(x)))

    def test_statics_resolve_safe_assigned_dimensions_without_executing_python(self):
        source=("unit=2.0\n"
                "width=unit*3\n"
                "height=width/3\n"
                "depth=unit+1\n"
                "result=cq.Workplane('XY').rect(width,height).extrude(depth).fillet(unit/8)\n")
        data=extract(source)
        self.assertAlmostEqual(data[NAMES.index("base_min_over_major")],1/3,places=6)
        self.assertAlmostEqual(data[NAMES.index("extrude_over_base")],.5,places=6)
        self.assertAlmostEqual(data[NAMES.index("fillet_radius_over_base")],.25/6,places=6)
        from safe_cad_numeric_resolver import pure_numeric
        import ast
        self.assertIsNone(pure_numeric(ast.parse("unknown(2)",mode="eval").body,{}))
        self.assertIsNone(pure_numeric(ast.parse("10**999",mode="eval").body,{}))

    def test_untrusted_expressions_cannot_execute_or_create_model(self):
        from pathlib import Path
        sentinel=Path("/tmp/assetwright-cad-v2-must-not-execute")
        evil=("__import__('os').system('touch /tmp/assetwright-cad-v2-must-not-execute')\n"
              "result=cq.Workplane().rect(4,2).extrude(2)\n")
        result=extract(evil)
        self.assertEqual(len(result),SIZE)
        self.assertFalse(sentinel.exists())
        self.assertEqual(extract("invalid foo bar"),[0.]*SIZE)

    def test_source_only_features_never_use_true_STL_measurements(self):
        train=corpus(300,"train")
        valid=corpus(80,"validation")
        for doc in (train,valid):
            doc["profile_feature_schema"]=SCHEMA
            for i,row in enumerate(doc["records"]):
                row["profile_geometry_features"]=extract(
                    f"result=cq.Workplane('XY').rect({3+i%13},{1+i%7}).extrude({1+i%5})")
        a,b=verify(train,valid)
        model=fit(a[:240],"relative_profile",10.)
        guessed=predict(model,b)
        self.assertEqual(guessed.shape,(80,5))
        self.assertTrue(np.isfinite(guessed).all())
        first=source_x(b[0],"relative_profile")
        tampered=dict(b[0])
        tampered["surface_target"]=[.999,.999,3.,.999,.999]
        tampered["stl_sha256"]="f"*64
        self.assertTrue(np.array_equal(first,source_x(tampered,"relative_profile")))

    def test_legacy_features_have_no_extra_source_geometry(self):
        sample=corpus(300,"train")["records"][0]
        sample["profile_geometry_features"]=extract(
            "result=cq.Workplane().rect(8,1).extrude(6)")
        self.assertGreater(len(source_x(sample,"relative_profile")),
                           len(source_x(sample,"aggregate_literals")))
        self.assertGreater(len(source_x(sample,"aggregate_literals")),
                           len(source_x(sample,"operations_only")))

if __name__=="__main__":unittest.main()
