import argparse,json
from dataclasses import asdict
from .core import Config,fuse
from .io import read_rgb,write_rgb

def main():
    p=argparse.ArgumentParser(description="Registered RGB 8-bit multifocus fusion")
    p.add_argument("a");p.add_argument("b");p.add_argument("output")
    p.add_argument("--method",choices=["average","laplacian","sml","guided","experimental","noise_energy"],default="guided")
    p.add_argument("--config",help="JSON Config fields; overrides --method")
    p.add_argument("--linear-light",action="store_true")
    args=p.parse_args()
    cfg=Config(**json.load(open(args.config))) if args.config else Config(method=args.method,linear_light=args.linear_light)
    write_rgb(args.output,fuse(read_rgb(args.a),read_rgb(args.b),cfg))
    print(json.dumps(asdict(cfg),sort_keys=True))

if __name__=="__main__":main()
