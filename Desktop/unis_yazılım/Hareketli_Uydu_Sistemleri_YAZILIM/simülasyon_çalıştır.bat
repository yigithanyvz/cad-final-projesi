@echo off
setlocal
cd /d "%~dp0"

if exist "C:\msys64\ucrt64\bin\g++.exe" set "PATH=C:\msys64\ucrt64\bin;%PATH%"
if exist "C:\msys64\mingw64\bin\g++.exe" set "PATH=C:\msys64\mingw64\bin;%PATH%"

where g++ >nul 2>nul
if errorlevel 1 (
    echo [HATA] g++ bulunamadi.
    echo Bu C++ simulasyonlarini calistirmak icin MinGW-w64 veya MSYS2 g++ kurman gerekiyor.
    echo Kurulumdan sonra terminali yeniden acip bu dosyayi tekrar calistir.
    if /i not "%MERGEN_NO_PAUSE%"=="1" pause
    exit /b 1
)

if not exist "Efe\bin" mkdir "Efe\bin"

echo [1/4] Azimuth/Elevasyon C++ simulasyonu derleniyor...
g++ -std=c++17 -O2 "Efe\azimuth_elevation_simulation\src\main.cpp" -o "Efe\bin\azimuth_elevation_simulation.exe"
if errorlevel 1 goto :build_failed

echo [2/4] Mama kabi C++ simulasyonu derleniyor...
g++ -std=c++17 -O2 "Efe\mama_kabi_stabilization_simulation\src\main.cpp" -o "Efe\bin\mama_kabi_stabilization_simulation.exe"
if errorlevel 1 goto :build_failed

set TARGET_AZ=%1
set TARGET_EL=%2
if "%TARGET_AZ%"=="" set TARGET_AZ=120
if "%TARGET_EL%"=="" set TARGET_EL=30

echo [3/4] Azimuth/Elevasyon simulasyonu calistiriliyor...
"Efe\bin\azimuth_elevation_simulation.exe" %TARGET_AZ% %TARGET_EL%
if errorlevel 1 goto :run_failed

echo [4/4] Mama kabi stabilizasyon simulasyonu calistiriliyor...
"Efe\bin\mama_kabi_stabilization_simulation.exe"
if errorlevel 1 goto :run_failed

echo.
echo Simulasyonlar tamamlandi.
echo Azimuth/Elevasyon sonuc klasoru: Efe\azimuth_elevation_simulation\results
echo Mama kabi sonuc klasoru: Efe\mama_kabi_stabilization_simulation\results
if /i not "%MERGEN_NO_PAUSE%"=="1" pause
exit /b 0

:build_failed
echo [HATA] C++ derleme basarisiz oldu.
if /i not "%MERGEN_NO_PAUSE%"=="1" pause
exit /b 1

:run_failed
echo [HATA] Simulasyon calisirken hata olustu.
if /i not "%MERGEN_NO_PAUSE%"=="1" pause
exit /b 1
