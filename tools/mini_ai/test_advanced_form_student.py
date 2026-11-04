"""Small synthetic arithmetic unit tests; never count as source GLB results."""
import unittest
from advanced_form_student import (
    OPERATIONS, TRAIN_LEVELS, TRAIN_LEVELS, expected_cases,
    train_response_curves, inverse_strength, train_classifier,
    predict_class, gates, EXPECTED,
)

class AdvancedFormStudentTest(unittest.TestCase):
    def rows(self):
        result=[]
        for op_index,op in enumerate(OPERATIONS):
            for family in range(12):
                for level in TRAIN_LEVELS:
                    vec=[0.]*6
                    vec[op_index]=level*(.25+.03*op_index)
                    result.append({"phase":"train","family":"advtrain%02d" % (family+1),
                        "class":op,"strength":level,"features":vec,
                        "sha256":"fixture-%s-%s-%s" % (op,family,level)})
        return result

    def test_full_batch_cardinality(self):
        self.assertEqual(EXPECTED, len(expected_cases()))
        self.assertEqual(720,len(self.rows()))

    def test_owned_model_learns_all_six_numeric_signatures(self):
        student=train_classifier(self.rows(),epochs=300)
        self.assertFalse(student["android_deployable"])
        for index,op in enumerate(OPERATIONS):
            vec=[0.]*6
            vec[index]=.20
            self.assertEqual(op,predict_class(student,vec)[0])

    def test_inverse_curves_fit_and_do_not_use_constant_strength(self):
        curve=train_response_curves(self.rows())
        for index,op in enumerate(OPERATIONS):
            vec=[0.]*6
            vec[index]=.47*(.25+.03*index)
            self.assertAlmostEqual(.47,inverse_strength(curve,op,vec),places=6)
        # Refuse a saturated control even if its rows carry multiple labels.
        bad=self.rows()
        for row in bad:
            if row["class"]=="SECTION_LOFT": row["features"][0]=.1
        with self.assertRaises(ValueError):
            train_response_curves(bad)

    def test_gates_do_not_accept_weak_accuracy(self):
        weak={"accuracy":.50,"per_class_correct":{op:8 for op in OPERATIONS},
            "oracle_strength_mae":.2,"end_to_end_strength_mae":.6,
            "constant_strength_baseline_mae":.23}
        self.assertFalse(all(gates(weak,weak).values()))

if __name__=="__main__":
    unittest.main()
