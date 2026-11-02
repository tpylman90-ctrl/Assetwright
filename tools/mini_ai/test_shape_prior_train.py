"""Deterministic regression tests for real-geometry shape prior fitting."""
import json
import math
from pathlib import Path
import tempfile
import unittest

from shape_prior_train import fit, validate_rows, train_centroids, evaluate, run


def source_asset(index, vec, *, valid=True):
    return {
        "id": f"cc0_{index}",
        "license": "CC0-1.0" if valid else "unknown",
        "mesh_analysis": "blender_geometry_inspected",
        "geometry": {
            "schema": "assetwright-geometry-descriptor-v1",
            "features": vec,
            "source_sha256": f"{index:064x}",
        }
    }


def report(count=8):
    assets = []
    for i in range(count):
        # Two separated families; descriptors fit a two-cluster shape prior.
        t = i % 2
        scale = (i // 2) * .006
        vec = [(0.12 if t else 0.83) + scale, .5 + scale] + [.25] * 6
        assets.append(source_asset(i+1, vec))
    return {"schema": "assetwright-cc0-shape-study-v1", "cycle": 2,
            "assets": assets}


class ShapePriorTests(unittest.TestCase):
    def test_validation_rejects_bad_or_duplicate_source(self):
        doc = report(5)
        self.assertEqual(len(validate_rows(doc)), 5)
        bad = source_asset(99, [-2] + [.1] * 7)
        doc["assets"].append(bad)
        doc["assets"].append(source_asset(1, [.5] * 8))
        doc["assets"].append(source_asset(400, [.5] * 8, valid=False))
        self.assertEqual(len(validate_rows(doc)), 5)

    def test_training_produces_evaluated_numeric_model(self):
        evaluation, model = fit(report())
        self.assertEqual(evaluation["licensed_geometry_examples"], 8)
        self.assertEqual(evaluation["train_examples"], 6)
        self.assertEqual(evaluation["holdout_examples"], 2)
        self.assertIsNotNone(model)
        self.assertEqual(len(model["centroids"]), 2)
        self.assertEqual(len(model["centroids"][0]), 8)
        self.assertFalse(model["android_deployable"])
        self.assertGreaterEqual(evaluation["baseline_mean_squared_distance"], 0)
        self.assertGreaterEqual(evaluation["trained_mean_squared_distance"], 0)

    def test_cumulative_studies_above_fifty_fit_without_old_capacity_error(self):
        study = {"schema":"assetwright-cc0-shape-study-v1", "cycle":18,
                 "assets":[source_asset(i+1,
                     [.20 + (i % 4)*.08, .48] + [.25]*6)
                     for i in range(75)]}
        evaluation, model = fit(study)
        self.assertEqual(evaluation["licensed_geometry_examples"],75)
        self.assertIsNotNone(model)
        self.assertEqual(len(model["centroids"]),2)

    def test_not_enough_actual_meshes_never_claims_training(self):
        evaluation, model = fit(report(3))
        self.assertEqual(evaluation["status"], "insufficient_data")
        self.assertIsNone(model)

    def test_real_output_contains_only_derived_descriptor_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = folder / "report.json"
            data.write_text(json.dumps(report()))
            result = run(data, folder / "out")
            self.assertTrue((folder / "out" / "evaluation.json").is_file())
            self.assertTrue((folder / "out" / "candidate_prior.json").is_file())
            self.assertEqual(
                (folder / "out" / "validated_prior.json").exists(),
                result["status"] == "trained_passed_validation"
            )
            contents = (folder / "out" / "candidate_prior.json").read_text()
            self.assertNotIn(".glb", contents)
            self.assertNotIn("model.blend", contents)


if __name__ == "__main__":
    unittest.main()
