"""Research policy and native socket geometry audit safety checks."""
import unittest
from zero_to_cad_native_bridge import propose,SCHEMA
from zero_to_cad_operation_student import train_markov
from zero_to_cad_visual_student import MODEL as V_MODEL,DIM,OUTPUTS
from test_zero_to_cad import manifest
from native_socket_audit import compare,near_well

def validated():
    grammar=train_markov(manifest(30,"train")["records"])
    grammar["validated_on_official_split"]=True
    grammar["selected_method"]="trigram"
    visual={"schema":V_MODEL,"validated_on_official_split":True,
            "approved_for_geometry_generation":False,"inference_needs_teacher":False,
            "weights":[[0.0]*DIM for _ in range(OUTPUTS)],"bias":[0.0]*OUTPUTS}
    return grammar,visual

class NativeResearchBridgeTests(unittest.TestCase):
    def test_only_one_whitelisted_owned_native_operation_is_proposed(self):
        g,v=validated()
        r=propose(g,v)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["native_operation"],"recess_rear_socket")
        self.assertEqual(r["native_parameters"]["drive_count"],1)
        self.assertFalse(r["external_mesh_used"])
        self.assertFalse(r["automatically_deployable"])
        self.assertEqual(len(r["distilled_visual_signature"]),24)
        self.assertGreater(r["learnt_conditional_cutblind_probability"],0)
    def test_requires_both_independent_research_gates(self):
        g,v=validated()
        g["validated_on_official_split"]=False
        with self.assertRaisesRegex(ValueError,"not independently validated"):propose(g,v)
        g,v=validated()
        v["approved_for_geometry_generation"]=True
        with self.assertRaisesRegex(ValueError,"not independently validated"):propose(g,v)
    def test_native_hull_well_is_measured_from_real_vertices_not_bounding_box(self):
        before=[(1.,.80,-1.0),(-1.,.80,-1.0),(0.,1.05,-1.0)]
        after=before+[(.08,.8,-.8),(-.08,.8,-.8)]+[(.08,.8,-1.)]
        self.assertEqual(near_well(before,-1.,.8),0)
        self.assertEqual(near_well(after,-1.,.8),2)
    def test_rejects_structurally_defective_or_fake_mesh(self):
        base={"parts":[{"name":"Sculpted continuous body","triangles":40,
                        "boundary_edges":0,"nonmanifold_edges":0,
                        "invalid_triangles":0,"signed_volume":1.}],
              "mesh_parts":2,"nonmanifold_edges":0,"triangles":50}
        newer={"parts":[{"name":"Sculpted continuous body","triangles":70,
                         "boundary_edges":3,"nonmanifold_edges":0,
                         "invalid_triangles":0,"signed_volume":1.}],
               "mesh_parts":2,"nonmanifold_edges":0,"triangles":90}
        before=[(1.,.8,-1.),(-1.,.8,-1.)]
        after=before+[(.03,.8,-.8)]*20
        report=compare(base,newer,before,after)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["hull_single_connected_surface"])

if __name__=="__main__":unittest.main()
