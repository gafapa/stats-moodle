@echo off
setlocal

echo.
echo ============================================
echo   Moodle Student Analyzer - Building EXE
echo ============================================
echo.

python --version >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.11+ was not found in PATH.
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    exit /b 1
)

echo [2/3] Cleaning previous artifacts...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist MoodleAnalyzer.spec del /q MoodleAnalyzer.spec

echo [3/3] Building standalone executable...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name MoodleAnalyzer ^
    --icon NONE ^
    --hidden-import sklearn.ensemble._gb ^
    --hidden-import sklearn.ensemble._forest ^
    --hidden-import sklearn.linear_model._ridge ^
    --hidden-import sklearn.utils._cython_blas ^
    --hidden-import sklearn.neighbors.typedefs ^
    --hidden-import sklearn.neighbors._partition_nodes ^
    --hidden-import sklearn.tree._utils ^
    --hidden-import matplotlib.backends.backend_tkagg ^
    --hidden-import matplotlib.backends._backend_tk ^
    --collect-submodules sklearn ^
    --collect-submodules matplotlib ^
    --collect-submodules customtkinter ^
    main.py

if errorlevel 1 (
    echo ERROR: Executable build failed.
    exit /b 1
)

echo.
echo ============================================
echo   Build complete: dist\MoodleAnalyzer.exe
echo ============================================
echo   This EXE can be distributed without Python
echo   or manual dependency installation.
echo.
exit /b 0
