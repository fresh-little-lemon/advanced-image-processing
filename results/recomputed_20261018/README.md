# Frozen 26-scene WHU validation reconstructed on 2026-10-18 UTC

These are fresh computations from published phase-2 code, not retrieval of an old result archive. Inputs: exactly 78 A/B/GT files from the frozen validation manifest, all SHA-256 verified. The public archive was downloaded at upstream commit 6071f2909f5563ccb9bcd71317f5102eefe13e6f, archive SHA-256 ec6bb595a56ca1b4a36d4ac2081cadb915a9e4718d54391d05c9dbcb419ea413. Only the 78 validation images were extracted. Other archive entries were skipped. The 94 WHU held-out scenes and 13 external MFFW2 scenes were not opened or evaluated.

Source: https://github.com/HaoZhang1018/MFI-WHU/tree/6071f2909f5563ccb9bcd71317f5102eefe13e6f

## Same predictions, distinct metric domains

All methods receive the same sRGB-decoded linear-RGB inputs. Each prediction is measured twice: full-image RGB MSE, and full-image luminance MSE using Y=0.299R+0.587G+0.114B. Both PSNR definitions use range=1. MAE below is full-image RGB MAE. Do not pool RGB and Y PSNR into one ranking column. No SSIM was recomputed.

| Method | Mean RGB PSNR (dB) | Mean Y PSNR (dB) | Mean RGB MAE |
|---|---:|---:|---:|
| guided | 37.76874365 | 38.66973576 | 0.0022544243 |
| global_full | 37.23697050 | 38.05877467 | 0.0039349728 |
| flat_full | 37.81229051 | 38.70180798 | 0.0024868956 |
| gff_continuous_shared_gray | 38.69456369 | 39.50994106 | 0.0029346480 |

The GFF per-scene RGB PSNR and MAE match the tracked repository CSV exactly (maximum absolute discrepancy 0.0 for both). The freshly recomputed Y-PSNR reproduces the four historical rounded Y values, explaining their difference from RGB PSNR. This does not verify any historical SSIM result or recover an inaccessible historical artifact.

On this clean validation set, global energy has lower mean RGB PSNR than guided, and full GFF has the highest mean PSNR among these four. Guided has lower mean RGB MAE than GFF. Full and zero-limit ablation CSVs contain 182 and 104 rows respectively, including duplicated guided controls for their separate runs.

## Reproducibility and scope

Algorithm snapshot: 49427a9a22bf5bbf1e0debf9ade040fa9e1081c7. The safety wrapper was subsequently published at 1aa96a81e6b53d20aa61518076be9799c6701f96; algorithms were not changed for this rerun. Run the published rebuild_phase2.py helper with a fresh external --output directory and an existing private --data-root containing the frozen validation images. It uses one compute thread and never selects held-outs. Source/configuration hashes and full command records remain in the private run's rebuild.json.

This package contains numerical outputs and protocol metadata only. Raw benchmark photos and derived panels remain private because source-photo redistribution rights have not been independently established. Private visual deliverables include fixed-first, largest-gain, and largest-regression panels with selection metadata, plus a fixed-first panel including full GFF. The panels illustrate this validation run. The next experiments investigate the observed failure cases; edge-device measurements and C++ energy candidates remain pending.
