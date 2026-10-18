# Evaluation contract hardening, 2026-10-18

Status: engineering checks implemented and locally tested. No new paper-quality
results, held-out runs, original-author changes or native MATLAB validation.

## Reproduce

Use the existing `requirements-repro.txt` environment. No new dependency is needed.

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -v
python scripts/check_evaluation_contract.py --output /tmp/fusion-contract-audit.json
python scripts/check_evaluation_contract.py --output /tmp/fusion-contract-selftest.json \
  --write-selftest-bundle /tmp/fusion-contract-synthetic-bundle.json
python scripts/check_evaluation_contract.py --output /tmp/fusion-contract-recheck.json \
  --run-bundle /tmp/fusion-contract-synthetic-bundle.json
```

The checker reads public scene metadata, hashes and historical result metadata.
It never loads held-out pixels, downloads data, runs fusion on a dataset, starts
MATLAB/Octave, or enables test/external-test execution. Synthetic self-test numbers
only exercise serialization and validation; they are not method-quality evidence.

## Protocol versions are distinct

`docs/evaluation_protocol.md` (2026-10-17) specifies PSNR-Y with 0.299/0.587/0.114,
27-cell perturbations, and 20 warm-ups/100 timing calls. The later
`baselines/gff_author/FORMAL_EVALUATION_PROTOCOL.md` (2026-10-18) remains a draft;
it specifies full-image linear RGB PSNR, supplemental Rec.709 SSIM-Y, the eight-cell
ablation, and 5 warm-ups/30 timing calls. Do not merge those definitions or label
existing exploration as final results. This contract explicitly identifies the
latter as `formal-draft-20261018`; it does not resolve or silently rewrite the old
protocol, and cannot certify final native-MATLAB evidence.

## What is checked

- Public master and split manifests agree exactly: 26 validation/development,
  94 test, 13 external-test scenes, 133 groups; exploration is empty in this new
  public-data manifest. Earlier Lytro/EDMF exploration remains separate
- Scene IDs, group IDs, file hashes and paths cannot cross split boundaries;
  A/B/optional GT roles are unique and dimensions agree
- A formal training set is absent because these are classical methods. Metadata
  isolation cannot establish historical tuning behavior or semantic duplicate
  scenes; the pending semantic audit remains pending
- `paired_uint8_inputs` fixes PCG64, A-then-B draws including zero-sigma draws,
  linear noise, clipping, encoding and one uint8 rounding. It reproduces the
  existing pilot convention. Call once per case; share those exact pixels/files
- The result schema cross-checks each method's seed and role-keyed A/B hashes,
  rejects missing/duplicate method rows, swapped role order, changed dimensions,
  and duplicate clean cases disguised as multiple seeds
- The eight-cell schema allows exactly three changing factors: estimator,
  mean subtraction and variance normalization. All remaining backbone parameters
  agree. An executable invariant checks identical output across the two estimators
  when both corrections and fallback are off
- Each result includes content-addressed code, non-learned model/config, and runtime
  objects. Octave must be labeled `octave_compatibility`; it cannot claim MATLAB
- Failed results remain in the denominator with a reason and no metrics. Exact
  PSNR matches use JSON null plus `positive_infinity`; raw NaN/Infinity is rejected

## Metric behavior and historical impact

`metrics.psnr` now rejects unequal shapes (including broadcastable shapes), integer
arrays, empty/wrong-channel arrays, nonfinite inputs and values outside [0,1].
Arithmetic is explicitly float64. Previously uint8 subtraction/squaring overflowed,
and shape mismatches or NaN could silently produce meaningless numbers.

Valid float64 inputs retain the identical full-image, range-1 formula; 30 seeded
numerical regressions compare exactly. Float32 calls now use float64 arithmetic
and can differ by rounding. Invalid historical calls must be rerun or withdrawn;
they must not be automatically repaired by clipping/normalizing. No historical
result files were changed or recomputed, and the synthetic regression is not proof
that every historical caller supplied valid data.

`metric_contract.score_rgb` is keyword-only and requires an explicit color domain.
It applies a common crop/mask, computes RGB PSNR/MAE, and computes a **local** SSIM-Y
formula with Rec.709, 11x11 Gaussian sigma 1.5, K1=.01, K2=.03, L=1, population
covariance, and valid windows. A mask excludes every SSIM window touching an invalid
pixel. Empty valid support errors instead of silently producing NaN. Tests include
constants, exact identity, an independently written direct-window formula, crops,
masks and wrong domains. Independent library/MATLAB comparison is still pending;
do not call this official SSIM validation or add it to formal tables yet.

Existing `q_local` is unchanged. Its flat-input NaN is explicitly tested as undefined
local behavior; it is not renamed Q_AB/F or silently coerced into a valid score.

## Executable result schema

`evaluation_contract.validate_run_record` is the authoritative executable schema.
`check_evaluation_contract.py --write-selftest-bundle` writes a complete example.

- Root: `schema_version`, `protocol_id`, `evidence_level`, `manifest_sha256`,
  `protocol_sha256`, `code`, `code_sha256`, `model`, `model_sha256`, `runtime`,
  `runtime_sha256`, `cases`, `results`
- Code: actual source-file SHA-256 map and 40-character base commit; a base commit
  alone must not claim that an uncommitted patch was present on the remote
- Model: `kind=non_learned`, `artifact_sha256=null`, exact per-method `configs`;
  there are no learned weights, so no invented model checkpoint hash
- Runtime: engine, version, dependency versions, and matching execution label;
  runtime identity is a declaration to corroborate with real logs, not proof of execution
- Cases: IDs linked to the scene manifest, native shape, explicit A/B order, input
  hashes and noise condition/seed. This checker only admits validation/exploration
- Results: case/method identity, shared input hashes/seed, status, shape/output hash,
  or a failure reason. Successful full-image linear-RGB rows have explicit range,
  crop, valid-pixel count, PSNR status, MAE, and optional local SSIM specification

Object hashes use sorted compact UTF-8 JSON with `ensure_ascii=False`, no NaN and
no Infinity. Bundles declare `manifest_hash_encoding=canonical-json`; this differs
from the byte SHA-256 of a manifest file. Existing `SHA256SUMS` are checked on exact
file bytes. Schema checks attest consistency of declarations; validate actual
source/input/output bytes and capture runtime logs when producing an experiment.

Historical `run.json` records missing the new hash/schema fields are reported as
legacy exploratory evidence. They are not retroactively certified or overwritten.

## Remaining gates

Native MATLAB author execution, independent official metric comparisons, semantic
scene deduplication, final algorithm/parameter freeze and untouched held-out tests
remain outstanding. The 78-case Octave pilot stays compatibility-only. Author GFF
source/defaults and all earlier numerical result files are unchanged.
