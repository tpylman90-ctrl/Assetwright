"""Synthetic geometry comparisons validate the *measurement*, not beauty."""
import math
import unittest
from vehicle_design_critic import _canopy_crown, _arm_stations


def greenhouse(exponent:float):
    # One annular ring at two longitudinal stations, with z-up mapped to
    # glTF Y-up and arbitrary longitudinal glTF Z positions.
    points=[]
    for longitude in (-.12,0,.12):
        for i in range(16):
            angle=i*2*math.pi/16
            x=.9*math.cos(angle)
            top=max(0,math.sin(angle))
            height=.86+.55*top**exponent if top else .86+.04*math.sin(angle)
            points.append((x,height,longitude))
    return points


def support(stations:int):
    points=[]
    for j in range(stations):
        x=.5+j*1.2/(stations-1)
        radius=.18-.10*j/(stations-1)
        for i in range(12):
            a=i*math.pi/6
            points.append((x,.41+radius*math.cos(a),.20+radius*math.sin(a)))
    return [points]


class DesignCriticTests(unittest.TestCase):
    def test_flattened_roof_is_measurably_broader_than_blob(self):
        dome=_canopy_crown(greenhouse(1.0))
        shaped=_canopy_crown(greenhouse(.32))
        self.assertLess(dome["roof_crown_width_ratio"],.35)
        self.assertGreater(shaped["roof_crown_width_ratio"],.35)
        self.assertGreater(shaped["roof_crown_width_ratio"],
                           dome["roof_crown_width_ratio"]+.20)

    def test_cross_section_count_distinguishes_rods_from_profiling(self):
        rod=_arm_stations(support(2))
        sculpt=_arm_stations(support(5))
        self.assertEqual(rod["mount_section_count_min"],2)
        self.assertEqual(sculpt["mount_section_count_min"],5)
        self.assertEqual(sculpt["mount_parts_analyzed"],1)

    def test_missing_geometry_cannot_get_positive_score(self):
        self.assertEqual(_canopy_crown([])["roof_crown_width_ratio"],0)
        self.assertEqual(_arm_stations([])["mount_section_count_min"],0)


if __name__=="__main__":
    unittest.main()
