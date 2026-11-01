"""Tests for safe prompt-triggered CC0 model study. No network access required."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from forge_asset_cycle import (
    read_request, selected_assets, normalized_dimensions,
    candidate_glb, run_cycle, catalog_asset,
)


class ForgeAssetCycleTests(unittest.TestCase):
    def test_request_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "request.json"
            base = {
                "schema": "assetwright-forge-training-request-v1",
                "cycle": 1,
                "max_assets": 4,
                "focus": "mechanical vehicle shape references",
            }
            path.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(read_request(path)["cycle"], 1)
            for bad in (-1, 0, 25, 100):
                base["max_assets"] = bad
                path.write_text(json.dumps(base), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_request(path)
            base["max_assets"] = 4
            base["focus"] = "../passwd & sudo rm"
            path.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_request(path)

    def test_vehicle_assets_win_selection(self):
        data = {
            "chair": {"type": 2, "name": "Chair", "category": "Furniture",
                      "tags": ["wood"], "dimensions": [1, 2, 3]},
            "engine": {"type": 2, "name": "Industrial engine", "category": "Industrial",
                       "tags": ["mechanical", "metal"], "dimensions": [1, 2, 2]},
            "truck": {"type": 2, "name": "Truck", "category": "Vehicles",
                      "tags": ["truck", "wheel"], "dimensions": [2, 3, 6]},
            "texture": {"type": 1, "name": "Car paint", "tags": ["vehicle"]},
        }
        chosen = selected_assets(data, "vehicle mechanical", 2)
        self.assertEqual({key for key, _ in chosen}, {"engine", "truck"})

    def test_exclude_previous_sources_to_enable_continuous_new_studies(self):
        catalog = {
            "covered_car": {"type": 2, "name": "Covered Car", "category": "Vehicles",
                            "tags": ["car"]},
            "old_tyre": {"type": 2, "name": "Old Tyre", "category": "Vehicles",
                          "tags": ["tyre"]},
            "new_generator": {"type": 2, "name": "Mechanical Generator",
                              "category": "Industrial", "tags": ["machine"]}
        }
        candidates = selected_assets(catalog, "vehicle mechanical", 2,
                                     exclude_ids={"covered_car", "old_tyre"})
        self.assertEqual([key for key, _ in candidates], ["new_generator"])

    def test_dont_invent_mesh_feature_ratios(self):
        self.assertEqual(normalized_dimensions([2, 4, 8]), [0.25, 0.5, 1.0])
        self.assertIsNone(normalized_dimensions([1, 0, 3]))
        self.assertIsNone(normalized_dimensions(["1", 2, 3]))

    def test_file_variant_allowlisting_and_size_cap(self):
        files = {
            "1k": {"glb": {
                "url": "https://dl.polyhaven.org/asset/test.glb",
                "size": 1024, "md5": "a" * 32}},
            "8k": {"glb": {
                "url": "https://dl.polyhaven.org/asset/test-huge.glb",
                "size": 200 * 1024 * 1024}},
            "evil": {"url": "https://example.com/unknown.glb", "size": 13},
            "fbx": {"url": "https://dl.polyhaven.org/asset/test.fbx", "size": 5},
        }
        candidate = candidate_glb(files)
        self.assertEqual(candidate[1], 1024)
        self.assertTrue(candidate[0].endswith("test.glb"))

    def test_report_is_metadata_only_without_explicit_glb(self):
        catalog = {
            "engine": {"type": 2, "name": "Mechanical engine",
                       "category": "Industrial", "tags": ["engine", "metal"],
                       "polycount": 1000, "dimensions": [1, 2, 3]}
        }
        with patch("forge_asset_cycle.api_json", return_value=catalog):
            result = run_cycle({
                "cycle": 10, "max_assets": 1, "focus": "engine",
            }, fetch_geometry=False)
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["geometry_inspected_count"], 0)
        self.assertFalse(result["model_training_performed"])
        self.assertFalse(result["android_model_updated"])
        self.assertEqual(result["assets"][0]["license"], "CC0-1.0")
        self.assertEqual(result["assets"][0]["normalized_dimensions"],
                         [0.33333, 0.66667, 1.0])


if __name__ == "__main__":
    unittest.main()
