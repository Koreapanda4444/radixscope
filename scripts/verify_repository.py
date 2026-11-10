"""Check current documentation, metadata and optional built Python distributions."""

import argparse
import contextlib
import importlib.metadata
import io
import json
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

from radixscope import __version__
from radixscope.core import BitField, BitfieldLayout


def verify_packages(root: Path) -> None:
    wheels = list((root / "dist").glob(f"radixscope-{__version__}-*.whl"))
    assert wheels, "build the Python wheel first"
    for wheel in wheels:
        with ZipFile(wheel) as package:
            for asset in ("radixscope.svg", "ui-check.svg", "ui-up.svg", "ui-down.svg", "ko.json"):
                assert f"radixscope/assets/{asset}" in package.namelist()
            translations = json.loads(package.read("radixscope/assets/ko.json"))
            assert translations["Convert"] == "변환"
            metadata = BytesParser().parsebytes(
                package.read(f"radixscope-{__version__}.dist-info/METADATA")
            )
            assert metadata["Version"] == __version__
    archive = root / "dist" / f"radixscope-{__version__}.tar.gz"
    with tarfile.open(archive) as source:
        assert f"radixscope-{__version__}/packaging/windows.iss" in source.getnames()


def main(*, packages: bool = False) -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__ == "1.0.0"
    assert importlib.metadata.version("radixscope") == __version__
    assert not (root / "tests").exists()
    documents = [root / "README.md", root / "README.ko.md", *sorted((root / "docs").rglob("*.md"))]
    commands: set[str] = set()
    snippets = links = 0
    fence = chr(96) * 3
    for document in documents:
        text = document.read_text(encoding="utf-8")
        assert "2.1.0" not in text
        assert re.search(r"\bv[23](?:\.\d+)*\b", text, re.IGNORECASE) is None
        assert text.count(fence) % 2 == 0
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#", "mailto:")):
                continue
            path = (document.parent / target.split("#", 1)[0]).resolve()
            assert path.is_relative_to(root) and path.exists(), (document, target)
            links += 1
        for language, code in re.findall(rf"{fence}([^\n]*)\n(.*?){fence}", text, re.DOTALL):
            if language == "python":
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(code, str(document), "exec"), {})
                snippets += 1
            elif language in ("sh", "bash"):
                commands.update(
                    line.strip() for line in code.splitlines()
                    if line.strip().startswith("radixscope ")
                )
    with tempfile.TemporaryDirectory(prefix="radixscope-docs-") as directory:
        temporary = Path(directory)
        (temporary / "numbers.txt").write_text("255\n1/3\n0.1\n", encoding="utf-8")
        layout = BitfieldLayout(16, (BitField("low", 0, 8, True), BitField("high", 8, 8)))
        (temporary / "layout.json").write_text(layout.to_json(), encoding="utf-8")
        for command in sorted(commands):
            process = subprocess.run(
                [sys.executable, "-m", "radixscope", *shlex.split(command)[1:]],
                input="1\nF\n", capture_output=True, text=True, cwd=temporary,
                timeout=20, check=False,
            )
            assert process.returncode == 0, (command, process.stderr)
            assert process.stdout.strip() and not process.stderr, command
    if packages:
        verify_packages(root)
    print(f"Repository verification: {len(documents)} documents, {links} local links, "
          f"{snippets} Python examples, {len(commands)} CLI examples passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", action="store_true", help="also check built wheel/source")
    main(packages=parser.parse_args().packages)
