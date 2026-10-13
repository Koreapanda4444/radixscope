import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from radixscope import __version__


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    system = "windows" if os.name == "nt" else platform.system().lower()
    machine = platform.machine()
    architecture = "x64" if machine.lower() in ("amd64", "x86_64") else machine
    archive = (
        Path(sys.argv[1]).resolve() if len(sys.argv) > 1
        else root / "dist" / f"RadixScope-{__version__}-{system}-{architecture}.zip"
    )
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    with tempfile.TemporaryDirectory(prefix="radixscope-verify-") as directory:
        extracted = Path(directory) / "package with spaces \uac80\uc99d"
        extracted.mkdir()
        with ZipFile(archive) as package:
            package.extractall(extracted)
        bundle = extracted / "RadixScope"
        executable = bundle / ("RadixScope.exe" if os.name == "nt" else "RadixScope")
        assert executable.is_file()
        if os.name != "nt":
            executable.chmod(0o755)
        information = json.loads((bundle / "build-info.json").read_text(encoding="utf-8"))
        assert information["version"] == __version__
        assert (bundle / "docs" / "ko" / "desktop.md").is_file()
        assert (bundle / "THIRD_PARTY_NOTICES.md").is_file()
        result_path = extracted / "verification.json"
        result = subprocess.run(
            [str(executable), "--smoke-test", str(result_path)], cwd=extracted,
            env=environment, capture_output=True, text=True, encoding="utf-8",
            check=False, timeout=120,
        )
        if not result_path.is_file():
            raise RuntimeError(f"Desktop exited {result.returncode}: {result.stderr}")
        report = json.loads(result_path.read_text(encoding="utf-8"))
        assert result.returncode == 0 and report["status"] == "ok", report
        assert report["version"] == __version__
        assert len(report["checks"]) == 9, report
        print(json.dumps(report, indent=2))
    print("Extracted desktop GUI, all calculation workers, bit editors and cancellation passed")


if __name__ == "__main__":
    main()
