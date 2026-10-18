"""Phase-2 controlled mechanism experiments, separate from frozen phase-1 API."""
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import gaussian_filter, binary_erosion, laplace, median_filter
from .core import gray,box,noise_sigma,guided_filter,fuse,Config

LUMA=np.array([.299,.587,.114])

def luminance_sigma(covariance):
    covariance=np.asarray(covariance,dtype=float)
    if covariance.shape!=(3,3) or not np.allclose(covariance,covariance.T):
        raise ValueError('Require symmetric RGB 3x3 covariance')
    if np.linalg.eigvalsh(covariance).min() < -1e-14:raise ValueError('Covariance must be positive semidefinite')
    return float(np.sqrt(max(float(LUMA@covariance@LUMA),0)))

def valid_support(a,b,radius=4):
    # Exclude any saturated input channel, plus its entire Laplacian+box support.
    valid=np.all((a>0)&(a<1)&(b>0)&(b<1),axis=-1)
    return binary_erosion(valid,structure=np.ones((2*radius+1,2*radius+1)),border_value=0)

def flat_patch_sigma(y,valid=None,block=8,fraction=.2):
    """Fixed diagnostic: select lowest guide-gradient 20% of full valid blocks.

    Selection is not a proof of flatness; coverage/guide energy remain explicit.
    """
    h,w=y.shape;guide=gaussian_filter(y,1.,mode='reflect')
    gy,gx=np.gradient(guide);energy=gx*gx+gy*gy
    choices=[]
    for i in range(2,h-block-1,block):
        for j in range(2,w-block-1,block):
            region=(slice(i,i+block),slice(j,j+block))
            if valid is None or np.all(valid[region]):choices.append((float(energy[region].mean()),i,j))
    if not choices:return 0.,{'valid':False,'coverage':0.,'guide_energy':float('nan')}
    choices.sort();selected=choices[:max(1,int(np.ceil(len(choices)*fraction)))]
    # h=[[1,-1],[-1,1]]; squared kernel norm4, same as global estimator.
    # Each hp[i,j] uses y[i:i+2,j:j+2], so selected guide blocks
    # have a one-pixel lower/right residual halo. valid is eroded by4
    # in this experiment; its halo therefore remains unsaturated.
    hp=y[1:,1:]-y[:-1,1:]-y[1:,:-1]+y[:-1,:-1]
    values=np.concatenate([hp[i:i+block,j:j+block].ravel() for _,i,j in selected])
    sigma=float(np.median(abs(values-np.median(values)))/(.6744897501960817*2))
    return sigma,{'valid':True,'coverage':len(values)/(h*w),'guide_energy':float(np.mean([v[0] for v in selected]))}

@dataclass(frozen=True)
class DiagnosticConfig:
    sigma_mode:str='estimated_global'
    subtract_mean:bool=True
    normalize_variance:bool=True
    fallback_quantization:bool=False
    kappa:float=4.
    epsilon_variance:float=1e-8
    window:int=7

    def __post_init__(self):
        if self.epsilon_variance<0:raise ValueError('epsilon_variance must be nonnegative')
        if self.sigma_mode not in {'oracle_known','estimated_global','estimated_flat','zero'}:raise ValueError('Unknown sigma mode')

def energy_fuse(a,b,cfg=None,oracle_sigmas=None,valid=None):
    cfg=cfg or DiagnosticConfig();ya,yb=gray(a),gray(b)
    details=[];sigmas=[]
    for i,y in enumerate((ya,yb)):
        if cfg.sigma_mode=='oracle_known':
            if oracle_sigmas is None:raise ValueError('oracle_known requires explicit luma standard deviations')
            sigma=float(oracle_sigmas[i]);detail={'valid':True,'coverage':1.,'guide_energy':0.}
        elif cfg.sigma_mode=='estimated_global':sigma=noise_sigma(y);detail={'valid':True,'coverage':1.,'guide_energy':0.}
        elif cfg.sigma_mode=='estimated_flat':sigma,detail=flat_patch_sigma(y,valid)
        else:sigma=0.;detail={'valid':True,'coverage':1.,'guide_energy':0.}
        if sigma<0 or not np.isfinite(sigma):raise ValueError('Sigma must be finite and nonnegative')
        sigmas.append(sigma);details.append(detail)
    threshold=float(np.linalg.norm(LUMA)/255)
    fallback=cfg.fallback_quantization and (not all(d['valid'] for d in details) or max(sigmas)<=threshold)
    if fallback:
        output,weight=fuse(a,b,Config(method='guided'),True)
        return output,weight,{'sigmas':sigmas,'estimator':details,'fallback':True,'raw_weight':weight}
    energies=[];variances=[]
    for y,sigma in zip((ya,yb),sigmas):
        response=laplace(y,mode='reflect');nu=20*sigma*sigma
        energies.append(box(response**2-(nu if cfg.subtract_mean else 0),cfg.window))
        # Variance formula always uses signal-energy proxy corrected by nu;
        # mean-subtraction switch does not alter variance modeling.
        variances.append(cfg.kappa*box(2*nu**2+4*nu*np.maximum(response**2-nu,0),cfg.window)/(cfg.window**2))
    gap=energies[0]-energies[1]
    denom=np.sqrt((variances[0]+variances[1] if cfg.normalize_variance else 0)+cfg.epsilon_variance)
    # Exact zero-variance limit; epsilon_variance=0 isolates the old floor.
    z=np.divide(gap,denom,out=np.zeros_like(gap),where=denom>0)
    raw=1/(1+np.exp(-np.clip(z,-30,30)))
    raw=np.where(denom>0,raw,np.where(gap>0,1.,np.where(gap<0,0.,.5)))
    weight=guided_filter((ya+yb)/2,median_filter(raw,size=cfg.window,mode='reflect'))
    output=np.clip(weight[...,None]*a+(1-weight[...,None])*b,0,1)
    return output,weight,{'sigmas':sigmas,'estimator':details,'fallback':False,'raw_weight':raw,'energy_a':energies[0],'energy_b':energies[1]}

def reliability(scores,labels,valid,bins=10):
    p=scores[valid];y=labels[valid].astype(float)
    if len(p)==0:return {'brier':float('nan'),'ece':float('nan'),'accuracy':float('nan'),'pixels':0}
    ece=0.
    for i in range(bins):
        selected=(p>=i/bins)&(p<(i+1)/bins) if i<bins-1 else (p>=i/bins)&(p<=1)
        if selected.any():ece+=selected.mean()*abs(p[selected].mean()-y[selected].mean())
    return {'brier':float(np.mean((p-y)**2)),'ece':float(ece),'accuracy':float(np.mean((p>=.5)==y)),'pixels':len(p)}
