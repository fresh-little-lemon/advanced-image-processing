# Reproduce the phase-2 failure analysis

The [research memo](phase2_failure_analysis.md) reports the differential-noise mechanism, controlled ablations, shared-support experiment, and WHU-098 support-collapse case. Numerical results are in `results/phase2_failure_analysis_20261018/` and `results/shared_support_probe_20261018/`.

## Inputs and metric domain

Use the pinned 26-scene validation manifest and its 78 original A/B/GT images. Each runner checks image SHA-256 before use. Inputs remain in a private data directory; the runners do not read the held-out manifests. Acquisition details are in [the manifest documentation](../data/manifests/README.md).

Both runners load RGB code values with `read_rgb(..., profile_policy='encoded_ignore')` and explicitly apply `decode_srgb` before fusion. That function implements the standard inverse sRGB transfer function. PSNR and MAE use the resulting full-image, three-channel linear-RGB samples. This convention assumes the source values follow sRGB; it does not apply ICC profiles or perform camera colorimetric calibration. Added noise is injected in this decoded domain.

## Commands

Run from the repository root with the project dependencies installed. Every output argument must name a fresh directory. The scripts set numerical-library thread counts to one.

```sh
python scripts/analyze_phase2_failures.py \
  --data-root /private/whu-validation \
  --output /private/new-failure-analysis

python scripts/probe_shared_support.py \
  --data-root /private/whu-validation \
  --output /private/new-shared-support-probe

python scripts/summarize_procedural_oracle.py \
  --metrics /private/completed-phase2/results/phase2_procedural/metrics.csv \
  --output /private/new-procedural-oracle-summary

PYTHONPATH=src python -m unittest discover -s tests -v
```

The probe uses the fixed settings recorded in its protocol: original inputs plus one asymmetric added-noise condition, 8×8 shared support, lowest-20% selection, 64 bootstrap replicates, and fixed seeds. It writes numerical results only. The report's bootstrap and support-collapse findings are retained alongside the positive and negative metric changes.

## Recorded outputs and publication provenance

The published numerical files and historical protocol preserve the completed run byte for byte. `source_sha256` in that historical protocol identifies the original experiment script. The [source provenance record](../results/shared_support_probe_20261018/source_provenance.json) maps it to the portable published runner. Publication changes parameterize filesystem paths and add fresh-output protection; the `paired_delta` and `candidate` function ASTs were checked for exact equality. This publication step did not rerun the experiment.

Source and derived benchmark images are excluded from this publication. The numerical files, methods, and scripts can be reviewed independently of image redistribution permissions.
