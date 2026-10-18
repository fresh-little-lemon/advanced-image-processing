"""Cross-fitted residual selection on disjoint 2x2 high-pass stencils.

Selection and noise estimation use complementary spatial samples. Under
spatially independent noise the two stencil sets share no input pixels. Each
source chooses its own blocks; the two fold variance estimates are averaged.
Texture and spatially correlated noise can still bias this estimate.
"""
import numpy as np
from .core import gray, validate
from .diagnostic import valid_support
from .residual_floor import mad_variance


def estimate_crossfit(a,b):
    a,b=validate(a),validate(b)
    if a.shape!=b.shape or min(a.shape[:2])<12:
        raise ValueError('require matching RGB inputs of size at least12')
    valid=valid_support(a,b);h,w=valid.shape
    positions=[(i,j) for i in range(2,h-9,8) for j in range(2,w-9,8) if valid[i:i+8,j:j+8].all()]
    k=max(1,int(np.ceil(.2*len(positions))))
    info={'eligible_blocks':len(positions),'selected_blocks_per_source_per_fold':k if positions else 0,
          'available':bool(positions) and k>=2,'valid_pixel_fraction':float(valid.mean()),'fold_variances':[]}
    if not info['available']:return (0.,0.),info
    # The sixteen 2x2 stencils fit entirely within an 8x8 block and do not overlap.
    parity=(np.indices((4,4)).sum(axis=0)%2).ravel()
    variances=[]
    for image in (a,b):
        y=gray(image);hp=y[1:,1:]-y[:-1,1:]-y[1:,:-1]+y[:-1,:-1]
        blocks=np.stack([hp[i:i+8:2,j:j+8:2].ravel() for i,j in positions])
        folds=[]
        for fold in (0,1):
            train=blocks[:,parity==fold];test=blocks[:,parity!=fold]
            score=np.median(abs(train-np.median(train,axis=1)[:,None]),axis=1)
            ids=np.argsort(score,kind='stable')[:k]
            folds.append(mad_variance(test[ids]))
        info['fold_variances'].append(folds);variances.append(float(np.mean(folds)))
    return tuple(float(np.sqrt(v)) for v in variances),info
