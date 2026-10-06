import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze_sentinel1_change import db_change, NODATA

class DbChangeTests(unittest.TestCase):
    def test_power_ratio_sign_and_units(self):
        before = np.array([[[1, 10]], [[0.1, 1]]], dtype="float32")
        after = np.array([[[10, 1]], [[1, 0.1]]], dtype="float32")
        b, a, delta, valid = db_change(before, after, np.ones((1,2), dtype="uint8"))
        self.assertTrue(valid.all())
        np.testing.assert_allclose(delta, [[[10, -10]], [[10, -10]]], atol=1e-5)

    def test_all_four_measurements_must_be_positive_and_valid(self):
        before = np.ones((2,1,6), dtype="float32")
        after = before.copy()
        before[0,0,0] = 0
        after[1,0,1] = -0.01
        before[1,0,2] = np.nan
        after[0,0,3] = NODATA
        mask = np.array([[1,1,1,1,0,1]], dtype="uint8")
        b, a, delta, valid = db_change(before, after, mask)
        np.testing.assert_array_equal(valid, [[False,False,False,False,False,True]])
        for output in (b,a,delta):
            self.assertTrue(np.all(output[:,:,:5] == NODATA))
        self.assertTrue(np.all(delta[:,:,5] == 0))

if __name__ == "__main__":
    unittest.main()
