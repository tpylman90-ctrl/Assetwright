"""Disconnected mesh topology does not require external geometry files."""
import unittest
from mesh_islands import connected_bounds


def tetra(offset):
    x=offset
    vertices=[(x,0,0),(x+1,0,0),(x,1,0),(x,0,1)]
    edges=[(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
    triangles=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
    return vertices,edges,triangles


class MeshIslandTests(unittest.TestCase):
    def test_two_islands_stored_as_two_bounding_components(self):
        v1,e1,t1=tetra(0)
        v2,e2,t2=tetra(5)
        points=v1+v2
        edges=e1+[(a+4,b+4) for a,b in e2]
        tris=(t1+[(a+4,b+4,c+4) for a,b,c in t2])*3
        islands=connected_bounds(points,edges,tris,minimum_triangles=8)
        self.assertEqual(len(islands),2)
        self.assertEqual(sum(x["triangles"] for x in islands),24)
        self.assertEqual(sorted([x["min"][0] for x in islands]),[0.0,5.0])

    def test_connected_mesh_remains_one_component(self):
        vertices,edges,triangles=tetra(0)
        out=connected_bounds(vertices,edges,triangles,minimum_triangles=1)
        self.assertEqual(len(out),1)

    def test_tiny_loose_islands_are_ignored(self):
        v1,e1,t1=tetra(0)
        v2,e2,t2=tetra(5)
        islands=connected_bounds(v1+v2,e1+[(a+4,b+4) for a,b in e2],
                                 t1*4+[(a+4,b+4,c+4) for a,b,c in t2],
                                 minimum_triangles=10)
        self.assertEqual(len(islands),1)
        self.assertEqual(islands[0]["triangles"],16)

    def test_invalid_edges_cannot_create_bogus_parts(self):
        v,e,t=tetra(0)
        with self.assertRaises(ValueError):
            connected_bounds(v,e+[(1,100)],t,minimum_triangles=1)


if __name__=="__main__":
    unittest.main()
