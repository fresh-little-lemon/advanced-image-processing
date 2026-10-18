"""Float64 RGB reference implementation; all spatial boundaries use reflect.

Guided filtering: He, Sun, Tang (ECCV 2010), DOI 10.1007/978-3-642-15549-9_1.
SML: Nayar and Nakagawa (PAMI 1994), DOI 10.1109/34.308479.
Our single-scale guided mask baseline is NOT the complete Li et al. 2013 GFF.
"""
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import uniform_filter, laplace, convolve1d, median_filter

@dataclass(frozen=True)
class Config:
    method: str = "guided"
    window: int = 7
    radius: int = 5
    epsilon: float = 1e-3
    linear_light: bool = False
    noise_correction: bool = True
    exposure_normalization: bool = True
    confidence_weighting: bool = True

    def __post_init__(self):
        if self.method not in {"average", "laplacian", "sml", "guided", "experimental", "noise_energy"}:
            raise ValueError("Unknown fusion method")
        if self.window < 1 or self.window % 2 != 1 or self.radius < 0 or self.epsilon <= 0:
            raise ValueError("Require positive odd window, nonnegative radius, positive epsilon")

def validate(x):
    x = np.asarray(x)
    if x.ndim != 3 or x.shape[2] != 3 or min(x.shape[:2]) < 2:
        raise ValueError("Expected HxWx3 RGB, H/W >= 2")
    if not np.issubdtype(x.dtype, np.floating):
        raise ValueError("Pass normalized floating-point RGB, not integer data")
    if not np.isfinite(x).all() or np.min(x) < 0 or np.max(x) > 1:
        raise ValueError("RGB values must be finite and in [0,1]")
    return x.astype(np.float64, copy=False)

def gray(x):
    return x @ np.array([.299, .587, .114])

def decode_srgb(x):
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055)**2.4)

def encode_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)

def box(x, size):
    return uniform_filter(x, size=size, mode="reflect")

def guided_filter(guide, mask, radius=5, epsilon=1e-3):
    size = 2*radius+1
    mi, mp = box(guide,size), box(mask,size)
    cov = box(guide*mask,size)-mi*mp
    var = np.maximum(box(guide*guide,size)-mi*mi, 0)
    a = cov/(var+epsilon)
    b = mp-a*mi
    return np.clip(box(a,size)*guide+box(b,size),0,1)

def focus(y, window=7, sml=False):
    if sml:
        response = abs(convolve1d(y,[1.,-2.,1.],0,mode="reflect")) + abs(convolve1d(y,[1.,-2.,1.],1,mode="reflect"))
    else:
        response = abs(laplace(y,mode="reflect"))
    return box(response,window)

def noise_sigma(y):
    # Robust diagonal high-pass estimate (kernel norm = 2). Texture biases it high.
    hp = convolve1d(convolve1d(y,[1.,-1.],0,mode="reflect"),[1.,-1.],1,mode="reflect")
    interior = hp[1:-1,1:-1] if min(y.shape)>2 else hp
    return float(np.median(abs(interior-np.median(interior)))/(0.6744897501960817*2))

def fuse(a, b, config=None, return_weight=False):
    """Fuse registered equal-size RGB inputs; no alignment or HDR reconstruction.

Default works in encoded RGB for parity with pilot/C++ baseline. linear_light
    explicitly decodes assumed sRGB before all processing and re-encodes output.
    Exposure normalization changes focus comparison only, not source radiometry.
    """
    c = config or Config()
    a,b = validate(a),validate(b)
    if a.shape != b.shape:
        raise ValueError("Inputs must have equal dimensions and be registered")
    if c.linear_light:
        a,b = decode_srgb(a),decode_srgb(b)
    ya,yb = gray(a),gray(b)
    if c.method == "average":
        weight = np.full(ya.shape,.5)
    else:
        fa,fb = focus(ya,c.window,c.method=="sml"),focus(yb,c.window,c.method=="sml")
        if c.method == "noise_energy":
            # Signed noise-corrected squared Laplacian response; retain negative
            # estimates for unbiased expected energy differences under AWGN.
            energies=[];variances=[]
            for y in (ya,yb):
                scale=1/(float(np.mean(y))+.03) if c.exposure_normalization else 1.
                response=laplace(y,mode="reflect")*scale
                nu=20*(noise_sigma(y)*scale)**2 if c.noise_correction else 0.
                corrected=response**2-nu
                energies.append(box(corrected,c.window))
                # Correlation-adjusted variance proxy, NOT calibrated uncertainty.
                variances.append(4*box(2*nu**2+4*nu*np.maximum(corrected,0),c.window)/(c.window*c.window))
            gap=energies[0]-energies[1]
            if c.confidence_weighting:
                z=np.clip(gap/np.sqrt(variances[0]+variances[1]+1e-8),-30,30)
                weight=1/(1+np.exp(-z))
            else:
                weight=(gap>=0).astype(float)
        elif c.method == "experimental":
            # Expected |four-neighbor Laplacian| for white Gaussian noise.
            if c.noise_correction:
                factor = np.sqrt(20)*np.sqrt(2/np.pi)
                fa = np.maximum(fa-factor*noise_sigma(ya),0)
                fb = np.maximum(fb-factor*noise_sigma(yb),0)
            if c.exposure_normalization:
                fa = fa/(box(ya,c.window)+.03)
                fb = fb/(box(yb,c.window)+.03)
            if c.confidence_weighting:
                # Flat/unreliable regions approach neutral blending instead of
                # arbitrary source A. This may reduce sharpness; report ablations.
                weight = .5 + .5*(fa-fb)/(fa+fb+.005)
            else:
                weight = (fa>=fb).astype(float)
        else:
            weight = (fa>=fb).astype(float)
        if c.method in {"guided","experimental","noise_energy"}:
            weight = guided_filter((ya+yb)/2,median_filter(weight,size=c.window,mode="reflect"),c.radius,c.epsilon)
    result = np.clip(weight[...,None]*a+(1-weight[...,None])*b,0,1)
    if c.linear_light:
        result = encode_srgb(result)
    return (result,weight) if return_weight else result
