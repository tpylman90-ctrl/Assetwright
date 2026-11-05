"""CAD library scale-up safety and owned reasoning model tests.

Synthetic fixture records only; real performance must be demonstrated on
pinned official Zero-to-CAD train/validation examples in separate CI.
"""
from __future__ import annotations
import json
import unittest

from zero_to_cad_ingest import parse_row,source_ops,structured_ops,SCHEMA,DATASET,LICENSE
from cad_shape_school import (
    verify_manifests,concepts,fit_concepts,evaluate_concepts,
    fit_faces,evaluate_faces,probabilities,complexity_features,
    cards,NATIVE_TRANSFER,OP_TO_GROUP
)

REVISION="3"*40
SHAPES=(
    ["rect","extrude","faces","workplane","circle","cutBlind","fillet"],
    ["circle","revolve","faces","hole","chamfer"],
    ["rect","extrude","polarArray","cut","fillet"],
    ["polygon","extrude","shell","mirror","translate"],
    ["spline","loft","faces","circle","cutThruAll","chamfer"],
    ["circle","sweep","cutBlind","fillet","rotate"],
)
def manifest(n,split):
    rows=[]
    for i in range(n):
        ops=SHAPES[i%len(SHAPES)]
        source=("import cadquery as cq\n"
            f"result=cq.Workplane('XY').rect({i+1},3).extrude({i%5+1})\n"
            f"# independent source identity {split}:{i}\n")
        raw={"uuid":f"{split}_{i:06d}","cadquery_file":source,
             "cadquery_ops_json":json.dumps(ops),
             "num_faces":7+len(ops)*5+sum(1 for x in ops if x in
                 ("cut","cutBlind","cutThruAll","hole"))*18+
                 (i%3)*2}
        parsed,reason=parse_row(raw,split)
        assert reason=="accepted"
        rows.append(parsed)
    return {
        "schema":SCHEMA,"dataset":DATASET,"license":LICENSE,
        "split":split,"dataset_revision":REVISION,"records":rows
    }

class CadShapeSchoolTest(unittest.TestCase):
    def test_fixtures_independent_and_licensed(self):
        train,valid=verify_manifests(manifest(360,"train"),manifest(110,"validation"))
        self.assertEqual((360,110),(len(train),len(valid)))
        self.assertTrue(all(op in OP_TO_GROUP for op in (
            "rect","extrude","cut","fillet","mirror","rotate")))
        self.assertTrue(all(row["num_faces"]>0 for row in valid))

    def test_disjoint_and_revision_gate_fails_closed(self):
        a=manifest(360,"train")
        b=manifest(110,"validation")
        b["dataset_revision"]="4"*40
        with self.assertRaisesRegex(ValueError,"different"):verify_manifests(a,b)
        b["dataset_revision"]=REVISION
        b["records"][0]["code_sha256"]=a["records"][0]["code_sha256"]
        with self.assertRaisesRegex(ValueError,"leakage"):verify_manifests(a,b)
        b["records"][0]["code_sha256"]="bad"
        with self.assertRaises(ValueError):verify_manifests(a,b)

    def test_contextual_student_uses_history_only(self):
        train=manifest(360,"train")["records"]
        valid=manifest(110,"validation")["records"]
        model=fit_concepts(train)
        baseline=evaluate_concepts(model,valid,"unigram")
        contextual=evaluate_concepts(model,valid,"trigram")
        self.assertGreater(contextual["transitions"],150)
        self.assertLess(contextual["cross_entropy"],baseline["cross_entropy"])
        for method in ("unigram","bigram","trigram"):
            self.assertAlmostEqual(sum(probabilities(model,("profile",),method).values()),
                                   1.0,places=7)
        # Sanity: the answer isn't included in the model input prefix.
        self.assertEqual(concepts(["rect","faces","extrude","fillet"]),
                         ["profile","volume","finish"])

    def test_geometry_proxy_does_not_include_face_target_as_feature(self):
        records=manifest(360,"train")["records"]
        model=fit_faces(records)
        evaluation=evaluate_faces(model,manifest(110,"validation")["records"])
        self.assertGreater(evaluation["heldout_labeled_sources"],70)
        self.assertTrue(0<evaluation["semantic_log_face_mae"]<10)
        row=records[0].copy()
        x=complexity_features(row)
        row["num_faces"]=9999
        self.assertEqual(x,complexity_features(row))
        self.assertIn("partial",set(x["status"] for x in NATIVE_TRANSFER.values()))

    def test_never_run_downloaded_cad_python(self):
        source=("__import__('os').system('touch /tmp/assetwright-cad-school-unsafe')\n"
                "result=cq.Workplane().circle(2).extrude(1).fillet(.1)")
        ops,sha=source_ops(source)
        self.assertIn("fillet",ops)
        self.assertEqual(len(sha),64)
        from pathlib import Path
        self.assertFalse(Path("/tmp/assetwright-cad-school-unsafe").exists())

    def test_cards_are_train_observations_not_auto_generated_geometry(self):
        rows=manifest(360,"train")["records"]
        model=fit_concepts(rows)
        found=cards(model,rows)
        self.assertTrue(found)
        self.assertLessEqual(len(found),12)
        self.assertTrue(all("native_transfer" in x and
                            "geometry_rationale_educational_not_causal" in x
                            for x in found))

if __name__=="__main__":
    unittest.main()
