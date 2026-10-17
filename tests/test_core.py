import unittest
import numpy as np
from reliable_focus.core import Config,fuse,decode_srgb,encode_srgb,focus,noise_sigma
from reliable_focus.metrics import edge_preservation_local,psnr

class FusionTests(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(7)
        self.a=self.rng.random((32,39,3));self.b=self.rng.random((32,39,3))
    def test_identity(self):
        for method in ['average','laplacian','sml','guided','experimental','noise_energy']:
            np.testing.assert_allclose(fuse(self.a,self.a,Config(method=method)),self.a,atol=1e-14)
    def test_bounds_and_determinism(self):
        for method in ['average','laplacian','sml','guided','experimental','noise_energy']:
            c=Config(method=method)
            x,w=fuse(self.a,self.b,c,True)
            self.assertTrue(np.all((x>=0)&(x<=1)))
            np.testing.assert_array_equal(x,fuse(self.a,self.b,c))
            np.testing.assert_allclose(x,w[...,None]*self.a+(1-w[...,None])*self.b)
    def test_constants_tie(self):
        a=np.full((8,9,3),.2);b=np.full_like(a,.8)
        np.testing.assert_allclose(fuse(a,b,Config(method='laplacian')),a)
        np.testing.assert_allclose(fuse(a,b,Config(method='experimental')),(a+b)/2)
    def test_average(self):
        np.testing.assert_array_equal(fuse(self.a,self.b,Config(method='average')),(self.a+self.b)/2)
    def test_srgb_round_trip(self):
        np.testing.assert_allclose(encode_srgb(decode_srgb(self.a)),self.a,atol=1e-15)
    def test_linear_light_differs(self):
        a=np.zeros((4,4,3));b=np.ones_like(a)
        self.assertGreater(fuse(a,b,Config(method='average',linear_light=True)).mean(),.7)
    def test_reject_bad_input(self):
        for x in [self.a*2,np.full_like(self.a,np.nan),self.a.astype('uint8'),self.a[:,:,0]]:
            with self.assertRaises(ValueError):fuse(x,self.b)
        with self.assertRaises(ValueError):fuse(self.a,self.b[:-1])
        with self.assertRaises(ValueError):Config(window=2)
    def test_flat_metric_undefined(self):
        a=np.zeros((4,4,3));self.assertTrue(np.isnan(edge_preservation_local(a,a,a)))
    def test_noise_estimator(self):
        y=np.random.default_rng(1).normal(0,.02,(512,512))
        self.assertLess(abs(noise_sigma(y)-.02),.001)

if __name__=='__main__':unittest.main()
