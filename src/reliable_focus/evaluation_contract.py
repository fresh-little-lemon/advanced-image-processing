"""Fail-closed metadata contracts; no image loading or held-out execution.

These checks establish internal consistency, not proof of unseen-data history,
semantic deduplication, independent metric validation or actual runtime identity.
"""
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import PurePosixPath
import re
import numpy as np
from .core import decode_srgb, encode_srgb, validate

SCHEMA_VERSION = "fusion-evaluation-contract/1"
PROTOCOL_ID = "formal-draft-20261018"
SPLITS = {"train", "validation", "test", "external_test", "exploration"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    """SHA-256 of sorted compact UTF-8 JSON, prohibiting NaN and Infinity."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def check_hash(value, label):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
            f"{label}: require lowercase SHA-256")


def validate_manifest(scenes):
    require(isinstance(scenes, list), "Manifest scenes must be a list")
    seen, groups, hashes, paths = set(), {}, {}, {}
    for scene in scenes:
        sid, group, split = (scene.get(k) for k in ("scene_id", "group_id", "split"))
        require(isinstance(sid, str) and sid and sid not in seen, "Duplicate/missing scene_id")
        require(isinstance(group, str) and group, f"{sid}: missing group_id")
        require(split in SPLITS, f"{sid}: unknown split")
        require(groups.get(group, split) == split, f"{sid}: group leakage across splits")
        groups[group] = split
        seen.add(sid)
        files = scene.get("files")
        require(isinstance(files, list), f"{sid}: files must be a list")
        roles = [f.get("role") for f in files]
        require(sorted(roles) in (["A", "B"], ["A", "B", "GT"]),
                f"{sid}: require unique roles A/B and optional GT")
        shapes = set()
        for f in files:
            check_hash(f.get("sha256"), f"{sid}/{f['role']}")
            path = f.get("path")
            require(isinstance(path, str) and path and not PurePosixPath(path).is_absolute()
                    and ".." not in PurePosixPath(path).parts and "\\" not in path,
                    f"{sid}: require a safe relative data path")
            require(all(type(f.get(k)) is int and f[k] > 0 for k in ("width", "height", "bytes")),
                    f"{sid}: invalid dimensions or byte count")
            require(f.get("mode") == "RGB", f"{sid}: expected RGB file")
            shapes.add((f["height"], f["width"]))
            for lookup, key in ((hashes, f["sha256"]), (paths, path)):
                require(lookup.get(key, split) == split, f"{sid}: file leakage across splits")
                lookup[key] = split
        require(len(shapes) == 1, f"{sid}: A/B/GT dimensions differ")
    return {"scenes": len(scenes), "groups": len(groups), "splits": dict(Counter(s["split"] for s in scenes))}


def validate_manifest_bundle(master, split_manifests):
    """Verify memberships and byte-independent scene metadata equality."""
    scenes = master["scenes"] if isinstance(master, dict) else master
    report = validate_manifest(scenes)
    for split, subset in split_manifests.items():
        require(split in SPLITS, f"Unknown split {split}")
        validate_manifest(subset)
        expected = {s["scene_id"]: s for s in scenes if s["split"] == split}
        actual = {s["scene_id"]: s for s in subset}
        require(actual == expected, f"{split}: split manifest differs from master")
    require(set(s["split"] for s in scenes) <= set(split_manifests), "Missing split manifest")
    return report


def paired_uint8_inputs(a, b, *, noise_a_255, noise_b_255, seed):
    """Oct-18 pilot convention: encoded RGB -> linear noise -> clip -> uint8.

    Explicit PCG64; draw A then B even when a noise standard deviation is zero.
    Call once per case and share the exact returned pixels/files across methods.
    This helper does not perform exposure/registration or the older 27-cell v1.
    """
    a, b = validate(a), validate(b)
    require(a.shape == b.shape, "A/B dimensions differ")
    require(type(seed) is int and 0 <= seed < 2**64, "Seed must be uint64 integer")
    for value in (noise_a_255, noise_b_255):
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "Noise standard deviations must be finite and nonnegative")
    rng = np.random.Generator(np.random.PCG64(seed))
    outputs = []
    for source, sigma in ((a, noise_a_255), (b, noise_b_255)):
        noisy = np.clip(decode_srgb(source) + rng.normal(0, sigma/255, source.shape), 0, 1)
        outputs.append(np.floor(np.clip(encode_srgb(noisy), 0, 1)*255+.5).astype(np.uint8))
    return tuple(outputs)


def validate_ablation(configs):
    """Require exactly 2x2x2 settings and an identical non-target backbone."""
    keys = ("estimator", "subtract_mean", "normalize_variance")
    expected = set(itertools.product(("same_sample", "crossfit"), (False, True), (False, True)))
    require(isinstance(configs, list) and len(configs) == 8, "Require all eight ablation cells")
    observed, common = set(), None
    for cfg in configs:
        require(all(k in cfg for k in keys), "Missing ablation factor")
        require(type(cfg["subtract_mean"]) is bool and type(cfg["normalize_variance"]) is bool,
                "Ablation switches must be booleans")
        factors = tuple(cfg[k] for k in keys)
        require(factors in expected and factors not in observed, "Invalid/duplicate ablation cell")
        observed.add(factors)
        backbone = {k: v for k, v in cfg.items() if k not in keys and k != "config_id"}
        require(bool(backbone), "Ablation backbone must be explicit")
        require(common is None or backbone == common, "Non-target ablation parameters differ")
        common = backbone
    return {"cells": len(observed), "backbone_sha256": digest(common)}


def validate_run_record(run, *, scenes, manifest_sha256):
    """Validate the documented v1 result schema, including failed method rows."""
    validate_manifest(scenes)
    require(run.get("schema_version") == SCHEMA_VERSION, "Unknown result schema")
    require(run.get("protocol_id") == PROTOCOL_ID, "Wrong protocol version")
    require(run.get("evidence_level") in {"synthetic_contract_only", "exploratory"},
            "This contract version cannot certify formal/native-MATLAB results")
    check_hash(manifest_sha256, "manifest_sha256")
    require(run.get("manifest_sha256") == manifest_sha256, "Manifest hash mismatch")
    check_hash(run.get("protocol_sha256"), "protocol_sha256")
    for key in ("code", "model", "runtime"):
        require(isinstance(run.get(key), dict) and run[key], f"Missing {key} object")
        require(run.get(key+"_sha256") == digest(run[key]), f"{key} hash mismatch")
    code = run["code"]
    require(isinstance(code.get("base_commit"), str) and re.fullmatch(r"[0-9a-f]{40}", code["base_commit"]),
            "Require a 40-character base commit plus actual source hashes")
    require(isinstance(code.get("source_sha256"), dict) and code["source_sha256"], "Missing source hashes")
    for name, value in code["source_sha256"].items():
        check_hash(value, name)
    require(run["model"].get("kind") == "non_learned" and run["model"].get("artifact_sha256") is None,
            "Classical pipeline must explicitly record no trained model artifact")
    configs = run["model"].get("configs")
    require(isinstance(configs, dict) and configs and all(isinstance(v,dict) and v for v in configs.values()),
            "Missing exact per-method configs")
    methods = set(configs)
    runtime = run["runtime"]
    engine = runtime.get("engine")
    require(engine in {"python", "octave", "matlab"} and isinstance(runtime.get("version"), str)
            and runtime["version"] and isinstance(runtime.get("dependencies"), dict), "Missing runtime identity")
    expected_label = {"python": "python_execution", "octave": "octave_compatibility", "matlab": "matlab_execution"}[engine]
    require(runtime.get("execution_label") == expected_label, "Runtime label must not relabel Octave as MATLAB")
    scene_map = {s["scene_id"]: s for s in scenes}
    cases, clean, condition_keys = {}, set(), set()
    require(isinstance(run.get("cases"), list) and run["cases"], "Missing cases")
    for case in run["cases"]:
        cid, sid = case.get("case_id"), case.get("scene_id")
        require(isinstance(cid, str) and cid and cid not in cases and sid in scene_map, "Unknown/duplicate case")
        scene = scene_map[sid]
        require(scene["split"] in {"validation", "exploration"}, "Held-out evaluation is not enabled by this validator")
        require(case.get("split") == scene["split"] and case.get("group_id") == scene["group_id"], "Case split/group mismatch")
        require(type(case.get("seed")) is int and 0 <= case["seed"] < 2**64, "Invalid case seed")
        require(case.get("input_order") == ["A", "B"], "Input order must be explicit A then B")
        for key in ("noise_a_255", "noise_b_255"):
            value = case.get(key)
            require(type(value) in (int,float) and math.isfinite(value) and value >= 0, "Invalid noise condition")
        key = (sid, case["noise_a_255"], case["noise_b_255"], case["seed"])
        require(key not in condition_keys, "Duplicate scene/condition/seed")
        condition_keys.add(key)
        if case["noise_a_255"] == case["noise_b_255"] == 0:
            require(sid not in clean, "Clean conditions must not be counted repeatedly by seed")
            clean.add(sid)
        hashes = case.get("input_sha256")
        require(isinstance(hashes, dict) and set(hashes) == {"A", "B"}, "Require role-keyed input hashes")
        for role in ("A", "B"):
            check_hash(hashes[role], f"{cid}/{role}")
        shape = case.get("shape")
        require(isinstance(shape,list) and len(shape)==3 and shape[2]==3
                and all(type(x) is int and x > 0 for x in shape), "Invalid input shape")
        dims = scene["files"][0]
        require(shape == [dims["height"], dims["width"], 3], "Case changed native resolution")
        cases[cid] = case
    rows = run.get("results")
    require(isinstance(rows, list), "Missing result rows")
    seen, failed, perfect = set(), 0, 0
    for row in rows:
        key = (row.get("case_id"), row.get("method_id"))
        require(key[0] in cases and key[1] in methods and key not in seen, "Unknown/duplicate result row")
        seen.add(key)
        case = cases[key[0]]
        require(row.get("seed") == case["seed"] and row.get("input_sha256") == case["input_sha256"],
                "Methods must share case seeds and exact A/B input hashes")
        require(row.get("status") in {"ok", "failed"}, "Unknown result status")
        if row["status"] == "failed":
            require(isinstance(row.get("failure_reason"),str) and row["failure_reason"], "Missing failure reason")
            require(row.get("metrics") is None, "Failed rows cannot publish metrics")
            failed += 1
            continue
        require(row.get("output_shape") == case["shape"], "Output shape mismatch")
        check_hash(row.get("output_sha256"), "output_sha256")
        m = row.get("metrics")
        require(isinstance(m,dict) and m.get("color_domain") == "linear_rgb" and m.get("data_range") == 1,
                "Formal draft scores must explicitly use unit-range linear RGB")
        require(m.get("crop_border") == 0 and m.get("valid_pixels") == case["shape"][0]*case["shape"][1],
                "This native pre-registered track requires common full-image support")
        require(type(m.get("mae_rgb")) in (int,float) and math.isfinite(m["mae_rgb"]) and 0 <= m["mae_rgb"] <= 1,
                "Invalid MAE")
        if m.get("psnr_status") == "positive_infinity":
            require(m.get("psnr_rgb") is None and m["mae_rgb"] == 0, "Perfect PSNR must be explicit null with zero MAE")
            perfect += 1
        else:
            require(m.get("psnr_status") == "finite" and type(m.get("psnr_rgb")) in (int,float)
                    and math.isfinite(m["psnr_rgb"]) and m["psnr_rgb"] >= 0 and m["mae_rgb"] > 0,
                    "Invalid finite PSNR")
        if "ssim_y_rec709_local" in m:
            from .metric_contract import SSIM_SPEC
            require(m.get("ssim_spec") == SSIM_SPEC, "Wrong/unverified SSIM specification")
            value = m["ssim_y_rec709_local"]
            require(type(value) in (int,float) and math.isfinite(value) and -1.00000001 <= value <= 1.00000001,
                    "Invalid local SSIM")
    require(seen == set(itertools.product(cases, methods)), "Missing results: retain failures in the denominator")
    # Ensures extra numerical metadata cannot smuggle nonstandard NaN/Infinity JSON.
    digest(run)
    return {"cases": len(cases), "methods": len(methods), "rows": len(rows),
            "failed": failed, "positive_infinity_psnr": perfect}
