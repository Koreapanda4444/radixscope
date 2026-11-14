import importlib.metadata
import shutil
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from radixscope import __version__
from radixscope.gui.icon import ICON_SIZES, icon_image


def make_icon(source: Path, destination: Path) -> None:
    images: list[tuple[int, bytes]] = []
    for size in ICON_SIZES:
        image = icon_image(size, source)
        png = destination.with_name(f"{destination.stem}-{size}.png")
        if not image.save(str(png)):
            raise OSError("could not render application icon")
        images.append((size, png.read_bytes()))
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


def copy_licenses() -> None:
    bundle = ROOT / "dist" / "RadixScope"
    for name in ("PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6", "pyinstaller"):
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or ():
            source = Path(str(distribution.locate_file(entry)))
            if "licenses" in entry.parts and source.is_file():
                target = bundle / "licenses" / name / Path(*entry.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)


def main() -> None:
    if sys.argv[1:] == ["--licenses"]:
        copy_licenses()
        return
    if sys.argv[1:]:
        raise SystemExit("Usage: windows_resources.py [--licenses]")
    work = ROOT / "build" / "windows"
    work.mkdir(parents=True, exist_ok=True)
    make_icon(ROOT / "src/radixscope/assets/radixscope.svg", work / "radixscope.ico")
    (work / "version.txt").write_text(version_resource(), encoding="utf-8")


if __name__ == "__main__":
    main()
