"""Source integrity checks for v12 new eight-form physical geometry school."""
import os
import unittest

from dino_delta_school import STUDY,FAMILIES,LEVELS,EXPECTED,BASELINES,expected_changes


@unittest.skipUnless(os.getenv("ASSETWRIGHT_DINO_STUDY")=="resolution_aware_v12",
                     "Requires explicitly activated source-disjoint v12 study")
class GeometryMasterySourceSchool(unittest.TestCase):
    def test_fresh_original_splits_and_distinct_strengths(self):
        self.assertEqual(STUDY,"resolution_aware_v12")
        self.assertEqual(EXPECTED,1728)
        self.assertEqual(BASELINES,80)
        self.assertEqual({k:len(v) for k,v in FAMILIES.items()},
                         {"train":48,"development":16,"validation":16})
        self.assertEqual({name:sum(x[0]==name for x in expected_changes().values())
                          for name in FAMILIES},
                         {"train":1152,"development":288,"validation":288})
        for a,b in (("train","development"),("train","validation"),
                    ("development","validation")):
            self.assertFalse(set(FAMILIES[a])&set(FAMILIES[b]))
            self.assertFalse(set(LEVELS[a])&set(LEVELS[b]))
        self.assertTrue(all(x.startswith("ra_blind")
                            for x in FAMILIES["validation"]))
        self.assertEqual(len(set(expected_changes())),1728)


if __name__=="__main__":
    unittest.main()
