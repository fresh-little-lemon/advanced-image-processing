import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reliable_focus.crossfit_floor import estimate_crossfit
from reliable_focus.crossfit_fusion import fuse_crossfit
from reliable_focus.diagnostic import LUMA
from probe_crossfit_floor import run
from probe_residual_floor import generate_case,textures

class CrossfitFloorTests(unittest.TestCase):
    def test_stencils_share_no_pixels(self):
        folds=[set(),set()]
        for i in range(4):
            for j in range(4):
                folds[(i+j)%2].update((2*i+u,2*j+v) for u in (0,1) for v in (0,1))
        self.assertFalse(folds[0]&folds[1]);self.assertEqual(len(folds[0]|folds[1]),64)

    def test_constant_and_missing_support(self):
        x=np.full((48,48,3),.4);s,info=estimate_crossfit(x,x)
        self.assertEqual(s,(0.,0.));self.assertTrue(info['available'])
        s,info=estimate_crossfit(np.zeros_like(x),np.ones_like(x))
        self.assertEqual(s,(0.,0.));self.assertFalse(info['available'])

    def test_swap(self):
        a,b,_=generate_case(textures()['stochastic'],.25,'normal',0,5,11)
        for method in ('crossfit_residual_mean','crossfit_residual_full'):
            x,dx,_=run(a,b,method,.6255813533858501);y,dy,_=run(b,a,method,.6255813533858501)
            self.assertAlmostEqual(dx,-dy,places=14);np.testing.assert_allclose(x,y,atol=1e-12)

    def test_homogeneous_noise_variance(self):
        ratios=[];clean=np.full((96,96,3),.45);truth=(np.linalg.norm(LUMA)*5/255)**2
        for seed in range(32):
            rng=np.random.default_rng(seed);noise=clean+rng.normal(0,5/255,clean.shape)
            s,_=estimate_crossfit(clean,noise);ratios.append(s[1]**2/truth)
        self.assertGreater(np.mean(ratios),.85);self.assertLess(np.mean(ratios),1.15)

    def test_scaling(self):
        rng=np.random.default_rng(7);a=rng.uniform(.2,.8,(64,64,3));b=rng.uniform(.2,.8,(64,64,3))
        s,_=estimate_crossfit(a,b);t,_=estimate_crossfit(.5*a+.2,.5*b+.2)
        np.testing.assert_allclose(t,.5*np.array(s),atol=1e-14)

    def test_invalid_inputs(self):
        x=np.ones((32,32,3))*.4
        with self.assertRaises(ValueError):estimate_crossfit(x,x[:20])
        with self.assertRaises(ValueError):estimate_crossfit(x[:8],x[:8])
        with self.assertRaises(ValueError):estimate_crossfit(x*4,x)

    def test_public_api_matches_experiment(self):
        for brightness in ('normal','dark','extreme_white'):
            a,b,_=generate_case(textures()['stochastic'],.75,brightness,0,5,23)
            expected,delta,_=run(a,b,'crossfit_residual_mean',1.)
            actual,details=fuse_crossfit(a,b,return_details=True)
            np.testing.assert_allclose(actual,expected,atol=1e-14)
            self.assertAlmostEqual(delta,details['delta_sigma2'],places=14)
            self.assertFalse(np.shares_memory(actual,a))
            self.assertFalse(np.shares_memory(actual,b))
