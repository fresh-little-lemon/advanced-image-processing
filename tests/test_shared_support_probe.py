import unittest
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_shared_support import paired_delta,candidate
from reliable_focus.diagnostic import valid_support,energy_fuse,DiagnosticConfig

class ProbeTests(unittest.TestCase):
 def test_source_swap(self):
  rng=np.random.default_rng(71);a=rng.uniform(.2,.8,(80,80,3));b=rng.uniform(.2,.8,(80,80,3));valid=valid_support(a,b)
  from reliable_focus.core import gray
  d,ds,info=paired_delta(gray(a),gray(b),valid);e,es,other=paired_delta(gray(b),gray(a),valid)
  self.assertAlmostEqual(d,-e,places=14);self.assertAlmostEqual(ds,-es,places=14)
  np.testing.assert_allclose(candidate(a,b,ds),candidate(b,a,es),rtol=0,atol=1e-12)
 def test_no_support(self):
  a=np.full((16,16),.4);self.assertEqual(paired_delta(a,a,np.zeros_like(a,dtype=bool))[:2],(0.,0.))
 def test_constant(self):
  a=np.full((24,24,3),.4);np.testing.assert_allclose(candidate(a,a,0),a,rtol=0,atol=1e-15)
 def test_zero_delta_equals_no_mean(self):
  rng=np.random.default_rng(2);a=rng.uniform(.2,.8,(32,32,3));b=rng.uniform(.2,.8,(32,32,3))
  expected=energy_fuse(a,b,DiagnosticConfig(subtract_mean=False))[0]
  np.testing.assert_allclose(candidate(a,b,0),expected,rtol=0,atol=5e-12)
if __name__=='__main__':unittest.main()
