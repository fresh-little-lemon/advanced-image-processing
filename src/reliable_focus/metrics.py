"""Diagnostics, not an independently validated official benchmark implementation."""
import numpy as np
from scipy.ndimage import sobel, laplace
from .core import gray

def edge_preservation_local(a,b,f):
    """Xydeas-Petrovic-style Q_AB/F, pilot-compatible unoriented edge angle.

    DOI 10.1049/el:20000267. Named local explicitly: border, angle and flat
    image behavior differ between published/community implementations.
    """
    def gradient(x):
        y=gray(x);gx=sobel(y,axis=1,mode="reflect");gy=sobel(y,axis=0,mode="reflect")
        return np.hypot(gx,gy),np.arctan2(gy,gx)
    gf,af=gradient(f);score=0.;weight=0.
    for x in (a,b):
        g,ang=gradient(x);ratio=np.minimum(g,gf)/(np.maximum(g,gf)+1e-12)
        delta=np.abs((ang-af+np.pi/2)%np.pi-np.pi/2);orient=1-delta/(np.pi/2)
        qg=.9994/(1+np.exp(-15*(ratio-.5)))
        qa=.9879/(1+np.exp(-22*(orient-.8)))
        score+=np.sum(qg*qa*g);weight+=np.sum(g)
    return float(score/weight) if weight>1e-12 else float("nan")

def diagnostics(a,b,f):
    y=gray(f)
    return {"q_local":edge_preservation_local(a,b,f),
            "clipped_fraction":float(np.mean((f<=0)|(f>=1))),
            "laplacian_energy":float(np.mean(laplace(y,mode="reflect")**2)),
            "source_envelope_violation":float(np.mean(np.maximum(np.minimum(a,b)-f,0)+np.maximum(f-np.maximum(a,b),0)))}

def psnr(reference,test):
    mse=float(np.mean((reference-test)**2))
    return float("inf") if mse==0 else -10*np.log10(mse)
