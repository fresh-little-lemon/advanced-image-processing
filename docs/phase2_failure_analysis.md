# Differential noise-estimation bias in multifocus fusion

## 1. Experimental setting

This study examines the frozen 26-scene MFI-WHU validation set. Each scene contains two defocused sources and a provided clear reference. All processing and evaluation use decoded linear RGB; PSNR is computed from full-image three-channel MSE with range 1, and MAE is averaged over the same samples. The 94 WHU and 13 MFFW2 held-out scenes remain unevaluated.

Two input conditions are evaluated: the original source pair, and a fixed asymmetric corruption adding independent RGB Gaussian noise to B with standard deviation 5/255 while leaving A unchanged. The corruption uses one seed and clips samples to [0,1]. Original sensor, JPEG, and resampling noise is unknown. Accordingly, `oracle_added_only` supplies the known injected variance while assuming zero baseline residual noise; the separate procedural experiments provide a fully specified additive-noise oracle.

The clear reference is used for evaluation and diagnostic region labels. Local source preference is determined by 7×7 RGB MSE to the reference, retaining locations with an error difference greater than 1e-6 and valid unsaturated filter support. These labels describe reference preference rather than physical focus boundaries. Reference gradient-energy quintiles define texture regions for diagnosis. Neither reference information nor diagnostic labels enter the candidate estimators. Correlations and regional proportions are summarized across scenes; proportions are scene-wise means.

## 2. Differential mean subtraction shifts the focus threshold

Let

S = box(Laplacian(A)² − Laplacian(B)², 7),

and let δ = σ_A² − σ_B² denote the estimated noise-variance contrast. The implemented mean-corrected focus score is exactly

S_corrected = S − 20δ.

This identity was verified numerically in every validation scene. A source-wide estimation difference therefore produces a spatially constant threshold shift, including in regions whose texture contributed little to the noise estimate.

The controlled `global_no_mean` ablation removes this subtraction while preserving the global variance model, sigmoid, median filter, and guided filter. It improves 25/26 scenes and all 16 scenes where `global_full` loses to guided, recovering 0.59674 dB on average. Nine of those 16 scenes still remain below guided. In contrast, removing variance normalization alone changes mean PSNR from 37.23697 to 37.24196 dB. These interventions locate most of the original deficit in differential mean correction, with a residual contribution from the remaining focus-score and reconstruction choices.

The magnitude of the correction is strongly associated with its effect: Spearman ρ is −0.92547 for global-minus-no-mean PSNR and −0.88718 for global-minus-guided PSNR. This descriptive relationship agrees with the controlled ablation.

### Preference reversals and texture contamination

Across the 16 losing scenes, subtraction reverses the hard energy preference at 23.0046% of eligible pixels. Reversals away from the reference-preferred source account for 22.7976% of eligible pixels, compared with 0.2070% toward that source. These measurements precede sigmoid, median, and guided filtering.

WHU-085 has the largest global-versus-guided deficit, −3.53595 dB. Its source-wide estimates are σ_A=0.003668 and σ_B=0.047169, while B contains most of the sharper reference content. The clear reference receives an estimate of 0.052561. Flat-patch estimates are much smaller: 0.000242 for A and 0.001654 for B. Across all scenes, source sigma difference correlates with A-preferred area at ρ=0.55350, and the clear reference has a larger estimated sigma than both sources in 25/26 scenes. Together, these observations support a focus-coverage mechanism: source-wide high-pass statistics respond to the amount of sharp content, and the resulting correction penalizes the source carrying that content.

### Spatial distribution of the error

Relative to no-mean, subtraction increases scene-mean MSE by 4.6153e-5 in the lowest gradient-energy quintile, with increases in 25/26 scenes. The highest quintile increases by 1.7001e-5, with increases in 26/26 scenes. The larger low-texture effect is consistent with small local focus gaps being overturned by a global threshold shift.

On valid unsaturated supports, the increase remains 3.1226e-5 in 25/26 scenes. Global-minus-guided PSNR has weak correlations with saturated fraction (ρ=0.17197) and median B/A luminance ratio (ρ=0.05729). The ratio is a descriptive exposure proxy. Within this original-input condition, differential estimation bias explains the deficit more directly than saturation or exposure variation.

## 3. Noise-oracle comparison separates two mechanisms

On the existing procedural grid, asymmetric-noise mean PSNR is 34.76839 dB for global estimation, 34.69382 dB for the known-noise oracle, and 31.26979 dB for guided. Stochastic textures exhibit substantial sigma-estimation bias even where global PSNR exceeds oracle PSNR. Noise estimation, focus selection, smoothing, and reconstruction therefore need separate diagnostics: the final PSNR can improve through compensating effects.

The clean sine case isolates a different mechanism. Oracle and global both achieve 49.99172 dB, compared with guided at 59.18226 dB, despite known zero added noise. The fixed variance floor causes weak nonzero energy differences to produce mixed weights. The previously implemented exact-zero-variance limit resolves this procedural case. The original-image ablation above instead identifies differential mean subtraction as the dominant aggregate failure.

## 4. Shared-support estimation and uncertainty shrinkage

Two changes were specified before running the candidate experiment.

**Shared-support noise contrast.** Both sources use the same 8×8 blocks, selected from the lowest 20% of the maximum A/B smoothed gradient energy within valid support. Pooled high-pass MAD estimates yield δ̂=σ̂_A²−σ̂_B². Replacing only the mean correction by 20δ̂ retains the original global-sigma variance normalization and all subsequent filtering. This isolates the effect of selecting a common spatial support.

**Bootstrap shrinkage.** Sixty-four block-bootstrap replicates on the selected support estimate v̂, the variability of δ̂. The contrast is multiplied by

α = max(0, 1 − v̂/δ̂²),

with α=0 when δ̂=0. This positive-part rule reduces correction when the estimated contrast is small relative to its resampling variability. The bootstrap conditions on the selected blocks; the WHU-098 analysis below examines the consequences of that conditioning.

The experiment uses fixed support settings and seeds without a parameter sweep. It produces 390 metric rows: 26 original scenes × 7 methods and 26 corrupted scenes × 8 methods. Four focused tests pass: source-swap symmetry, absent-support handling, constant input, and equivalence of zero differential correction to `global_no_mean`. The last identity was also checked for all 52 input conditions.

## 5. Quantitative results

All PSNR values below are mean full-image linear-RGB PSNR in dB.

| Method | Original PSNR | Added-noise PSNR | Original MAE | Added-noise MAE |
|---|---:|---:|---:|---:|
| guided | 37.76874 | 33.26152 | 0.00225442 | 0.01421267 |
| gff | 38.69456 | 33.71069 | 0.00293465 | 0.01436614 |
| global_full | 37.23697 | 34.43164 | 0.00393497 | 0.01088594 |
| global_no_mean | 37.83371 | 34.03515 | 0.00300691 | 0.01287607 |
| flat_full | 37.81229 | 34.60089 | 0.00248690 | 0.01095022 |
| shared_delta | 37.77746 | 34.65557 | 0.00310669 | 0.01105475 |
| shared_delta_shrink | 37.77843 | 34.65265 | 0.00310517 | 0.01105973 |
| oracle_added_only | — | 34.65626 | — | 0.01080058 |

On original inputs, shared support recovers 0.54049 dB relative to global estimation. It is 0.00872 dB above guided, 0.03483 dB below flat, and 0.91710 dB below full GFF. Its MAE remains higher than guided, flat, GFF, and no-mean. Thus replacing the differential correction removes much of the global estimator's PSNR deficit, while the retained normalization and reconstruction still produce a less favorable absolute-error profile.

Under the fixed added-noise condition, shared support is 0.22393 dB above global, 0.05467 dB above flat, and 1.39405 dB above guided. Its MAE is higher than global and flat. Mean correction itself remains useful in this condition: global exceeds no-mean by 0.39649 dB. The contrasting original and corrupted results motivate adapting the reliability of the correction rather than disabling it uniformly.

Bootstrap shrinkage changes PSNR by +0.00096 dB on originals and −0.00292 dB on corrupted inputs. Its additional computation has little effect on the aggregate result.

### WHU-098: support collapse and an overconfident correction

WHU-098 is the sole corrupted scene where shared support loses to guided, by 1.36072 dB; it also loses 1.21443 dB to global. Before corruption, 83.32% of pixels have valid support and 3,023 blocks are eligible. Noise and clipping reduce these to 1.66% valid support and 10 eligible blocks. The lowest-20% selection consequently uses only 2 blocks.

The estimated variance contrast is +0.00199148, whereas the newly injected B-noise contributes a known negative contrast of −0.000171844. The bootstrap shrink coefficient remains 0.98768. The two surviving blocks yield a stable estimate within their restricted support, but they fail to represent the image-wide noise contrast. This is a selection and spatial-coverage failure that within-support resampling does not capture.

The same distinction appears in an aggregate noise-estimation diagnostic. Comparing each estimated noisy-minus-original contrast increment with the known injected increment, the mean absolute error is 1.15525e-4 for shared support and 7.90752e-5 for global estimation. Clipping and changing support contribute to this error. Shared support's higher PSNR therefore coexists with less accurate estimation of the injected contrast increment, reinforcing the need to evaluate estimation and fusion separately.

## 6. Next experimental design

### Focus-coverage invariance and estimator separation

Construct deterministic defocus pairs with varying sharp-area fractions, and add known noise in both source directions. Measure whether the estimated differential variance remains stable as focus coverage changes. Cross the mean-correction estimator and variance-normalization estimator in a factorial ablation. The current candidate changes only the mean term; this next comparison will distinguish residual mean-estimation error from mixing caused by the global variance model.

### Spatial validity and selective correction

Evaluate estimates on independent spatial strata and measure sign-error rates and confidence coverage under clipping. Include a prespecified abstention alternative that uses zero differential correction or a fixed baseline when spatial support is insufficient. Establish the support-acceptance criterion on controlled development simulations and freeze it before subsequent evaluation. WHU-098 supplies the immediate diagnostic target: a useful validity measure should distinguish two consistent surviving blocks from broad, representative support.

The results identify two linked requirements for the next estimator: invariance to the amount of sharp content, and sensitivity to loss of representative spatial support. These requirements follow directly from the original-input threshold-shift analysis and the corrupted-input WHU-098 failure.

## 7. Reproducibility files

- [`per_scene_diagnostics.csv`](../results/phase2_failure_analysis_20261018/per_scene_diagnostics.csv): 26-scene noise estimates, threshold shifts, reference-preference reversals, and regional errors
- [`summary.json`](../results/phase2_failure_analysis_20261018/summary.json): diagnostic aggregates and descriptive correlations
- [`procedural_oracle_by_texture.csv`](../results/phase2_failure_analysis_20261018/procedural_oracle_by_texture.csv): existing controlled procedural oracle comparison
- [`protocol.json`](../results/shared_support_probe_20261018/protocol.json): fixed experimental settings and source hash
- [`metrics.csv`](../results/shared_support_probe_20261018/metrics.csv): 390 RGB-domain metric rows
- [`estimator_diagnostics.csv`](../results/shared_support_probe_20261018/estimator_diagnostics.csv): estimated contrasts, support sizes, and shrink coefficients
- [`WHU098_support_counterexample.json`](../results/shared_support_probe_20261018/WHU098_support_counterexample.json): measured support collapse

The package contains numerical results, protocol metadata, scripts, and tests. Source and derived benchmark images remain in private research storage.
