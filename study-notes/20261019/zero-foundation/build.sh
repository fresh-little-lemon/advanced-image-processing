#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
for pass in 1 2 3; do
 xelatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=build main.tex
done
