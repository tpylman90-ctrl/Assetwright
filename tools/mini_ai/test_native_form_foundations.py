"""Guard source-only native-form training and fail-closed sampling."""
from __future__ import annotations
import unittest
from native_form_foundations import KINDS,fit_student,predict,score

class NativeFormFoundationsTest(unittest.TestCase):
    def synthetic_rows(self):
        # Arithmetic fixtures ONLY: never production/CI geometry evidence.
        rows=[]
        for kind in KINDS:
            for level in (.35,.60,.9):
                for dims in range(3):
                    vec=[0.,0.,0.,.5]
                    if kind=="ROUNDED_BOX": vec[3]=.57+.18*level
                    elif kind=="ELLIPSOID": vec[1]=.93
                    elif kind=="TAPERED_LOFT": vec[0]=level*.85
                    elif kind=="ARCH_SWEEP": vec[2]=level*.35
                    rows.append({"phase":"train","class":kind,"features":vec,
                                 "sha256":f"{kind}-{level}-{dims}"})
        return rows

    def test_real_optimizer_learns_form_discrimination(self):
        rows=self.synthetic_rows()
        model=fit_student(rows,epochs=1200)
        self.assertEqual(45,model["training_samples"])
        self.assertGreaterEqual(score(model,rows)["accuracy"],.9)
        self.assertFalse(model["android_deployable"])

    def test_invalid_source_partitions_reject(self):
        rows=self.synthetic_rows()
        with self.assertRaises(ValueError): fit_student(rows[:-1])
        with self.assertRaises(ValueError): fit_student([
            {**r,"phase":"validation"} for r in rows])

    def test_inference_not_hardcoded_class_by_filename(self):
        model=fit_student(self.synthetic_rows(),epochs=1100)
        self.assertEqual("ELLIPSOID",predict(model,[0,.93,0,.5])[0])
        self.assertEqual("TAPERED_LOFT",predict(model,[.6,0,0,.5])[0])

if __name__=="__main__":
    unittest.main()
