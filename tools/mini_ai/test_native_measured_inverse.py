"""Inverse response safety, family holdout, and independent geometry tests."""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest

from native_measured_inverse import (
    ORDER,METRIC,TRAIN_LEVELS,validate_response,inverse,case,digest,
)
from native_measured_program_audit import compare,SCHEMA as AUDIT

def fixture():
    rows=[]
    for family,width in (("coupe",1.0),("utility",1.2)):
        rows.append({"sha256":hashlib.sha256(("baseline"+family).encode()).hexdigest(),
                     "name":"measure__"+family+"__baseline",
                     "meta":{"family":family,"phase":"train","commands":[]},
                     "metrics":{"rear_socket_depth_m":0.,
                                "upper_hull_station_halfspan_m":width,
                                "engine_housing_flare_ratio":1.}})
        for operation in ORDER:
            for level in TRAIN_LEVELS:
                field=METRIC[operation]
                responses={"recess_rear_socket":.16,
                           "sculpt_cockpit_shoulder":.028,
                           "loft_rear_nacelle":.46}
                base=rows[-1] if False else {
                    "rear_socket_depth_m":0.,
                    "upper_hull_station_halfspan_m":width,
                    "engine_housing_flare_ratio":1.}
                values=dict(base)
                values[field]+=responses[operation]*level
                label=family+operation+str(level)
                rows.append({"sha256":hashlib.sha256(label.encode()).hexdigest(),
                             "name":label,
                             "meta":{"family":family,"phase":"train",
                                     "commands":[{"operation":operation,"strength":level}]},
                             "metrics":values})
    return rows

class MeasuredNativeGeometryTests(unittest.TestCase):
    def test_native_curves_are_identifiable_and_inverse_is_continuous(self):
        curves=validate_response(fixture())
        self.assertEqual(set(curves),set(ORDER))
        for op in ORDER:
            assert curves[op]["slope_direction"]=="increasing"
            points=curves[op]["curve"]
            x=.725
            # Known underlying analytic response only in this isolated test.
            y=points[1][1]*(x/points[1][0])
            self.assertAlmostEqual(inverse(points,y),x,places=4)
    def test_no_reference_leakage_into_native_response_fit(self):
        f=fixture()
        f[0]["meta"]["phase"]="reference"
        with self.assertRaisesRegex(ValueError,"heldout"):
            validate_response(f)
    def test_missing_levels_and_repeated_source_are_rejected(self):
        f=fixture()
        with self.assertRaisesRegex(ValueError,"Missing native control levels"):
            validate_response(f[:-1])
        f=fixture()
        f[1]["sha256"]=f[0]["sha256"]
        with self.assertRaisesRegex(ValueError,"Repeated"):
            validate_response(f)
    def test_forged_metadata_cannot_admit_outside_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            name="fake_reference"
            (folder/(name+".glb")).write_bytes(b"not a valid original GLB")
            (folder/(name+".json")).write_text(json.dumps({
                "schema":"assetwright-native-measured-program-v1",
                "case":name,"original_generator":"imported_tripo_mesh",
                "source_glb_sha256":digest(b"not a valid original GLB"),
                "phase":"train"}))
            with self.assertRaisesRegex(ValueError,"Untrusted original GLB"):
                case(folder,name)
    def test_forward_critic_never_accepts_wrong_partition(self):
        original={"meta":{"phase":"reference","model_sha256":"baseline"},
                  "metrics":{"rear_socket_depth_m":.22}}
        pred={"meta":{"phase":"predicted","model_sha256":"a"*64},
              "metrics":{"rear_socket_depth_m":.21},
              "structural":{"nonmanifold_edges":0,"invalid_triangles":0,
                            "triangles":1200}}
        self.assertTrue(compare(original,pred,ORDER[1])["passed"])
        original["meta"]["phase"]="train"
        with self.assertRaisesRegex(ValueError,"source reference"):
            compare(original,pred,ORDER[1])

if __name__=="__main__":unittest.main()
