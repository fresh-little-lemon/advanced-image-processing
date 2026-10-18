# Rebuilding missing phase-2 outputs

The published snapshot `49427a9a22bf5bbf1e0debf9ade040fa9e1081c7` contains the
phase-2 algorithms, fixed experimental protocols, runners, and diagnostic
write-up. It does **not** contain the directories `results/phase2_procedural`,
`results/phase2_zero_limit`, `results/phase2_validation`,
`results/phase2_validation_zero_limit`, `results/phase2_summary.json`, or the
`deliverables` image panels referenced by that write-up. These outputs can be
recomputed; recomputation must not be described as retrieval of historical files.

## Safe reconstruction

From the repository root, using the project's installed Python environment:

```sh
python scripts/rebuild_phase2.py --output /absolute/path/to/new-phase2-run
```

The output directory must not exist and must be outside the source repository.
The helper refuses to replace an existing run, records Python source hashes,
uses one compute thread, and retains partial output with a failure status if a
command fails. It runs the 2,970-row procedural grid, the 1,080-row zero-variance
limit grid, and the procedural summary. These need no downloaded images and
never evaluate either held-out dataset. Timing fields are new observations and
are not expected to match previous executions.

To also rebuild natural-image validation and all original demo selections:

```sh
python scripts/rebuild_phase2.py \
  --output /absolute/path/to/new-phase2-with-validation \
  --data-root /absolute/path/to/existing-private-data
```

The helper selects only the repository's frozen 26-scene WHU validation
manifest; the validation runner checks each image SHA-256 before evaluation.
This requires exactly its 78 A/B/GT input images. It does not require the 94 WHU
held-out scenes or the 13 external MFFW2 scenes. The source locations and
acquisition instructions are in `data/manifests/README.md`; use separate local
storage and retain upstream attribution and rights restrictions. Existing
validation/GFF CSVs cannot reconstruct the original image pixels.

The demo runner uses the fixed-first, maximum-improvement, and
maximum-regression validation cases, with a fixed center crop. The crop is not
a physical focus-boundary annotation. Neither maximum-improvement examples nor
this validation set establish a general advantage on new scenes.

## Metric conventions

The tracked GFF linear validation CSV and summary report **full-image,
three-channel linear-RGB** PSNR and MAE: 26 scenes, mean PSNR
38.694563686014284 dB and mean MAE 0.0029346479751515787. The phase-2 validation
runner uses that same RGB-MSE convention. Luminance-only linear-Y PSNR is a
different measurement and must not be placed in the same ranking column.
The repository currently does not contain the historical linear-Y outputs
needed to verify that separate evaluation. These numbers must not be inferred
from RGB PSNR or from a historical text report.

A fresh procedural reconstruction is evidence that the published mechanism
experiments can run, not evidence of recovered natural-image results, phase-3
progress, or target-device performance. The C++ implementation covers four
baseline methods; the phase-2 energy candidates remain Python implementations.
ARM64/edge performance is unmeasured here.
