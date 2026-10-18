"""Reference fusion with cross-fitted mean correction and global variance model."""
import numpy as np
from scipy.ndimage import laplace,median_filter
from .core import validate,gray,noise_sigma,box,guided_filter
from .crossfit_floor import estimate_crossfit


def fuse_crossfit(a,b,return_details=False):
    """Fuse registered linear RGB floats with fixed classical operators.

    Exposure compensation, alignment, and color decoding belong to the caller.
    The estimator uses unsaturated common support, source-specific residual
    selection, and disjoint estimation samples. Missing support sets the mean
    correction to zero while preserving the global uncertainty normalization.
    This experimental API does not change the established baseline CLI.
    """
    a,b=validate(a),validate(b)
    sigmas,details=estimate_crossfit(a,b)
    delta=sigmas[0]**2-sigmas[1]**2
    ya,yb=gray(a),gray(b);energies=[];variances=[]
    for y in (ya,yb):
        response=laplace(y,mode='reflect');nu=20*noise_sigma(y)**2
        energies.append(box(response**2,7))
        variances.append(4*box(2*nu**2+4*nu*np.maximum(response**2-nu,0),7)/49)
    score=(energies[0]-energies[1]-20*delta)/np.sqrt(variances[0]+variances[1]+1e-8)
    raw=1/(1+np.exp(-np.clip(score,-30,30)))
    weight=guided_filter((ya+yb)/2,median_filter(raw,size=7,mode='reflect'))
    result=np.clip(weight[...,None]*a+(1-weight[...,None])*b,0,1)
    if return_details:return result,{**details,'sigmas':list(sigmas),'delta_sigma2':delta}
    return result
