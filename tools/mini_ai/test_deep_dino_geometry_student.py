"""No downloaded-code execution, numeric-shape source and view provenance tests."""
import tempfile
from pathlib import Path
import unittest

from deep_dino_curriculum import NUMERIC_DIM, NUMERIC_SCHEMA, numeric_cad_features
from deep_dino_geometry_student import geometry_rows
from test_deep_dino_curriculum import fixtures


def geometry_fixture(n, split):
    doc, teacher = fixtures(n, split)
    doc["numeric_feature_schema"] = NUMERIC_SCHEMA
    for i, row in enumerate(doc["records"]):
        snippet = (f"result=cq.Workplane('XY').rect({2+i%8},3)"
                   f".extrude({2+i%5}).fillet(0.2).translate(({i%4},0,0))")
        row["numeric_cad_features"] = numeric_cad_features(snippet)
    return doc, teacher


class DeepDinoNativeGeometryTests(unittest.TestCase):
    def test_safe_numeric_ast_contains_real_size_information(self):
        x = numeric_cad_features("result=cq.Workplane('XY').rect(2,4).extrude(8).fillet(.5)")
        y = numeric_cad_features("result=cq.Workplane('XY').rect(8,10).extrude(12).fillet(2)")
        self.assertEqual(len(x), NUMERIC_DIM)
        self.assertEqual(len(y), NUMERIC_DIM)
        self.assertNotEqual(x, y)
        self.assertTrue(all(-1<=v<=1 for v in x+y))

    def test_dangerous_python_is_never_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "must-not-exist"
            script = ("__import__('os').system('touch " + str(target) + "')\n"
                      "result = cq.Workplane().rect(2,3).extrude(-5)")
            result = numeric_cad_features(script)
            self.assertFalse(target.exists())
            self.assertTrue(any(abs(v)>0 for v in result))
            self.assertEqual(numeric_cad_features("bad (]"), [0.] * NUMERIC_DIM)

    def test_owned_student_accepts_only_audited_geometry(self):
        doc, teacher = geometry_fixture(30, "train")
        rows = geometry_rows(doc, teacher, "train")
        self.assertEqual(len(rows), 30)
        self.assertTrue(all(row["literal_geometry_evidence"] for row in rows))
        doc["records"][0]["numeric_cad_features"] = [99.] * NUMERIC_DIM
        with self.assertRaisesRegex(ValueError, "bounded source"):
            geometry_rows(doc, teacher, "train")
        doc, teacher = geometry_fixture(30, "train")
        doc["numeric_feature_schema"] = "not-audited"
        with self.assertRaisesRegex(ValueError, "audited"):
            geometry_rows(doc, teacher, "train")

    def test_no_lost_or_short_feature_vectors(self):
        doc, teacher = geometry_fixture(30, "train")
        doc["records"][2]["numeric_cad_features"] = [0.] * 3
        with self.assertRaisesRegex(ValueError, "bounded source"):
            geometry_rows(doc, teacher, "train")


if __name__ == "__main__":
    unittest.main()
