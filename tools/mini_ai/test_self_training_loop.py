"""Offline tests for recurring research-only model selection and rollback."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from self_training_loop import evaluate_cycle, run


def examples(n=160):
    pairs = []
    for index in range(n):
        sha = hashlib.sha256(("reviewed-cc0-object-" + str(index)).encode()).hexdigest()
        # Controlled original fixtures simulate two text/geometry families.
        is_vehicle = index % 2 == 0
        pairs.append({
            "source_object_id": "cc0_model_" + str(index),
            "source": "Poly Haven",
            "license": "CC0-1.0",
            "caption": ("An elongated metallic aerodynamic race vehicle with a wide body"
                        if is_vehicle else
                        "A compact round industrial machine and sturdy mechanical housing"),
            "source_mesh_sha256": sha,
            "geometry_features": (
                [.16, .40, .04, .01, .5, .70, .12, .02] if is_vehicle else
                [.70, .82, .05, .01, .6, .80, .17, .02]
            )
        })
    return {"schema": "assetwright-grounded-text-mesh-pairs-v1", "pairs": pairs}


class SelfTrainingLoopTests(unittest.TestCase):
    def test_first_verified_model_only_promoted_to_research_champion(self):
        report, candidate, champion = evaluate_cycle(examples())
        self.assertEqual(report["status"], "research_champion_promoted")
        self.assertEqual(report["self_generated_examples_accepted"], 0)
        self.assertEqual(report["weak_component_labels_accepted"], 0)
        self.assertFalse(report["android_model_updated"])
        self.assertIsNotNone(champion)
        self.assertEqual(champion["model"], candidate)
        self.assertFalse(champion["android_deployable"])
        self.assertEqual(champion["schema"], "assetwright-research-champion-v1")

    def test_identical_data_does_not_retrain_over_existing_champion(self):
        first, candidate, incumbent = evaluate_cycle(examples())
        second, _, kept = evaluate_cycle(examples(), incumbent)
        self.assertEqual(second["decision"], "keep_incumbent")
        self.assertEqual(second["new_independent_training_sources"], 0)
        self.assertEqual(kept, incumbent)
        self.assertEqual(first["candidate_test_mse"], second["candidate_test_mse"])

    def test_modified_private_self_generated_or_restricted_sources_not_trusted(self):
        doc = examples()
        bad = dict(doc["pairs"][0])
        bad.update(source="Private generative AI", source_mesh_sha256="f"*64,
                   source_object_id="generated1")
        doc["pairs"].append(bad)
        bad2 = dict(doc["pairs"][1])
        bad2.update(license="CC-BY-NC", source_mesh_sha256="e"*64,
                    source_object_id="restricted1")
        doc["pairs"].append(bad2)
        report, _, _ = evaluate_cycle(doc)
        self.assertEqual(report["grounded_unique_source_pairs"], 160)
        self.assertEqual(report["self_generated_examples_accepted"], 0)

    def test_tampered_incumbent_or_heldout_data_is_rejected(self):
        _, _, champion = evaluate_cycle(examples())
        tampered = copy.deepcopy(champion)
        tampered["model"]["bias"][0] = 3.
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            evaluate_cycle(examples(), tampered)
        tampered = copy.deepcopy(champion)
        tampered["model"]["source_model_hashes"].append("0"*64)
        with self.assertRaises(ValueError):
            evaluate_cycle(examples(), tampered)

    def test_new_samples_are_counted_and_old_champion_retained_if_no_gain(self):
        _, _, champion = evaluate_cycle(examples(120))
        result, candidate, new_champion = evaluate_cycle(examples(160), champion)
        self.assertIsNotNone(candidate)
        self.assertGreater(result["new_independent_training_sources"], 0)
        self.assertIn(result["decision"], {"keep_incumbent", "promote_research_only"})
        self.assertFalse(new_champion["android_deployable"])

    def test_data_shortage_never_promotes(self):
        doc = examples(8)
        report, candidate, champion = evaluate_cycle(doc)
        self.assertEqual(report["status"], "insufficient_verified_data")
        self.assertIsNone(candidate)
        self.assertIsNone(champion)

    def test_filesystem_outputs_do_not_write_private_weights_to_git(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            path = root / "verified_pairs.json"
            path.write_text(json.dumps(examples()), encoding="utf-8")
            report = run(path, root / "out")
            self.assertEqual(report["decision"], "promote_research_only")
            self.assertTrue((root / "out" / "champion.json").is_file())
            self.assertTrue((root / "out" / "evaluation.json").is_file())
            self.assertFalse(json.loads((root / "out" / "champion.json").read_text())
                             ["android_deployable"])


if __name__ == "__main__":
    unittest.main()
