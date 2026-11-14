import hashlib
import html
import json
import urllib.request
import importlib.metadata
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
    bundle = ROOT / "_internal"
    destination = bundle / "licenses"
    destination.mkdir(parents=True, exist_ok=True)
    inventory = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*")
                       if p.is_file() and "licenses" not in p.relative_to(bundle).parts)
    notices: dict[str, str] = {}
    components: dict[str, object] = {}

    def retain(name: str, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        if digest not in notices:
            filename = digest[:12] + "-" + Path(name).name
            (destination / filename).write_bytes(data)
            notices[digest] = filename
        return notices[digest]

    for name in ("PySide6-Essentials", "PySide6-Addons", "shiboken6"):
        dist = importlib.metadata.distribution(name)
        paths = []
        for entry in dist.files or ():
            if any(term in str(entry).lower() for term in ("license", "copying", "notice")):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    paths.append(retain(source.name, source.read_bytes()))
        components[name] = {"version": dist.version, "notices": sorted(set(paths))}
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        python_license = Path(sys.base_prefix) / "LICENSE"
    if python_license.is_file():
        components["Python"] = {"version": sys.version.split()[0],
                                "notices": [retain("Python-LICENSE.txt", python_license.read_bytes())]}
    urls = {
        "LGPL-3.0.txt": "https://www.gnu.org/licenses/lgpl-3.0.txt",
        "GPL-3.0.txt": "https://www.gnu.org/licenses/gpl-3.0.txt",
        "Qt-for-Python-notices.html": "https://doc.qt.io/qtforpython-6/licenses.html",
        "Qt-third-party-notices.html": "https://doc.qt.io/qt-6/licenses-used-in-qt.html",
        "Python-notices.html": "https://docs.python.org/3/license.html",
    }
    references = []
    for filename, url in urls.items():
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        if not data:
            raise RuntimeError("empty upstream license notice")
        references.append((filename, retain(filename, data)))
    from PySide6.QtCore import qVersion
    qt_version = qVersion()
    pyside_version = importlib.metadata.version("PySide6")
    qt_source = ("https://download.qt.io/official_releases/qt/"
                 + ".".join(qt_version.split(".")[:2]) + "/" + qt_version + "/single/")
    pyside_source = ("https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-"
                     + pyside_version + "-src/")
    document = """<h1>RadixScope: third-party notices</h1>
<p>Python, Qt, PySide6 and shiboken are included in this program. Their licenses apply
separately; this notice does not assign a license to RadixScope.</p>
<p>Qt/PySide6/shiboken use the LGPLv3 open-source option. LGPL libraries are dynamically
loaded from _internal. You may replace them with compatible modified builds and debug
those modifications, including reverse engineering for that purpose. Keep the same
Python ABI, Qt ABI, plugin paths and DLL filenames. No integrity restriction is applied.</p>
<p>The unmodified corresponding library sources and upstream build instructions are
available for the exact versions below. When redistributing a build, retain these
notices and provide equivalent access to the corresponding sources, including any
modifications and build files. Verify source availability for the lifetime of your
binary distribution; mirror the matching sources beside downloads when necessary.</p>
<p>PySide6 is an installation metapackage; only its runtime components are listed.
PyInstaller is a build tool; its bootloader exception permits distribution without
copying its build-tool license. Other unknown component notices are retained.</p>"""
    document += "<p>Qt " + html.escape(qt_version) + ': <a href="' + qt_source + '">Source and build files</a></p>'
    document += "<p>PySide6/shiboken " + html.escape(pyside_version) + ': <a href="' + pyside_source + '">Source and build files</a></p>'
    document += "<h2>License texts and attributions</h2><ul>"
    for label, filename in references:
        document += '<li><a href="' + filename + '">' + label + '</a></li>'
    for filename in sorted(notices.values()):
        document += '<li><a href="' + filename + '">' + html.escape(filename) + '</a></li>'
    for name, component in components.items():
        document += '<li>' + html.escape(name) + ' ' + html.escape(str(component)) + '</li>'
    document += "</ul><p>Official obligations: https://www.qt.io/development/open-source-lgpl-obligations</p>"
    (destination / "NOTICE.html").write_text(document, encoding="utf-8")
    (destination / "inventory.json").write_text(json.dumps(
        {"components": components, "runtime_files": inventory, "source_urls": [qt_source, pyside_source],
         "notice_files": sorted(notices.values())}, indent=2), encoding="utf-8")


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
