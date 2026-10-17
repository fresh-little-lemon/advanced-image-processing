"""Explicit 8-bit sRGB file policy; numerical API also accepts float64."""
from pathlib import Path
import numpy as np
from PIL import Image

def read_rgb(path, *, profile_policy="reject"):
    if profile_policy not in {"reject", "encoded_ignore"}:
        raise ValueError("Unknown profile policy")
    with Image.open(path) as image:
        if image.mode != "RGB":
            raise ValueError(f"{path}: require RGB 8-bit; convert explicitly to avoid hidden range/profile changes")
        if image.info.get("icc_profile") and profile_policy == "reject":
            raise ValueError(f"{path}: embedded ICC profile; explicitly convert to sRGB first")
        return np.asarray(image,dtype=np.float64)/255

def write_rgb(path,image):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.floor(np.clip(image,0,1)*255+.5).astype(np.uint8)).save(path)
