#!/bin/bash

set -euo pipefail

echo ""
echo "============================================"
echo "  Moodle Student Analyzer - Building app"
echo "============================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11+ was not found in PATH."
    exit 1
fi

echo "[1/3] Installing dependencies..."
python3 -m pip install -r requirements.txt

echo "[2/3] Cleaning previous artifacts..."
rm -rf dist build MoodleAnalyzer.spec

echo "[3/3] Building standalone executable..."
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name MoodleAnalyzer \
    --hidden-import sklearn.ensemble._gb \
    --hidden-import sklearn.ensemble._forest \
    --hidden-import sklearn.linear_model._ridge \
    --hidden-import sklearn.utils._cython_blas \
    --hidden-import sklearn.neighbors.typedefs \
    --hidden-import sklearn.neighbors._partition_nodes \
    --hidden-import sklearn.tree._utils \
    --hidden-import matplotlib.backends.backend_tkagg \
    --hidden-import matplotlib.backends._backend_tk \
    --collect-submodules sklearn \
    --collect-submodules matplotlib \
    --collect-submodules customtkinter \
    main.py

echo ""
echo "============================================"
echo "  Build complete: dist/MoodleAnalyzer"
echo "============================================"
echo "  This binary can be distributed without"
echo "  Python or manual dependency installation."
