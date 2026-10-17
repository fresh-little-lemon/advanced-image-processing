# Portable CPU C++17 core

Requires CMake >= 3.16, a C++17 compiler, and OpenCV 4 development libraries
(`core`, `imgproc`, `imgcodecs`). No architecture-specific intrinsics or GPU are
required. The same source is intended for x86-64 and ARM64.

```sh
cmake -S cpp -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp --parallel 2
ctest --test-dir build/cpp --output-on-failure
build/cpp/multifocus_cli a.png b.png fused.png guided
PYTHONPATH=src python cpp/tests/parity.py --probe build/cpp/fusion_probe
# Or configure/build then compare in one step:
PYTHONPATH=src python cpp/tests/parity.py --build
```

`multifocus::fuse(a, b, method)` accepts equally sized, nonempty `CV_64FC3`
RGB images containing finite values in [0,1]. The result owns its storage.
Methods are `average`, `laplacian`, `sml`, and `guided`. Luminance uses
0.299 R + 0.587 G + 0.114 B on the supplied gamma-encoded values. There is no
linear-light conversion, alignment, registration, deghosting, or color management.

- Laplacian: absolute 4-neighbor Laplacian, 7x7 normalized box focus score
- SML: summed absolute horizontal/vertical [1,-2,1], 7x7 normalized box score
- Hard focus comparison: greater-or-equal chooses A
- Guided: Laplacian hard mask, 7x7 binary median, grayscale averaged-source
  guide, radius 5 guided filter, epsilon 0.001, clipped weights
- Every filter uses half-sample symmetric reflection (`BORDER_REFLECT`), matching
  SciPy ndimage `mode="reflect"`; the median explicitly reflects its neighborhood

The CLI reads only 8-bit three-channel images, interprets samples as RGB values
without gamma decoding, and writes an 8-bit PNG (lossy quantization, lossless
encoding). EXIF orientation, ICC transforms, alpha, grayscale, and 16-bit input
are not handled by this minimal CLI. Use the float64 API for exact numeric input.

`fusion_probe` is a test utility that reads `height width` followed by all A RGB
samples then all B RGB samples in row-major order from stdin; it writes fused
samples as decimal FP64 text. The parity script therefore avoids PNG rounding.
Different floating-point summation orders can change hard decisions for nearly
equal focus scores; the tested fixtures do not establish universal bitwise parity.

## Verification status

The included CI workflow targets native `ubuntu-24.04` and
`ubuntu-24.04-arm`, with C++ invariants and Python parity checks. These runner
labels are documented by [GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
A workflow definition is not evidence of a passing ARM64 run. Record actual
compiler, OpenCV version, architecture, and CI result when those runs complete.

### Recorded local verification (2026-10-17)

Native x86-64 Debian 13, g++ 14.2.0, OpenCV 4.10.0:

- All three executables compiled with `-std=c++17 -O2 -Wall -Wextra -Wpedantic`
- C++ invariants passed
- All 60 float64 Python parity cases passed at `rtol=atol=1e-10`
- PNG CLI smoke test passed: constant 40 and 200 produce 120
- ARM64 execution and the CMake configure/build path have not been run locally

The container had OpenCV runtime libraries but lacked development headers,
CMake, and system package installation privileges. Official Debian development
packages (`libopencv-core-dev`, `libopencv-imgproc-dev`, and
`libopencv-imgcodecs-dev`, version `4.10.0+dfsg-5`) were downloaded from
https://deb.debian.org/debian/pool/main/o/opencv/ and extracted under `/tmp`.
No system installation was performed. The direct compilation equivalent was:

```sh
# HEADERS points to the extracted usr/include/opencv4 directory.
# Source can be tests/test_fusion.cpp, tests/probe.cpp, or src/main.cpp.
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic \
  -Icpp/include -I"$HEADERS" cpp/src/fusion.cpp cpp/tests/test_fusion.cpp \
  /usr/lib/x86_64-linux-gnu/libopencv_core.so.410 \
  /usr/lib/x86_64-linux-gnu/libopencv_imgproc.so.410 \
  /usr/lib/x86_64-linux-gnu/libopencv_imgcodecs.so.410 \
  -o build/cpp/test_fusion
```

### CPU benchmark

`fusion_benchmark` times only the float64 fusion call (validation and allocations
included). It sets OpenCV to one thread and performs three warmups plus ten timed
iterations. Linux builds also report process peak RSS. The Python driver times
fresh CLI processes separately, including startup, input decoding, conversion,
and PNG encoding/writing, and records actual per-process peak RSS via `wait4`.

```sh
python cpp/tests/benchmark.py a.jpg b.jpg results/cpp_verification.json
```

The recorded 520x520 Lytro-01 run and measurement limitations are in
`results/cpp_verification.json`. CPU timing is environment-specific, and process
RSS includes runtime libraries and image buffers; neither establishes target ARM
performance. The CLI uses one OpenCV thread; the library API preserves its
caller's OpenCV threading configuration.
