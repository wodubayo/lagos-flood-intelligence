import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from explore_sentinel1_thresholds import candidate, remove_small

class CandidateTests(unittest.TestCase):
    def test_threshold_boundary_persistent_dark_and_missing(self):
        b=np.array([-20,-21,-25,-20,-20])
        a=np.array([-23,-24,-28,-23,-22])
        d=a-b
        valid=np.array([True,True,True,False,True])
        np.testing.assert_array_equal(candidate(b,a,d,valid,-21,-3),[True,False,False,False,False])
    def test_cleanup_removes_island_preserves_hole_and_diagonal_connection(self):
        raw=np.zeros((20,20),dtype=bool)
        raw[2:7,2:7]=True
        raw[4,4]=False
        raw[7,7]=True
        raw[15,15]=True
        clean=remove_small(raw,9)
        self.assertFalse(clean[15,15])
        self.assertFalse(clean[4,4])
        self.assertTrue(clean[7,7])
        self.assertEqual(int(clean.sum()),25)
