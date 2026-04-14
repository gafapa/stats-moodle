@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "EXE_PATH=dist\MoodleAnalyzer.exe"
set "WEBSITE_DIR=website"
set "DEPLOY_DIR=deploy\webserver"
set "DOWNLOADS_DIR=%DEPLOY_DIR%\downloads"

echo.
echo ============================================
echo   Preparing website release bundle
echo ============================================
echo.

if not exist "%WEBSITE_DIR%\index.html" (
    echo ERROR: Website sources were not found in "%WEBSITE_DIR%".
    exit /b 1
)

if not exist "%EXE_PATH%" (
    if exist "build.bat" (
        echo The executable was not found. Running build.bat first...
        call build.bat
        if errorlevel 1 (
            echo ERROR: build.bat failed.
            exit /b 1
        )
    ) else (
        echo ERROR: "%EXE_PATH%" was not found and build.bat is missing.
        exit /b 1
    )
)

echo Cleaning previous deploy folder...
if exist "%DEPLOY_DIR%" rmdir /s /q "%DEPLOY_DIR%"

echo Creating deploy structure...
mkdir "%DEPLOY_DIR%"
mkdir "%DOWNLOADS_DIR%"

echo Copying website assets...
copy /y "%WEBSITE_DIR%\index.html" "%DEPLOY_DIR%\index.html" >nul
copy /y "%WEBSITE_DIR%\styles.css" "%DEPLOY_DIR%\styles.css" >nul
copy /y "%WEBSITE_DIR%\app.js" "%DEPLOY_DIR%\app.js" >nul

echo Copying standalone executable...
copy /y "%EXE_PATH%" "%DOWNLOADS_DIR%\MoodleAnalyzer.exe" >nul

echo.
echo ============================================
echo   Release bundle ready
echo ============================================
echo   Upload the contents of:
echo   %CD%\%DEPLOY_DIR%
echo   to your web server root.
echo.
exit /b 0
