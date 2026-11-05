"""Persisted source-hashed neural knowledge must not be reinitialized."""
import importlib.util
from pathlib import Path
import unittest

from native_studied_warm_start import DEFAULT, load_provenance


class OriginalNativeMemoryTests(unittest.TestCase):
    def test_retained_weights_have_real_source_and_heldout_lineage(self):
        lineage,normalization,weights=load_provenance(DEFAULT)
        self.assertTrue(weights.is_file())
        self.assertEqual(lineage["heldout_operation_accuracy"],.9375)
        self.assertLess(lineage["heldout_strength_mae"],.14)
        self.assertEqual(lineage["parameter_count"],160938)
        self.assertEqual(len(normalization["train_feature_mean"]),1536)
        self.assertFalse(lineage["approved_for_production"])
        self.assertFalse(lineage["android_installed"])

    def test_modified_checkpoint_fails_before_it_could_override_knowledge(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for file in ("model_lineage.json","normalization.json","owned_native_student.safetensors"):
                (root/file).write_bytes((DEFAULT/file).read_bytes())
            (root/"owned_native_student.safetensors").write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError,"modified"):
                load_provenance(root)

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None,
                         "Torch is optional in lean Android/Python checks")
    def test_pixel_rebase_mathematically_preserves_old_learned_activations(self):
        import torch
        from native_studied_warm_start import rebase_dense
        old_w=torch.tensor([[1.,-2.,.5],[-.5,.7,2.]])
        old_b=torch.tensor([.33,-.18])
        old_mean=torch.tensor([.3,.4,.25])
        old_std=torch.tensor([.8,.4,.7])
        new_mean=torch.tensor([.2,.5,.5])
        new_std=torch.tensor([.7,.7,.3])
        w,b=rebase_dense(old_w,old_b,old_mean,old_std,new_mean,new_std)
        for pixel in (torch.tensor([.1,.6,.4]),torch.tensor([.8,.4,.2])):
            a=old_w@((pixel-old_mean)/old_std)+old_b
            z=w@((pixel-new_mean)/new_std)+b
            self.assertTrue(torch.allclose(a,z,atol=1e-6))
        self.assertTrue(torch.equal(old_w,torch.tensor([[1.,-2.,.5],[-.5,.7,2.]])))


if __name__=="__main__":
    unittest.main()
