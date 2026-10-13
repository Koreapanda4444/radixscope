import tomllib
from pathlib import Path

from radixscope import __version__


def test_package_version() -> None:
    assert __version__ == "2.1.0"
    path = Path(__file__).parents[1] / "pyproject.toml"
    project = tomllib.loads(path.read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__
