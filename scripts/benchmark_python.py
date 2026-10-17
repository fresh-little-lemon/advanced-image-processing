#!/usr/bin/env python3
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,json,time,resource,platform
import numpy as np
from reliable_focus import Config,fuse
from reliable_focus.io import read_rgb
p=argparse.ArgumentParser();p.add_argument('a');p.add_argument('b');p.add_argument('--output',required=True);args=p.parse_args()
a,b=[read_rgb(x,profile_policy='encoded_ignore') for x in [args.a,args.b]]
rows=[]
for method in ['average','laplacian','sml','guided','experimental','noise_energy']:
    cfg=Config(method=method)
    for _ in range(2):fuse(a,b,cfg)
    timings=[]
    for _ in range(7):
        t=time.perf_counter();fuse(a,b,cfg);timings.append(time.perf_counter()-t)
    rows.append({'method':method,'seconds':timings,'median_seconds':float(np.median(timings))})
result={'architecture':platform.machine(),'python':platform.python_version(),'shape':list(a.shape),'threads':1,'warmups':2,'repeats':7,'scope':'core fusion including validation/allocation, excluding decoding/output/metrics','peak_process_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'results':rows}
with open(args.output,'w') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
