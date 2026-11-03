"""Tests for freeze-first strength calibration and fresh blind governance."""
import copy
import json
from pathlib import Path
import unittest
from native_operation_intent_student import train,examples,OPERATIONS
from native_strength_calibration import (
    new_blind_rows, split_integrity, calibrate, frozen_classifier,
    measure, BLIND_SCHEMA, GATE,
)
from native_skill_clinic import validate_curriculum

ROOT=Path(__file__).resolve().parents[2]/"training/curricula"

class FrozenNativeCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed=train(examples("train"),epochs=125)
        cls.prior=examples("holdout")
        cls.clinic=validate_curriculum(json.loads(
            (ROOT/"native_skill_clinic_v1.json").read_text()))
        cls.blind_doc=json.loads((ROOT/"native_strength_blind_v2.json").read_text())
    def test_new_blind_has_distinct_authored_operation_strength_groups(self):
        fresh=new_blind_rows(self.blind_doc)
        self.assertEqual(len(fresh),36)
        self.assertEqual(len({x["source_group"] for x in fresh}),12)
        self.assertEqual({x["operation"] for x in fresh},set(OPERATIONS))
        self.assertEqual({x["strength"] for x in fresh},{.30,.60,.90})
        checked=split_integrity(examples("train")+self.clinic["correction"],
                                self.clinic["development"],fresh,self.prior,
                                self.clinic["blind"])
        self.assertTrue(checked["past_exposed_blind_excluded"])
        self.assertFalse(checked["new_blind_used_for_checkpoint_selection"])
    def test_blind_rejects_unknown_operations_and_duplicate_templates(self):
        bad=copy.deepcopy(self.blind_doc)
        bad["templates"][1]["template"]=bad["templates"][0]["template"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            new_blind_rows(bad)
        bad=copy.deepcopy(self.blind_doc)
        bad["templates"][0]["operation"]="import_teacher_mesh"
        with self.assertRaisesRegex(ValueError,"unsupported"):
            new_blind_rows(bad)
    def test_classifier_is_frozen_under_gradient_updates(self):
        before=measure(self.seed,self.prior)
        candidate,notes=calibrate(self.seed,self.clinic["correction"],
                                  self.clinic["development"],self.prior,epochs=8)
        after=measure(candidate,self.prior)
        self.assertTrue(frozen_classifier(self.seed,candidate))
        self.assertEqual(before["operator_accuracy"],after["operator_accuracy"])
        self.assertEqual(before["abstentions"],after["abstentions"])
        self.assertTrue(notes["frozen_classification_weights"])
        changed=copy.deepcopy(candidate)
        changed["class_bias"][0]+=.1
        self.assertFalse(frozen_classifier(self.seed,changed))
    def test_numeric_metrics_do_not_conflate_winning_operation_and_strength(self):
        metrics=measure(self.seed,new_blind_rows(self.blind_doc))
        self.assertEqual(metrics["samples"],36)
        self.assertEqual(metrics["monotonic_groups"],12)
        self.assertGreaterEqual(metrics["operator_accuracy"],0)
        self.assertGreaterEqual(metrics["conditional_strength_mae"],0)
        self.assertGreater(GATE["minimum_blind_strength_improvement"],0)

if __name__=="__main__":unittest.main()
