import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from assess_candidate_terrain import horn_slope, components
class TerrainTests(unittest.TestCase):
    def test_plane_slope_and_nodata(self):
        z=np.tile(np.arange(7,dtype=float)*30,(7,1))
        result=horn_slope(z)
        np.testing.assert_allclose(result[1:-1,1:-1],45)
        self.assertTrue(np.all(result[0]==-9999))
        z[3,3]=np.nan
        result=horn_slope(z)
        self.assertTrue(np.all(result[2:5,2:5]==-9999))
    def test_eight_connected_components(self):
        labels=components([(0,0),(1,1),(5,5)])
        self.assertEqual(labels[0,0],labels[1,1])
        self.assertNotEqual(labels[0,0],labels[5,5])
