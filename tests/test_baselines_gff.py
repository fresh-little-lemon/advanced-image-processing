import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import unittest
from baselines_gff import (GFFConfig, fuse_gff, guided_scalar,
                          truncated_mean, quantize_u8_unit)


def naive_mean(x, r):
    h,w=x.shape
    return np.array([[x[max(0,y-r):min(h,y+r+1),max(0,z-r):min(w,z+r+1)].mean()
                      for z in range(w)] for y in range(h)])


def test_truncated_mean_matches_direct_edges_and_large_radius():
    x=np.arange(35,dtype=float).reshape(5,7)
    for r in (0,1,3,45):
        np.testing.assert_allclose(truncated_mean(x,r),naive_mean(x,r),atol=1e-12)


def test_guided_regression_matches_direct():
    rng=np.random.default_rng(2);g=rng.random((8,11));p=rng.random((8,11));r=2;e=.03
    mg,mp=naive_mean(g,r),naive_mean(p,r)
    a=(naive_mean(g*p,r)-mg*mp)/(naive_mean(g*g,r)-mg*mg+e)
    b=mp-a*mg
    np.testing.assert_allclose(guided_scalar(g,p,r,e),naive_mean(a,r)*g+naive_mean(b,r),atol=1e-12)


def check_identical_inputs_and_weight_sum(profile):
    x=np.random.default_rng(3).integers(0,256,(19,23,3))/255.
    f,d=fuse_gff([x,x],GFFConfig(profile=profile),True)
    np.testing.assert_allclose(f,x,atol=1e-12)
    for k in ('base_weights','detail_weights'):
        np.testing.assert_allclose(d[k].sum(0),1,atol=1e-15)
        assert d[k].min()>=0


def test_first_maximum_author_tie():
    a=np.full((17,18),.2);b=np.full((17,18),.8)
    f,d=fuse_gff([a,b],return_diagnostics=True)
    assert np.all(d['initial_weights'][0]==1)
    np.testing.assert_allclose(f,a,atol=1e-15)


def test_continuous_tie_symmetric_average():
    a=np.full((17,18),.2);b=np.full((17,18),.8)
    np.testing.assert_allclose(fuse_gff([a,b],GFFConfig(profile='continuous_shared_gray')),.5,atol=1e-12)


def test_quantization_rounding_and_saturation():
    np.testing.assert_array_equal(quantize_u8_unit(np.array([-1,0,.5/255,1.5/255,1,2])),np.array([0,0,1,2,255,255])/255)


def test_no_input_mutation_and_gray_rgb_agree():
    rng=np.random.default_rng(4);a=rng.integers(0,256,(21,22))/255.;b=rng.integers(0,256,(21,22))/255.
    aa=a.copy();f=fuse_gff([a,b]);rgb=fuse_gff([np.repeat(a[...,None],3,2),np.repeat(b[...,None],3,2)])
    np.testing.assert_array_equal(a,aa)
    np.testing.assert_allclose(rgb,np.repeat(f[...,None],3,2),atol=1/255)


def test_reject_bad_shapes_and_nan():
    x=np.zeros((8,8,3))
    with unittest.TestCase().assertRaises(ValueError):fuse_gff([x])
    with unittest.TestCase().assertRaises(ValueError):fuse_gff([x,np.zeros((7,8,3))])
    y=x.copy();y[0,0,0]=np.nan
    with unittest.TestCase().assertRaises(ValueError):fuse_gff([x,y])


def test_identical_author():
    check_identical_inputs_and_weight_sum('author_aligned')

def test_identical_continuous():
    check_identical_inputs_and_weight_sum('continuous_shared_gray')

def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(v) for k,v in sorted(globals().copy().items()) if k.startswith('test_') and callable(v))

if __name__ == '__main__':
    tests=unittest.TestSuite(unittest.FunctionTestCase(v) for k,v in sorted(globals().copy().items()) if k.startswith('test_') and callable(v))
    result=unittest.TextTestRunner(verbosity=2).run(tests)
    sys.exit(not result.wasSuccessful())
