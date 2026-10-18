# C++17 crossfit estimator reconstruction (2026-10-18)

This is a **new reconstruction**, not a byte-for-byte recovery of the lost C++
implementation. The recovered research ZIP did not contain the original C++
source or its parity/benchmark output. Historical 28-case parity, 10-case native
validation and old timings are not claimed as rerun results. New results live in
`results/` and identify their exact source hashes and environment.

## Scope

The C++ code implements only Python `estimate_crossfit(a, b)`: the shared valid
support, disjoint 2×2 high-pass samples, stable per-source/per-fold block
selection, MAD variance estimates, two-fold averaging, and diagnostic metadata.
It does not implement the full fusion pipeline. No ARM hardware benchmark or
embedded real-time claim is made.

Input is two matching row-major float64 RGB images in `[0,1]`, each at least
12×12. Every value must be finite. There is no implicit clipping, normalization,
color conversion, exposure correction, registration, or capture-domain mask
recovery. Returned sigmas are luminance noise estimates. The estimator retains
the Python model's limitations: texture, correlated noise, clipping, and weak
support can bias estimates; it does not report calibrated uncertainty.

## Reproduce

Requirements: a C++17 compiler (tested with GCC 14.2), Python 3, NumPy, SciPy.
The C++ implementation has no third-party library dependencies. The preserved
Python reference is imported directly for parity tests.

```sh
bash build_and_test.sh results_rerun
```

Choose a new result directory to preserve the supplied measured outputs. This
compiles with warnings as errors and floating-point contraction disabled, runs
native and Python parity tests, builds/runs AddressSanitizer + UndefinedBehavior-
Sanitizer native tests (leak detection disabled; see limitation below), benchmarks three resolutions,
and saves environment/source hashes and a summary. Any failed command stops the
script with a nonzero status. `CXX=clang++` can select another compiler if its
sanitizers are installed; that configuration was not used for the saved run.

The build uses `-O3 -DNDEBUG -ffp-contract=off`, no `-ffast-math`, no OpenMP, and
no architecture-specific `-march=native`. `build/` is generated and excluded from
the recovery package. Build products need not be trusted or transported.

## Files

- `include/crossfit.hpp`: normalized RGB input and diagnostic result API
- `src/crossfit.cpp`: C++17 estimator
- `src/crossfit_cli.cpp`: bounded binary fixture reader and JSON output
- `tests/native_tests.cpp`: explicit input validation, fallback, invariance,
  immutable input and nonoverlapping-template checks
- `tests/parity.py`: deterministic comparison to original Python function;
  checks both sigmas, all four fold variances, selected count, eligibility,
  availability and valid fraction
- `bench/benchmark.cpp`: five warmups and 30 measured repetitions per resolution;
  records every sample, median, mean, min/max, nearest-rank p95 and standard deviation
- `reference/`: preserved Python source and exact provenance
- `results/`: fresh measured results, environment, and sanitizer stderr
- `MANIFEST.sha256`: checksum manifest for the distributable files

The fixture transport is little-endian: eight bytes `CFITF64\0`, uint64 height
and width, then contiguous A and B RGB float64 buffers. It rejects truncated or
trailing data and limits inputs to 20 million pixels. It is a test transport,
not a production image loader. The C++ API itself uses native doubles.

## Numerical details and audit limits

Valid pixels have every channel of both inputs strictly inside `(0,1)`. A 9×9
binary erosion uses invalid values outside the image. Candidate starts are
`range(2, H-9, 8)` and `range(2, W-9, 8)`, with an entirely valid 8×8 block.
The lowest `ceil(0.2*N)` blocks are selected by stable sort, preserving scan
order when scores tie. Fewer than two selected blocks returns zero sigmas with
`available=false`. The C++ implementation computes only needed high-pass
samples instead of materializing a full high-pass image.

Parity tolerances are `rtol=1e-12, atol=2e-14` for floating estimates and exact
comparison for support/count metadata. CPU/NumPy accumulation order can cause
roundoff differences, and near-tied rankings can amplify them. Passing the
included cases is not a formal proof over all floating-point inputs.

Benchmark time includes validation, temporary allocations, support construction,
grayscale conversion, sorting and estimation for both images. It excludes input
generation, image decoding, fusion, metrics, process launch and output writing.
The shared cloud CPU is unpinned; variation and raw timing samples are retained.
These measurements are not directly comparable to lost historical measurements
without matching implementation and hardware conditions.

The checksum manifest covers files, not its own contents. Regenerate after a
rerun if distributing newly produced outputs; compare to the delivered manifest
only when verifying the untouched recovery package.

## Sanitizer runtime limitation

The first combined sanitizer attempt requested leak detection and exited because
LeakSanitizer does not work under this runtime's ptrace supervision. Its original
stderr is retained in `results/leak_sanitizer_unavailable.txt`. The successful
address/undefined-behavior run disables only leak detection (`detect_leaks=0`).
No leak-check success is claimed. On an unsupervised host you can rerun the native
sanitized binary with `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`; the local
script keeps this optional check disabled so it is reproducible here.
