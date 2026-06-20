$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $ScriptDir "sotm_simulator.py"
$Dist = Join-Path $ScriptDir "dist"
$Build = Join-Path $ScriptDir "build"
$TkHook = Join-Path $ScriptDir "tk_runtime_hook.py"

$ErrorActionPreference = "Continue"

$PythonCandidates = @(
    $env:PYTHON,
    (Join-Path $HOME ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    "python",
    "py"
) | Where-Object { $_ -and $_.Trim() -ne "" }

$PythonExe = $null
foreach ($Candidate in $PythonCandidates) {
    if ((Test-Path $Candidate) -or (Get-Command $Candidate -ErrorAction SilentlyContinue)) {
        & $Candidate -c "import sys; print(sys.executable)" *> $null
        if ($LASTEXITCODE -eq 0) {
            $PythonExe = $Candidate
            break
        }
    }
}

if (-not $PythonExe) {
    throw "Python bulunamadi. PYTHON ortam degiskeniyle python.exe yolunu verin."
}

& $PythonExe -c "import PyInstaller" *> $null
$HasPyInstaller = $LASTEXITCODE -eq 0
& $PythonExe -c "import cv2" *> $null
$HasOpenCv = $LASTEXITCODE -eq 0
$ErrorActionPreference = "Stop"

if (-not $HasPyInstaller) {
    & $PythonExe -m pip install pyinstaller
}

if (-not $HasOpenCv) {
    & $PythonExe -m pip install opencv-python
}

if (Test-Path $PythonExe) {
    $PythonPath = (Resolve-Path $PythonExe).Path
} else {
    $PythonPath = (& $PythonExe -c "import sys; print(sys.executable)").Trim()
}

$PythonRoot = Split-Path -Parent $PythonPath
$TclDir = Join-Path $PythonRoot "tcl"
$TclDataDir = Join-Path $TclDir "tcl8.6"
$TkDataDir = Join-Path $TclDir "tk8.6"
$DllDir = Join-Path $PythonRoot "DLLs"
$TkinterPkgDir = Join-Path $PythonRoot "Lib\tkinter"

& $PythonExe -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name SoTM_Simulator `
    --distpath $Dist `
    --workpath $Build `
    --specpath $ScriptDir `
    --runtime-hook $TkHook `
    --hidden-import tkinter `
    --hidden-import _tkinter `
    --hidden-import cv2 `
    --add-data "${TkinterPkgDir};tkinter" `
    --add-data "${TclDataDir};_tcl_data" `
    --add-data "${TkDataDir};_tk_data" `
    --add-binary "$(Join-Path $DllDir '_tkinter.pyd');." `
    --add-binary "$(Join-Path $DllDir 'tcl86t.dll');." `
    --add-binary "$(Join-Path $DllDir 'tk86t.dll');." `
    $App

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller exe uretimi basarisiz oldu."
}

"EXE olustu: $(Join-Path $Dist 'SoTM_Simulator.exe')"
