#!/bin/bash
# Build rf.wasm: rapidfuzz-cpp's ratio and partial_ratio scorers for the browser (the
# same C++ the Python rapidfuzz package uses, so scores are identical).
#   needs: pip install ziglang==0.13.0 ; rapidfuzz 3.14.1's source (its sdist has
#   extern/rapidfuzz-cpp):  pip download rapidfuzz==3.14.1 --no-binary :all: --no-deps
#                           tar xzf rapidfuzz-3.14.1.tar.gz
#   usage: bash build_rf.sh PATH/TO/rapidfuzz-3.14.1      (writes ../files/rf.wasm)
set -e
cd "$(dirname "$0")"
RF="${1:-rapidfuzz-3.14.1}"
Z="python3 -m ziglang"
mkdir -p build
$Z c++ -target wasm32-wasi -O3 -std=c++17 -fno-exceptions -fno-rtti -I "$RF/extern/rapidfuzz-cpp" -c rfwasm.cpp -o build/rfwasm.o
$Z c++ -target wasm32-wasi -O3 -std=c++17 -fno-exceptions -fno-rtti -c newdel.cpp -o build/newdel.o
$Z cc -target wasm32-wasi -O3 -s -mexec-model=reactor build/rfwasm.o build/newdel.o -o ../files/rf.wasm
ls -la ../files/rf.wasm
