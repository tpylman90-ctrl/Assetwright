"""Synthetic geometry comparisons validate the *measurement*, not beauty."""
import math
import unittest
from vehicle_design_critic import _canopy_crown, _arm_stations, _cockpit_shoulder_span, _rear_nacelle_profile


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


def support(stations:int, tapered:bool=True):
    points=[]
    for j in range(stations):
        x=.5+j*1.2/(stations-1)
        radius=.18-.10*j/(stations-1) if tapered else .18
        for i in range(12):
            a=i*math.pi/6
            points.append((x,.41+radius*math.cos(a),.20+radius*math.sin(a)))
    return [points]


class DesignCriticTests(unittest.TestCase):
    def test_flattened_roof_is_measurably_broader_than_blob(self):
        dome=_canopy_crown(greenhouse(1.0))
        shaped=_canopy_crown(greenhouse(.32))
        self.assertLess(dome["roof_crown_width_ratio"],.55)
        self.assertGreater(shaped["roof_crown_width_ratio"],.55)
        self.assertGreater(shaped["roof_crown_width_ratio"],
                           dome["roof_crown_width_ratio"]+.20)

    def test_cross_section_count_distinguishes_rods_from_profiling(self):
        rod=_arm_stations(support(2,tapered=False))
        sculpt=_arm_stations(support(5))
        self.assertEqual(rod["mount_section_count_min"],2)
        self.assertEqual(sculpt["mount_section_count_min"],5)
        self.assertEqual(sculpt["mount_parts_analyzed"],1)
        self.assertGreater(sculpt["mount_root_tip_taper_ratio"],1.25)
        self.assertGreater(sculpt["mount_root_tip_taper_ratio"],rod["mount_root_tip_taper_ratio"]+.25)
        self.assertEqual(rod["mount_root_tip_taper_ratio"],1.)

    def test_cockpit_shoulder_is_measured_on_actual_hull_vertices(self):
        base=[(-.80,.91,-.08),(-.88,.87,0),(.80,.91,-.08),(.88,.87,0),
              (-.70,.81,.08),(.70,.81,.08)]
        after=[(x*1.15,y,z) for x,y,z in base]
        # add full-height hull vertices so the upper-surface band exists
        base += [(-.6,.5,-1),(.6,.5,1),(-.15,1.06,1.1),(.15,1.06,-1.1)]
        after += [(-.6,.5,-1),(.6,.5,1),(-.15,1.06,1.1),(.15,1.06,-1.1)]
        before=_cockpit_shoulder_span(base)
        after_measure=_cockpit_shoulder_span(after)
        self.assertGreater(before["body_cockpit_samples"],0)
        self.assertGreater(
            after_measure["body_cockpit_shoulder_span"],
            before["body_cockpit_shoulder_span"]+.025)

    def test_rear_nacelle_flaring_is_real_radius_change(self):
        def mesh(radii):
            pts=[]
            for ring,rad in enumerate(radii):
                for index in range(20):
                    theta=2*math.pi*index/20
                    pts.append((.7+rad*math.cos(theta),.8+rad*math.sin(theta),
                                ring*.12))
            return [pts]
        plain=_rear_nacelle_profile(mesh([.24,.24]))
        sculpt=_rear_nacelle_profile(mesh([.25,.35,.33,.29,.25,.24]))
        self.assertEqual(plain["engine_housing_flare_ratio"],1.)
        self.assertEqual(plain["engine_housing_axial_sections"],2)
        self.assertGreater(sculpt["engine_housing_flare_ratio"],1.25)
        self.assertEqual(sculpt["engine_housing_axial_sections"],6)

    def test_missing_geometry_cannot_get_positive_score(self):
        self.assertEqual(_canopy_crown([])["roof_crown_width_ratio"],0)
        self.assertEqual(_arm_stations([])["mount_section_count_min"],0)
        self.assertEqual(_arm_stations([])["mount_root_tip_taper_ratio"],0)
        self.assertEqual(_cockpit_shoulder_span([])["body_cockpit_shoulder_span"],0)
        self.assertEqual(_rear_nacelle_profile([])["engine_housing_flare_ratio"],0)


if __name__=="__main__":
    unittest.main()
