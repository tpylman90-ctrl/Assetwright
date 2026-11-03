import unittest
from native_operation_intent_student import examples,train,evaluate,OPERATIONS
from native_operator_proposal_batch import batch,REQUEST

class NativeOperatorProposalBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owned=train(examples("train"),epochs=125)
        cls.heldout=evaluate(cls.owned,examples("holdout"))
    def test_owned_student_selects_three_distinct_native_operations(self):
        proof=batch(self.owned,self.heldout,"a"*64)
        self.assertEqual(proof["schema"],REQUEST)
        self.assertEqual([x["operation"] for x in proof["proposals"]],list(OPERATIONS))
        self.assertTrue(all(.45<=p["strength"]<=1. for p in proof["proposals"]))
        self.assertFalse(proof["teacher_model_used_to_generate_geometry"])
        self.assertFalse(proof["external_mesh_used"])
    def test_refuses_unapproved_student_or_disqualified_holdout(self):
        with self.assertRaisesRegex(ValueError,"Unverified"):
            batch({**self.owned,"external_mesh_used":True},self.heldout,"a"*64)
        with self.assertRaisesRegex(ValueError,"Unverified"):
            batch(self.owned,{**self.heldout,"heldout_accuracy":.40},"a"*64)
if __name__=="__main__":unittest.main()
