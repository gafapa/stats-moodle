#!/bin/bash

set -euo pipefail

echo ""
echo "============================================"
echo "  Moodle Student Analyzer - Build Mac M"
echo "============================================"
echo ""

# Verificar que estamos en Mac
if [[ "$(uname)" != "Darwin" ]]; then
    echo "ERROR: Este script debe ejecutarse en macOS."
    exit 1
fi

# Verificar arquitectura arm64
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    echo "ADVERTENCIA: Se detectó arquitectura '$ARCH'. Este script está optimizado para Apple Silicon (arm64)."
    echo "Continuando de todas formas..."
fi

# Verificar Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: Python 3.11+ no encontrado en PATH."
    echo "Instálalo con: brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Usando: $PYTHON_VERSION"
echo "Arquitectura: $(uname -m)"
echo ""

echo "[1/4] Instalando dependencias..."
python3 -m pip install -r requirements.txt --quiet

echo "[2/4] Verificando PyInstaller..."
python3 -m pip install "pyinstaller>=6.0.0" --quiet

echo "[3/4] Limpiando artefactos previos..."
rm -rf dist/MoodleAnalyzer dist/MoodleAnalyzer.app build/__pycache__ 2>/dev/null || true

echo "[4/4] Compilando ejecutable para Apple Silicon (arm64)..."
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name MoodleAnalyzer \
    --target-arch arm64 \
    --hidden-import sklearn.ensemble._gb \
    --hidden-import sklearn.ensemble._forest \
    --hidden-import sklearn.linear_model._ridge \
    --hidden-import sklearn.utils._cython_blas \
    --hidden-import sklearn.neighbors.typedefs \
    --hidden-import sklearn.neighbors._partition_nodes \
    --hidden-import sklearn.tree._utils \
    --hidden-import matplotlib.backends.backend_tkagg \
    --hidden-import matplotlib.backends._backend_tk \
    --hidden-import matplotlib.backends.backend_macosx \
    --collect-submodules sklearn \
    --collect-submodules matplotlib \
    --collect-submodules customtkinter \
    main.py

echo ""
echo "============================================"
echo "  Build completado: dist/MoodleAnalyzer"
echo "============================================"
echo ""

# Verificar que el binario es arm64
if [[ -f "dist/MoodleAnalyzer" ]]; then
    echo "Verificando arquitectura del binario:"
    file dist/MoodleAnalyzer
    lipo -info dist/MoodleAnalyzer 2>/dev/null || true
fi

echo ""
echo "  Para ejecutar:  open dist/MoodleAnalyzer"
echo "  o bien:         ./dist/MoodleAnalyzer"
echo ""
echo "  NOTA: Si macOS bloquea la app (Gatekeeper):"
echo "    xattr -cr dist/MoodleAnalyzer"
echo ""
