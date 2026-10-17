import unittest
import numpy as np
from scipy.ndimage import laplace
from reliable_focus.diagnostic import luminance_sigma,LUMA,valid_support,flat_patch_sigma,energy_fuse,DiagnosticConfig,reliability
from reliable_focus.core import box

class DiagnosticTests(unittest.TestCase):
    def test_rgb_covariance(self):
        self.assertAlmostEqual(luminance_sigma(np.eye(3)*.01**2),.01*np.linalg.norm(LUMA))
        self.assertAlmostEqual(luminance_sigma(np.ones((3,3))*.01**2),.01)
        with self.assertRaises(ValueError):luminance_sigma(-np.eye(3))
    def test_valid_support(self):
        a=np.full((24,24,3),.5);b=a.copy();b[12,12]=1
        m=valid_support(a,b)
        self.assertFalse(m[:4].any());self.assertFalse(m[8:17,8:17].any());self.assertTrue(m[5,5])
    def test_constant_flat_estimate(self):
        s,d=flat_patch_sigma(np.full((64,64),.4));self.assertEqual(s,0);self.assertTrue(d['valid'])
    def test_expected_energy_bias_monte_carlo(self):
        # Unclipped scalar Gaussian, interior only: E[L(n)^2]=20sigma².
        rng=np.random.default_rng(13);sigma=.02;means=[]
        for _ in range(64):
            n=rng.normal(0,sigma,(96,96));means.append(np.mean(box(laplace(n)**2-20*sigma*sigma,7)[4:-4,4:-4]))
        self.assertLess(abs(np.mean(means)),.00008)
    def test_independent_switches(self):
        rng=np.random.default_rng(4);a=rng.uniform(.2,.8,(32,32,3));b=rng.uniform(.2,.8,(32,32,3))
        _,_,on=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known'),(.01,.03))
        _,_,off=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known',subtract_mean=False),(.01,.03))
        np.testing.assert_allclose(off['energy_a']-on['energy_a'],20*.01**2,atol=1e-15)
        # Variance switch must not modify energy estimates.
        _,_,novar=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known',normalize_variance=False),(.01,.03))
        np.testing.assert_array_equal(on['energy_a'],novar['energy_a'])
    def test_oracle_zero_equals_zero_mode(self):
        rng=np.random.default_rng(3);a=rng.random((24,24,3));b=rng.random((24,24,3))
        x,_,_=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known'),(0,0))
        y,_,_=energy_fuse(a,b,DiagnosticConfig(sigma_mode='zero'))
        np.testing.assert_array_equal(x,y)
    def test_reliability_perfect(self):
        y=np.array([[0,1],[1,0]],dtype=bool);r=reliability(y.astype(float),y,np.ones_like(y))
        self.assertEqual(r['brier'],0);self.assertEqual(r['ece'],0)

class ZeroVarianceTests(unittest.TestCase):
    def test_zero_limit_scale_invariant_raw_decision(self):
        rng=np.random.default_rng(8);a=rng.uniform(.1,.8,(32,32,3));b=rng.uniform(.1,.8,(32,32,3))
        cfg=DiagnosticConfig(sigma_mode='zero',epsilon_variance=0)
        _,_,x=energy_fuse(a,b,cfg);_,_,y=energy_fuse(a*.01,b*.01,cfg)
        np.testing.assert_array_equal(x['raw_weight'],y['raw_weight'])
    def test_zero_limit_flat_is_finite(self):
        a=np.full((32,32,3),.4);b=a.copy()
        f,w,_=energy_fuse(a,b,DiagnosticConfig(sigma_mode='zero',epsilon_variance=0))
        self.assertTrue(np.isfinite(f).all());np.testing.assert_array_equal(w,np.full((32,32),.5))
    def test_equal_sigma_mean_subtraction_cancels(self):
        rng=np.random.default_rng(5);a=rng.uniform(.2,.8,(24,24,3));b=rng.uniform(.2,.8,(24,24,3))
        _,_,x=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known'),(.02,.02))
        _,_,y=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known',subtract_mean=False),(.02,.02))
        np.testing.assert_allclose(x['raw_weight'],y['raw_weight'],atol=1e-12)
