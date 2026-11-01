"""Regression tests for Forge -> Android lesson transfer semantics.

These are semantic parameter tests against unobserved prompt phrasings, not
claims about photorealism, mesh quality or neural 3D generation.
"""
import json
from pathlib import Path
import unittest

from home_train import SEED, predict
from check_forge_lessons import FEED, validate

PAIRS = {
    "width": ("wide", "narrow"),
    "length": ("long", "compact"),
    "roofHeight": ("tall", "low"),
    "canopyLength": ("elongated", "compact"),
    "noseTaper": ("blunt", "pointed"),
    "rearHaunch": ("bulky", "slim"),
}
PROBES = (
    ("wide hover racer with panoramic glass",
     "narrow hover racer with panoramic glass", "width", 0.20),
    ("long hover coupe with tapered nose",
     "compact hover coupe with tapered nose", "length", 0.20),
    ("tall hover suv with canopy",
     "low hover suv with canopy", "roofHeight", 0.15),
    ("elongated panoramic canopy hover speedster",
     "short compact canopy hover speedster", "canopyLength", 0.30),
    ("blunt nose hover racer",
     "pointed nose hover racer", "noseTaper", 0.08),
    ("bulky rear haunch hover suv",
     "slim rear haunch hover suv", "rearHaunch", 0.05),
)


class ForgeContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feed = json.loads(FEED.read_text(encoding="utf-8"))
        cls.examples = [
            {"prompt": x["prompt"], **x["parameters"]}
            for x in cls.feed["lessons"]
        ] + json.loads(SEED.read_text(encoding="utf-8"))

    def test_schema_and_pair_invariants(self):
        self.assertGreaterEqual(validate(self.feed), 20)
        self.assertGreaterEqual(self.feed["version"], 2)
        for axis in PAIRS:
            pairs = [
                item for item in self.feed["lessons"]
                if item.get("learning_objective") == axis
            ]
            self.assertEqual(len(pairs), 2, axis)
            a, b = pairs
            self.assertEqual(
                {a["contrast_pair"].rsplit("-", 1)[-1],
                 b["contrast_pair"].rsplit("-", 1)[-1]},
                {"higher", "lower"},
                axis
            )
            high = next(x["parameters"] for x in pairs
                        if x["contrast_pair"].endswith("-higher"))
            low = next(x["parameters"] for x in pairs
                       if x["contrast_pair"].endswith("-lower"))
            for other in high:
                if other != axis:
                    self.assertEqual(high[other], low[other],
                                     f"{axis}: unexpected {other} change")
            self.assertGreater(high[axis], low[axis], axis)
            self.assertTrue(all(
                x.get("review_status") == "parameter-verified-not-render-verified"
                and x.get("provenance") == "original-forge-authored-contrastive-shape-recipe"
                for x in pairs
            ))

    def test_unseen_semantic_prompts_move_expected_dimension(self):
        source_prompts = {x["prompt"].lower() for x in self.feed["lessons"]}
        for high, low, axis, threshold in PROBES:
            with self.subTest(axis=axis):
                self.assertNotIn(high.lower(), source_prompts)
                self.assertNotIn(low.lower(), source_prompts)
                output_high = predict(high, self.examples)[axis]
                output_low = predict(low, self.examples)[axis]
                self.assertGreater(
                    output_high - output_low, threshold,
                    f"{axis}: regression in prompt-to-geometry contrast"
                )


if __name__ == "__main__":
    unittest.main()
