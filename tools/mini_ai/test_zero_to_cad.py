"""Offline safety checks for the licensed CAD -> own Mini AI curriculum."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zero_to_cad_ingest import parse_row,structured_ops,source_ops,SCHEMA,DATASET,LICENSE
from zero_to_cad_operation_student import fit,probability
from zero_to_cad_dinov2_teacher import image_candidates

def row(i,split="train"):
    code=(f"import cadquery as cq\n"
          f"result=cq.Workplane('XY').rect({i+1},{3 if split=='validation' else 2})"
          ".extrude(2).faces('>Z').workplane().circle(1).cutBlind(-1)")
    return {"uuid":f"original_{split}_{i:05d}","cadquery_file":code,
            "cadquery_ops_json":json.dumps(["rect","extrude","faces","workplane","circle","cutBlind"]),
            "num_faces":12}

def manifest(count,split):
    records=[]
    for i in range(count):
        record,_=parse_row(row(i,split),split)
        if i%3==1:record["operations"]=["circle","extrude","faces","fillet"]
        if i%3==2:record["operations"]=["rect","extrude","faces","chamfer"]
        records.append(record)
    return {"schema":SCHEMA,"dataset":DATASET,"license":LICENSE,
            "split":split,"records":records}

class ZeroToCadTests(unittest.TestCase):
    def test_never_runs_downloaded_code(self):
        code=("__import__('os').system('touch /tmp/assetwright-z2cad-not-created')\n"
              "result=cq.Workplane().rect(1,2).extrude(3).fillet(.1)")
        ops,fingerprint=source_ops(code)
        self.assertIn("rect",ops)
        self.assertIn("extrude",ops)
        self.assertEqual(len(fingerprint),64)
        self.assertFalse(Path("/tmp/assetwright-z2cad-not-created").exists())
    def test_structured_ops_and_safe_ast_fallback(self):
        self.assertEqual(structured_ops('[{"op":"cq.Workplane.rect"},"extrude","unknown"]'),
                         ["rect","extrude"])
        x=row(1);x["cadquery_ops_json"]="invalid json"
        result,reason=parse_row(x,"train")
        self.assertEqual(reason,"accepted")
        self.assertEqual(result["operations_source"],"safe_ast_method_calls")
        self.assertEqual(result["operations"][-1],"cutBlind")
    def test_bad_source_is_rejected(self):
        x=row(1);x["uuid"]="bad"
        self.assertEqual(parse_row(x,"train")[1],"invalid_uuid")
        x=row(1);x["cadquery_file"]="a=1";x["cadquery_ops_json"]="[]"
        self.assertEqual(parse_row(x,"train")[1],"insufficient_supported_operations")
    def test_no_training_holdout_leakage(self):
        train=manifest(30,"train");valid=manifest(10,"validation")
        valid["records"][0]["code_sha256"]=train["records"][0]["code_sha256"]
        with self.assertRaisesRegex(ValueError,"overlap"): fit(train,valid)
    def test_owned_research_only_student(self):
        report,model=fit(manifest(55,"train"),manifest(18,"validation"))
        self.assertIsNotNone(model)
        self.assertFalse(model["android_deployable"])
        self.assertFalse(model["third_party_geometry_imported"])
        self.assertFalse(report["external_ai_produces_final_models"])
        for history in ([],["rect"],["rect","extrude"]):
            total=sum(probability(model,history,word,"trigram") for word in model["vocab"])
            self.assertAlmostEqual(total,1.,places=6)
        self.assertIn(report["status"],("validated_research_grammar","grammar_failed_holdout_gate"))
    def test_small_corpus_rejected(self):
        report,model=fit(manifest(12,"train"),manifest(4,"validation"))
        self.assertIsNone(model)
        self.assertEqual(report["status"],"insufficient_official_split_examples")
    def test_frozen_teacher_requires_hashed_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);image=root/"test.png";image.write_bytes(b"image-test")
            data=manifest(1,"train");r=data["records"][0]
            r["view_files"]={"image_0":image.name}
            r["view_sha256"]={"image_0":hashlib.sha256(image.read_bytes()).hexdigest()}
            self.assertEqual(len(list(image_candidates(data,root))),1)
            image.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError,"changed"):
                list(image_candidates(data,root))

if __name__=="__main__": unittest.main()
