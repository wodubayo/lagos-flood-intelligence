"""Offline tests for scientifically consequential scene-selection rules."""
import sys
import unittest
from pathlib import Path
from shapely.geometry import box, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from acquire_phase1 import event_period, rank_pairs


def scene(name, timestamp, orbit=95, footprint=None, direction='DESCENDING'):
    return {'geometry': mapping(footprint if footprint is not None else box(3, 6, 4, 7)),
            'properties': dict(sceneName=name, startTime=timestamp, platform='Sentinel-1A',
                               pathNumber=orbit, flightDirection=direction, polarization='VV+VH',
                               beamModeType='IW', processingLevel='GRD_HD', frameNumber=571)}


class PairSelectionTests(unittest.TestCase):
    def test_lagos_local_event_boundary(self):
        self.assertEqual(event_period('2024-07-02T22:59:59Z'), 'before')
        self.assertEqual(event_period('2024-07-02T23:00:00Z'), 'during')
        self.assertEqual(event_period('2024-07-04T23:00:00Z'), 'after')

    def test_orbit_and_direction_must_match(self):
        features = [scene('before', '2024-06-21T05:30:00Z'),
                    scene('wrong-orbit', '2024-07-03T05:30:00Z', orbit=103),
                    scene('wrong-pass', '2024-07-03T05:30:00Z', direction='ASCENDING')]
        self.assertEqual(rank_pairs(features, box(3, 6, 4, 7)), [])

    def test_event_day_beats_tiny_later_coverage_gain(self):
        features = [scene('before', '2024-06-21T05:30:00Z'),
                    scene('event', '2024-07-03T05:30:00Z', footprint=box(3.001, 6, 4, 7)),
                    scene('late', '2024-07-15T05:30:00Z')]
        pairs = rank_pairs(features, box(3, 6, 4, 7))
        self.assertEqual(pairs[0]['after'], 'event')
        self.assertLess(pairs[0]['common_aoi_fraction'], 1)

    def test_nonoverlapping_scenes_cannot_form_pair(self):
        features = [scene('before', '2024-06-21T05:30:00Z', footprint=box(3, 6, 3.3, 7)),
                    scene('after', '2024-07-03T05:30:00Z', footprint=box(3.7, 6, 4, 7))]
        self.assertEqual(rank_pairs(features, box(3, 6, 4, 7)), [])


if __name__ == '__main__':
    unittest.main()
