"""Bounded arithmetic fixtures; never replace actual GLB structural evidence."""
import unittest
try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("Optional native branch research NumPy not installed")
from native_branch_student import expected_stems, source_recipe, fit, predict, gates

class NativeBranchStudentTests(unittest.TestCase):
    def numeric_rows(self):
        rows=[]
        for family in range(1,7):
            for site in range(20):
                direction=site%4
                axial=site//4
                for variant in range(3):
                    y=source_recipe("train",family,site,variant)
                    angle=direction*np.pi/2
                    location=[np.cos(angle),np.sin(angle),(.2+.15*axial)]
                    observed=[.28+.65*y[0],.17+.37*y[1],
                              (.86-.13*y[2])/(.98-.07*y[2])]
                    rows.append({
                        "phase":"train","site":site,"target":y,
                        "features":np.asarray(location+observed),
                        "sha256":f"fake-{family}-{site}-{variant}"})
        return rows
    def test_source_batch_and_learner_response(self):
        self.assertEqual(520,len(expected_stems()))
        rows=self.numeric_rows()
        student=fit(rows)
        sites,controls=predict(student,np.stack([r["features"] for r in rows]))
        self.assertGreaterEqual(np.mean(sites==np.asarray([r["site"] for r in rows])),.99)
        self.assertLess(np.abs(controls-np.stack([r["target"] for r in rows])).mean(),.01)
        self.assertFalse(student["android_deployable"])
    def test_rejects_incorrect_source_split(self):
        rows=self.numeric_rows()
        with self.assertRaises(ValueError):fit(rows[:-1])
        rows[0]["phase"]="validation"
        with self.assertRaises(ValueError):fit(rows)
    def test_refuses_weak_candidate(self):
        m={"exact_site_accuracy":.35,
           "mean_control_mae":.2,"max_control_error":.31,
           "constant_strength_baseline_mae":.21,
           "per_strength_mae":{x:.2 for x in ("rise","socket_depth","blend")},
           "per_site_correct":{str(i):1 for i in range(20)}}
        self.assertFalse(all(gates(m,m).values()))

if __name__=="__main__":
    unittest.main()
