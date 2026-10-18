import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reliable_focus.residual_floor import estimate_floor, fuse_floor, mad_variance
from reliable_focus.diagnostic import energy_fuse, DiagnosticConfig
from probe_residual_floor import run_method
from probe_spatial_support import generate_case, estimate_support
from run_phase2_diagnostics import textures

class ResidualFloorTests(unittest.TestCase):
    def test_constant_zero(self):
        a=np.full((96,96,3),.4)
        sigmas,info=estimate_floor(a,a)
        self.assertEqual(sigmas,(0.,0.));self.assertTrue(info['available'])
        np.testing.assert_allclose(fuse_floor(a,a)[0],a,atol=1e-14)

    def test_missing_support(self):
        a=np.zeros((32,32,3));b=np.ones_like(a)
        sigmas,info=estimate_floor(a,b)
        self.assertEqual(sigmas,(0.,0.));self.assertFalse(info['available'])
        self.assertEqual(info['selected_blocks_per_source'],0)
        self.assertTrue(np.all(np.isfinite(fuse_floor(a,b)[0])))

    def test_shared_guide_matches_previous(self):
        a,b,_=generate_case(textures()['stochastic'],.25,'normal',0,5,11)
        sigmas,info=estimate_floor(a,b,ranking='guide',shared=True)
        delta,previous=estimate_support(a,b)
        self.assertAlmostEqual(sigmas[0]**2-sigmas[1]**2,delta,places=14)
        self.assertEqual(info['selected_blocks_per_source'],previous['selected_blocks'])

    def test_factorial_zero_mean_identity(self):
        rng=np.random.default_rng(17);a=rng.uniform(.2,.8,(48,48,3));b=rng.uniform(.2,.8,(48,48,3))
        sigmas,_=estimate_floor(a,b)
        actual,delta,_=run_method(a,b,'residual_variance_no_mean',(0.,0.))
        expected=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known',subtract_mean=False),sigmas)[0]
        self.assertEqual(delta,0.);np.testing.assert_allclose(actual,expected,atol=1e-14)

    def test_all_candidates_swap(self):
        a,b,_=generate_case(textures()['stochastic'],.75,'dark',5,0,23)
        for method in ('independent_guide','shared_residual','independent_residual','residual_variance_no_mean','residual_full'):
            x,dx,_=run_method(a,b,method,(.01,0.));y,dy,_=run_method(b,a,method,(0.,.01))
            self.assertAlmostEqual(dx,-dy,places=14);np.testing.assert_allclose(x,y,atol=1e-12)

    def test_scaling_covariance(self):
        rng=np.random.default_rng(2);a=rng.uniform(.2,.8,(80,80,3));b=rng.uniform(.2,.8,(80,80,3))
        s,_=estimate_floor(a,b);t,_=estimate_floor(.5*a+.2,.5*b+.2)
        np.testing.assert_allclose(t,np.array(s)*.5,atol=1e-14)

    def test_validation(self):
        x=np.ones((32,32,3))*.4
        with self.assertRaises(ValueError):estimate_floor(x,x,ranking='invalid')
        with self.assertRaises(ValueError):estimate_floor(x,x[:20])
        with self.assertRaises(ValueError):estimate_floor(x[:8],x[:8])
        y=x.copy();y[0,0,0]=np.nan
        with self.assertRaises(ValueError):estimate_floor(x,y)

    def test_mad_translation_and_scale(self):
        x=np.arange(64,dtype=float)
        self.assertAlmostEqual(mad_variance(x+17),mad_variance(x))
        self.assertAlmostEqual(mad_variance(x*3),mad_variance(x)*9)

    def test_selection_partition(self):
        a,b,_=generate_case(textures()['stochastic'],.5,'normal',0,5,11)
        _,info=estimate_floor(a,b)
        self.assertEqual(len(info['selected_quadrants']),2)
        for counts in info['selected_quadrants']:self.assertEqual(sum(counts),info['selected_blocks_per_source'])
        self.assertGreaterEqual(info['selected_overlap_fraction'],0.)
        self.assertLessEqual(info['selected_overlap_fraction'],1.)
