import importlib.metadata
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from radixscope import __version__


def make_icon(source: Path, destination: Path) -> None:
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise ValueError("invalid application icon")
    images: list[tuple[int, bytes]] = []
    for size in (16, 32, 48, 256):
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        temporary = destination.with_name(f"{destination.stem}-{size}.png")
        try:
            if not image.save(str(temporary)):
                raise OSError("could not render application icon")
            images.append((size, temporary.read_bytes()))
        finally:
            temporary.unlink(missing_ok=True)
    offset = 6 + 16 * len(images)
    entries: list[bytes] = []
    for size, data in images:
        dimension = size if size < 256 else 0
        entries.append(struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset
        ))
        offset += len(data)
    destination.write_bytes(
        struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries)
        + b"".join(data for _, data in images)
    )


def version_resource() -> str:
    numbers = (*(int(part) for part in __version__.split(".")), 0)
    return (
        "VSVersionInfo(ffi=FixedFileInfo("
        f"filevers={numbers!r}, prodvers={numbers!r}, mask=0x3f, flags=0, "
        "OS=0x40004, fileType=1, subtype=0, date=(0, 0)), "
        "kids=[StringFileInfo([StringTable('040904B0', ["
        "StringStruct('CompanyName', 'Koreapanda4444'), "
        "StringStruct('FileDescription', 'RadixScope desktop application'), "
        f"StringStruct('FileVersion', {__version__!r}), "
        "StringStruct('InternalName', 'RadixScope'), "
        "StringStruct('OriginalFilename', 'RadixScope.exe'), "
        "StringStruct('ProductName', 'RadixScope'), "
        f"StringStruct('ProductVersion', {__version__!r})])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])"
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    work = root / "build" / "desktop"
    work.mkdir(parents=True, exist_ok=True)
    assets = root / "src" / "radixscope" / "assets"
    make_icon(assets / "radixscope.svg", work / "radixscope.ico")
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--windowed", "--noupx", "--name", "RadixScope", "--paths", str(root / "src"),
        "--distpath", str(root / "dist" / "desktop"), "--workpath", str(work / "analysis"),
        "--specpath", str(work), "--add-data", f"{assets}:radixscope/assets",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
    ]
    if os.name == "nt":
        metadata = work / "version.txt"
        metadata.write_text(version_resource(), encoding="utf-8")
        command.extend(["--icon", str(work / "radixscope.ico"), "--version-file", str(metadata)])
    command.append(str(root / "packaging" / "desktop_entry.py"))
    subprocess.run(command, cwd=root, check=True)
    bundle = root / "dist" / "desktop" / "RadixScope"
    for name in ("README.md", "README.ko.md"):
        shutil.copy2(root / name, bundle / name)
    shutil.copytree(root / "docs", bundle / "docs", dirs_exist_ok=True)
    dependencies = {
        name: importlib.metadata.version(name) for name in ("PySide6", "shiboken6", "pyinstaller")
    }
    for name in ("PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6", "pyinstaller"):
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or ():
            source = Path(str(distribution.locate_file(entry)))
            if "licenses" in entry.parts and source.is_file():
                target = bundle / "licenses" / name / Path(*entry.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    information = {
        "version": __version__, "python": platform.python_version(),
        "platform": platform.system(), "architecture": platform.machine(),
        "dependencies": dependencies,
    }
    (bundle / "build-info.json").write_text(json.dumps(information, indent=2), encoding="utf-8")
    system = "windows" if os.name == "nt" else platform.system().lower()
    machine = platform.machine()
    architecture = "x64" if machine.lower() in ("amd64", "x86_64") else machine
    archive = root / "dist" / f"RadixScope-{__version__}-{system}-{architecture}.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                package.write(path, path.relative_to(bundle.parent))
    print(f"Desktop package: {archive}")


if __name__ == "__main__":
    main()
