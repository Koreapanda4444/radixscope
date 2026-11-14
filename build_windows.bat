@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1
python -c "import struct, sys; raise SystemExit(0 if sys.version_info >= (3, 11) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer, 64-bit, must be available as python.
  popd
  exit /b 1
)
python -m pip install ".[desktop-build]"
if errorlevel 1 goto failed
python packaging\windows_resources.py
if errorlevel 1 goto failed
python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name RadixScope --paths "%CD%\src" --contents-directory _internal --distpath dist --workpath build\windows\pyinstaller --specpath build\windows --icon "%CD%\build\windows\radixscope.ico" --version-file "%CD%\build\windows\version.txt" --add-data "%CD%\src\radixscope\assets;radixscope/assets" --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets "%CD%\packaging\desktop_entry.py"
if errorlevel 1 goto failed
python packaging\windows_resources.py --licenses
if errorlevel 1 goto failed
echo Built dist\RadixScope\RadixScope.exe. Keep the entire program folder together.
popd
exit /b 0
:failed
echo Windows build failed.
popd
exit /b 1
