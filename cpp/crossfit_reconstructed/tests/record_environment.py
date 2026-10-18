#!/usr/bin/env python3
import datetime,hashlib,json,os,platform,subprocess
from pathlib import Path
import numpy,scipy
root=Path(__file__).resolve().parents[1]
def command(*args):
    r=subprocess.run(args,capture_output=True,text=True);return r.stdout.strip() if r.returncode==0 else {'returncode':r.returncode,'stderr':r.stderr.strip()}
cpuinfo=Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
cpu=next((x.split(':',1)[1].strip() for x in cpuinfo.splitlines() if x.startswith('model name')),platform.processor())
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in ('.cpp','.hpp','.py','.sh') and 'build' not in p.parts}
result={'measured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'architecture':platform.machine(),'cpu_model':cpu,'logical_cpus_visible':os.cpu_count(),'affinity_cpu_count':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,'compiler':command(os.environ.get('CXX','g++'),'--version'),'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__,'release_flags':'-std=c++17 -Wall -Wextra -Wpedantic -Werror -ffp-contract=off -O3 -DNDEBUG','sanitizer_flags':'-std=c++17 -Wall -Wextra -Wpedantic -Werror -ffp-contract=off -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined','hardware_context':'shared cloud x86 CPU, unpinned process, single-thread estimator; no ARM hardware measurement','source_sha256':files}
(root/os.environ['OUT']/'environment.json').write_text(json.dumps(result,indent=2)+'\n')
