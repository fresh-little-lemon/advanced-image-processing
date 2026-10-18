import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from probe_spatial_support import accept_support, estimate_support, run_method
from probe_shared_support import paired_delta
from reliable_focus.core import gray
from reliable_focus.diagnostic import valid_support


class SpatialSupportTests(unittest.TestCase):
    def test_repeated_support_in_every_quadrant(self):
        info = {'selected_blocks': 8, 'quadrant_blocks': [2, 2, 2, 2], 'available': True}
        self.assertTrue(accept_support(info, 'spatial_gate'))
        self.assertTrue(accept_support(info, 'count_gate'))

    def test_same_count_concentrated_support(self):
        info = {'selected_blocks': 8, 'quadrant_blocks': [8, 0, 0, 0], 'available': True}
        self.assertTrue(accept_support(info, 'count_gate'))
        self.assertFalse(accept_support(info, 'spatial_gate'))

    def test_estimates_match_previous_probe(self):
        rng = np.random.default_rng(17)
        a = rng.uniform(.2, .8, (80, 80, 3)); b = rng.uniform(.2, .8, (80, 80, 3))
        raw, shrunk, old = paired_delta(gray(a), gray(b), valid_support(a, b))
        point, info = estimate_support(a, b)
        boot, boot_info = estimate_support(a, b, bootstrap=True)
        self.assertAlmostEqual(raw, point, places=14)
        self.assertAlmostEqual(shrunk, boot, places=14)
        self.assertEqual(old['blocks'], info['selected_blocks'])
        self.assertEqual(sum(info['quadrant_blocks']), info['selected_blocks'])

    def test_no_support_falls_back_to_no_mean(self):
        a = np.zeros((32, 32, 3)); b = np.ones_like(a)
        expected, _, _ = run_method(a, b, 'no_mean', (0., 0.))
        actual, delta, info = run_method(a, b, 'spatial_gate', (0., 0.))
        self.assertEqual(delta, 0.)
        self.assertFalse(info['accepted'])
        np.testing.assert_allclose(actual, expected, atol=1e-14)

    def test_swap_equivariance(self):
        rng = np.random.default_rng(19)
        a = rng.uniform(.2, .8, (96, 96, 3)); b = rng.uniform(.2, .8, (96, 96, 3))
        x, dx, _ = run_method(a, b, 'spatial_gate', (0., .01))
        y, dy, _ = run_method(b, a, 'spatial_gate', (.01, 0.))
        self.assertAlmostEqual(dx, -dy, places=14)
        np.testing.assert_allclose(x, y, rtol=0, atol=1e-12)
