#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CXX="${CXX:-g++}"
OUT="${1:-results}"
mkdir -p build "$OUT"
COMMON=(-std=c++17 -Wall -Wextra -Wpedantic -Werror -ffp-contract=off -Iinclude)
RELEASE=(-O3 -DNDEBUG)
"$CXX" "${COMMON[@]}" "${RELEASE[@]}" src/crossfit.cpp src/crossfit_cli.cpp -o build/crossfit_cli
"$CXX" "${COMMON[@]}" "${RELEASE[@]}" src/crossfit.cpp tests/native_tests.cpp -o build/native_tests
"$CXX" "${COMMON[@]}" "${RELEASE[@]}" src/crossfit.cpp bench/benchmark.cpp -o build/benchmark
./build/native_tests > "$OUT/native_tests.json"
python3 tests/cli_validation.py --executable build/crossfit_cli --output "$OUT/cli_validation.json"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tests/parity.py --executable build/crossfit_cli --output "$OUT/python_parity.json" | tee "$OUT/parity_summary.txt"
"$CXX" "${COMMON[@]}" -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined src/crossfit.cpp tests/native_tests.cpp -o build/native_tests_sanitized
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 ./build/native_tests_sanitized > "$OUT/native_sanitized.json" 2> "$OUT/sanitizer_stderr.txt"
./build/benchmark > "$OUT/benchmark.json"
CXX="$CXX" OUT="$OUT" python3 tests/record_environment.py
python3 - "$OUT" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);parity=json.loads((p/'python_parity.json').read_text());native=json.loads((p/'native_tests.json').read_text());cli=json.loads((p/'cli_validation.json').read_text());san=json.loads((p/'native_sanitized.json').read_text());bench=json.loads((p/'benchmark.json').read_text())
s={'status':'passed','scope':'reconstructed C++17 crossfit noise estimator only','python_parity_cases':parity['passed_cases'],'python_parity_total':parity['total_cases'],'max_sigma_abs_error':parity['max_sigma_abs_error'],'max_fold_variance_abs_error':parity['max_fold_variance_abs_error'],'native_passed':native['total']-native['failed'],'native_total':native['total'],'cli_validation_passed':cli['total']-cli['failed'],'cli_validation_total':cli['total'],'asan_ubsan_passed':san['failed']==0,'leak_detection':'not run in successful sanitizer pass; runtime ptrace incompatibility, see leak_sanitizer_unavailable.txt','benchmark_median_ms':{f"{x['width']}x{x['height']}":x['median_ms'] for x in bench['cases']},'full_fusion_cpp_validated':False,'arm_hardware_tested':False}
(p/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
PY
