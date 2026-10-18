# Spatial support reliability under controlled focus coverage and clipping

## Experimental design

This experiment tests whether spatially distributed repeated support improves differential noise correction. The design was frozen before execution in [protocol_frozen.json](../results/spatial_support_20261018/protocol_frozen.json), SHA-256 `30712a16650bf13a3427b2a168d33cccb23c618dc154c4bceb13f2e57805af68`. The grid contains 144 conditions and eight methods, yielding 1,152 metric rows.

Two fixed 96×96 linear-RGB textures are used: stochastic texture and a composite with sine texture on the left and stochastic texture on the right. Complementary defocus masks assign 25%, 50%, or 75% of the image width to sharp source A. Defocus is Gaussian with spatial sigma 1.5. Brightness transforms are normal `x`, dark `0.01+0.12x`, and extreme-white `0.999−0.01x`. Noise pairs are (0,0), (0,5), (5,0), and (5,5), expressed as independent RGB Gaussian standard deviations divided by 255; seeds are 11 and 23. Samples are clipped to [0,1]. The brightness strata jointly change signal scale and clipping exposure, so results are compared within each stratum. Noise-free inputs repeat across the two seeds.

The experiment reads procedural generators only. Natural-image validation and the WHU/MFFW2 held-outs are not inputs. PSNR and MAE use all linear-RGB samples. Noise-contrast error uses the known pre-clipping variance difference; clipping changes the effective residual distribution. `oracle_preclip` supplies that known pre-clipping model. Timing is single-thread Python pipeline wall time on the shared cloud CPU, including estimation and fusion, excluding generation and quality metrics. Three warmups precede one timed call per condition/method.

## Fixed reliability rules and ablations

The common-flat estimator selects the lowest-gradient 20% of eligible 8×8 blocks, using the maximum of the two smoothed source-gradient energies. Eligibility uses the existing eroded unsaturated support. The differential estimate is the difference of the two pooled high-pass MAD variance estimates.

- **Shared:** use that differential estimate when at least two blocks are selected
- **Bootstrap:** apply the previous 64-replicate positive-part shrinkage
- **Count gate:** require at least eight selected blocks
- **Spatial gate:** divide the image into four quadrants and require at least two selected block centers in each quadrant

Both gates revert to zero differential mean correction when rejected, while retaining the original global-sigma variance model, sigmoid, median, and guided filtering. Two samples per spatial stratum provide a minimal repeated-support requirement; four quadrants give a fixed partition of the image domain. These are preset engineering criteria. The count gate separates the effect of total sample count from spatial distribution.

The remaining controls are guided, continuous shared-gray GFF, zero mean correction, and the known pre-clipping noise model. Every row records image area, valid area, eligible/selected counts, selected pixel area and fraction, and all four quadrant counts. At this image size, eight disjoint blocks cover 512 of 9,216 pixels, or 5.56%; the retained area fields make the size dependence explicit.

## Fusion quality and rejection

The table reports scene-condition mean linear-RGB PSNR in dB. Each clean/equal-noise row has 12 conditions; each asymmetric row has 24. Rejections are spatial-gate rejections.

| Brightness | Noise | Shared | Count gate | Spatial gate | No-mean | Guided | GFF | Rejected |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| normal | clean | 32.45606 | 32.45606 | 38.58184 | 41.11279 | 42.76280 | 40.85504 | 6/12 |
| normal | equal_noise | 29.98138 | 29.98138 | 32.74075 | 33.70279 | 33.52484 | 33.40630 | 6/12 |
| normal | asymmetric | 30.95987 | 30.95987 | 33.84009 | 35.39718 | 34.79820 | 34.50440 | 12/24 |
| dark | clean | 50.92577 | 50.92577 | 55.58114 | 58.10376 | 61.46282 | 59.27210 | 6/12 |
| dark | equal_noise | 36.54752 | 36.52447 | 36.52242 | 36.52242 | 34.85346 | 34.95259 | 12/12 |
| dark | asymmetric | 38.74840 | 37.83400 | 36.45435 | 36.30193 | 34.67441 | 34.64417 | 21/24 |
| extreme_white | clean | 68.34984 | 68.34984 | 68.61991 | 68.73510 | 83.02788 | 80.92697 | 6/12 |
| extreme_white | equal_noise | 39.17587 | 39.17587 | 39.17587 | 39.17587 | 38.37453 | 38.54056 | 12/12 |
| extreme_white | asymmetric | 38.18644 | 38.18644 | 38.18644 | 38.18644 | 36.79190 | 36.79190 | 24/24 |

Under normal brightness, spatial rejection improves shared PSNR by 6.12578 dB on clean inputs and 2.88022 dB on asymmetric noise. The count gate leaves both groups unchanged because all selected supports meet its count threshold. On the 36 clean conditions across the three brightness strata, spatial gating rejects 18 and decreases PSNR in none; count gating changes none. This comparison is against the shared estimator: guided remains stronger on the clean groups.

The dark asymmetric group exhibits the opposite tradeoff. Spatial gating rejects 21/24 conditions and reduces PSNR from 38.74840 to 36.45435 dB; MAE increases from 0.0089093 to 0.0119273. It loses to shared on 19 conditions and improves two. Count gating rejects 5/24 and yields 37.83400 dB. Both noise directions show the effect: spatial-minus-shared mean PSNR is −3.28988 dB for noise (0,5) and −1.29823 dB for (5,0). In normal brightness the corresponding changes are +2.46191 and +3.29853 dB.

The largest gate-induced loss is 5.80241 dB: mixed texture, 50% sharp A, dark brightness, noise (0,5), seed 11. Its 32 eligible blocks yield seven selected blocks occupying 4.86% of the image, with quadrant counts [0,1,0,6]. Valid pixel support is 57.50%. Both gates reject a correction that is useful in this condition. Small or concentrated selected support can therefore contain adequate stationary-noise evidence, particularly after clipping removes candidate blocks.

In the extreme-white noisy groups, all estimators based on selected blocks already lack support and revert to zero correction. The new gates leave these results unchanged. In the asymmetric group this yields 38.18644 dB, compared with 49.40375 dB for the known pre-clipping noise model. The missing support remains a material information loss.

## Noise-contrast signs, errors, and abstention

Wrong-sign counts below apply only to nonzero corrections in asymmetric-noise conditions. Zero corrections are reported separately; they are not counted as correct-sign estimates.

| Brightness | Method | Wrong / active | Zero correction | Mean absolute contrast error |
|---|---|---:|---:|---:|
| normal | shared_delta | 10/24 | 0/24 | 0.0058438707 |
| normal | bootstrap_shrink | 8/17 | 7/24 | 0.0054869715 |
| normal | count_gate | 10/24 | 0/24 | 0.0058438707 |
| normal | spatial_gate | 4/12 | 12/24 | 0.0024118491 |
| dark | shared_delta | 2/24 | 0/24 | 8.0013744e-05 |
| dark | bootstrap_shrink | 0/21 | 3/24 | 8.4661193e-05 |
| dark | count_gate | 2/19 | 5/24 | 9.8336029e-05 |
| dark | spatial_gate | 0/3 | 21/24 | 0.00016396098 |
| extreme_white | shared_delta | 0/0 | 24/24 | 0.00017184391 |
| extreme_white | bootstrap_shrink | 0/0 | 24/24 | 0.00017184391 |
| extreme_white | count_gate | 0/0 | 24/24 | 0.00017184391 |
| extreme_white | spatial_gate | 0/0 | 24/24 | 0.00017184391 |

Spatial gating reduces the normal-brightness wrong-sign count from 10 to 4 while halving active corrections from 24 to 12. Dark conditions fall from 2 wrong signs among 24 active corrections to 0 among only 3. The associated loss of useful correction explains the fusion-quality decrease. In extreme-white conditions, the zero wrong-sign count accompanies zero active estimates.

### Focus coverage remains a separate source of bias

On clean stochastic texture, the true noise contrast is zero. Changing sharp-A coverage from 25% to 50% to 75% changes the shared estimates to −0.00840945, −0.000509554, and +0.00596345. Each case has 20 selected blocks and at least two in every quadrant, so the spatial rule accepts all three. Their shared/spatial PSNR values are 29.22836, 40.38840, and 32.46698 dB. Broad geometric support alone does not remove defocus-dependent contamination of high-pass statistics.

For the mixed texture at 25% sharp-A coverage, all 20 selected blocks lie in the right-hand quadrants, with counts [0,8,0,12]. Spatial rejection improves clean PSNR from 28.86730 to 46.63248 dB. The smoothed-gradient ranking selects stochastic high-frequency content in this case: small guide gradients do not necessarily imply a noise-only high-pass residual. The contrasting stochastic and mixed cases separate geometric support from the statistical suitability of that support.

## Exchange symmetry, tests, and CPU cost

All 144 conditions also evaluate the spatial-gate pipeline after exchanging A and B. The estimated contrast changes sign and the maximum fused-RGB discrepancy is 4.2466e−15. Reverse-noise conditions are included in the main grid. The repository suite passes 43 tests, including five support-probe tests for spatial/count separation, estimator equivalence to the previous probe, absent-support fallback, and source exchange.

Median end-to-end pipeline times across the fixed grid are:

| Method | Median milliseconds |
|---|---:|
| guided | 1.683 |
| gff_continuous_shared_gray | 4.114 |
| no_mean | 7.198 |
| shared_delta | 8.731 |
| bootstrap_shrink | 14.086 |
| count_gate | 8.745 |
| spatial_gate | 8.713 |
| oracle_preclip | 6.544 |

Count and quadrant tests have approximately the same pipeline cost as the shared estimator; bootstrap is slower. The implementation uses fixed-size block scans, median-based residual statistics, and four integer occupancy counters. Those operations map directly to a C++/OpenCV implementation with a fixed four-element counter array and selection-based medians. The recorded timings are for the Python implementation at 96×96.

## Interpretation and next design question

Spatial coverage removes some large corrections caused by concentrated texture selection, but it rejects useful estimates when clipping leaves only a few informative blocks. Conversely, a well-distributed set of blocks can retain substantial focus-coverage bias. The two observed requirements are therefore distinct: representativeness over the image domain and compatibility of the residual statistics with the noise model.

A subsequent design should test residual suitability across focus coverage while retaining a separate record of spatial support. Geometric occupancy can remain a diagnostic, whereas deciding to apply correction needs evidence about residual contamination and the cost of abstention. The present thresholds and grid are unchanged after the results; the complete positive and negative outcomes are retained.

## Reproduction

```sh
python scripts/probe_spatial_support.py --output /private/new-spatial-support-run
python scripts/summarize_spatial_support.py   --metrics /private/new-spatial-support-run/metrics.csv   --output /private/new-spatial-support-analysis.json
PYTHONPATH=src python -m unittest discover -s tests -v
```

Both output paths must be new. The default frozen protocol is under `results/spatial_support_20261018/`. That directory also contains the 1,152-row metric CSV, 144-case source-swap record, stratified and paired summaries, focus-coverage examples, runtime record, tests, and pre-run source/protocol hashes. No image files are included.
