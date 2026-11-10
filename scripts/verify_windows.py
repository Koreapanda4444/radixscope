"""Validate extracted and installed distributions on a disposable Windows runner."""

import json
import os
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from zipfile import ZipFile

from radixscope import __version__


def check_application(executable: Path, receipt: Path) -> dict[str, object]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    process = subprocess.run(
        [str(executable), "--self-check", str(receipt)],
        cwd=executable.parent, env=environment, timeout=180, check=False,
    )
    if not receipt.is_file():
        raise RuntimeError(f"no desktop verification receipt; exit code {process.returncode}")
    result = json.loads(receipt.read_text(encoding="utf-8"))
    if process.returncode != 0 or result.get("status") != "ok":
        raise RuntimeError(f"desktop validation failed: {result}")
    assert result["version"] == __version__ == "1.0.0"
    assert result["workspaces"] == 8 and result["calculations"] == 26
    assert result["languages"] == ["en", "ko"]
    assert result["cancellation"] and result["settings"]
    return dict(result)


def main() -> None:
    if os.name != "nt" or struct.calcsize("P") != 8:
        raise RuntimeError("distribution verification requires Windows x64")
    root = Path(__file__).resolve().parents[1]
    archive = root / "dist" / f"RadixScope-{__version__}-windows-x64.zip"
    installer = root / "dist" / f"RadixScope-{__version__}-windows-x64-setup.exe"
    assert archive.is_file() and installer.is_file()
    receipt_directory = root / "build" / "desktop" / "verification"
    receipt_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="RadixScope distribution ") as directory:
        temporary = Path(directory)
        with ZipFile(archive) as package:
            package.extractall(temporary / "portable")
        bundle = temporary / "portable" / "RadixScope"
        assert (bundle / "_internal").is_dir()
        assert any((bundle / "licenses").rglob("*LICENSE*"))
        assert any((bundle / "_internal").rglob("qwindows.dll"))
        information = json.loads((bundle / "build-info.json").read_text(encoding="utf-8"))
        assert information["version"] == __version__
        portable = check_application(
            bundle / "RadixScope.exe", receipt_directory / "portable.json"
        )
        installed = temporary / "Installed RadixScope"
        subprocess.run(
            [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
             "/CURRENTUSER", f"/DIR={installed}", f"/LOG={receipt_directory / 'install.log'}"],
            cwd=temporary, timeout=180, check=True,
        )
        setup = check_application(
            installed / "RadixScope.exe", receipt_directory / "installed.json"
        )
        uninstaller = installed / "unins000.exe"
        assert uninstaller.is_file()
        subprocess.run(
            [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
             f"/LOG={receipt_directory / 'uninstall.log'}"],
            cwd=temporary, timeout=60, check=True,
        )
        deadline = time.monotonic() + 20
        while (installed / "RadixScope.exe").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not (installed / "RadixScope.exe").exists(), "uninstall left the executable"
        assert not (installed / "_internal").exists(), "uninstall left the runtime"
    summary = {"portable": portable, "installed": setup, "uninstalled": True}
    (receipt_directory / "distribution.json").write_text(
        json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
