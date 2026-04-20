#!/usr/bin/env bash
# Use ./packaging/build_nvidia.sh (CUDA venv) or ./packaging/build_cpu.sh (CPU venv). See README.
echo "Run one of:" >&2
echo "  ./packaging/build_nvidia.sh   # venv: requirements-cuda.txt + packaging/requirements-build-cuda.txt" >&2
echo "  ./packaging/build_cpu.sh      # venv: requirements-cpu.txt + packaging/requirements-build-cpu.txt" >&2
exit 1
