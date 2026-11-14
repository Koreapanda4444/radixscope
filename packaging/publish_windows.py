"""Publish known build outputs without allowing COLLECT to clean the repository root."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'build/windows/stage/RadixScope'


def main() -> None:
    executable = STAGE / 'RadixScope.exe'
    runtime = STAGE / '_internal'
    if not executable.is_file() or not runtime.is_dir():
        raise RuntimeError('incomplete Windows build')
    manifest = ROOT / 'build/windows/published.json'
    previous = json.loads(manifest.read_text()) if manifest.exists() else {}
    files = [executable, *[p for p in runtime.rglob('*') if p.is_file()]]
    for source in files:
        target = ROOT / source.relative_to(STAGE)
        relative = target.relative_to(ROOT).as_posix()
        if (target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != previous.get(relative)
                and target.read_bytes() != source.read_bytes()):
            raise RuntimeError(f'Unmanaged output exists: {relative}; move it before building')
    old = ROOT / 'dist/RadixScope/RadixScope.exe'
    if old.exists():
        import pefile
        pe = pefile.PE(str(old))
        names = [table.entries.get(b'ProductName') for groups in pe.FileInfo
                 for group in groups if group.Key == b'StringFileInfo' for table in group.StringTable]
        if b'RadixScope' not in names or old.with_suffix('.exe.previous-build').exists():
            raise RuntimeError('Move the old dist folder before building; it will not be overwritten')
        old.rename(old.with_suffix('.exe.previous-build'))
    published = {}
    for source in files:
        relative = source.relative_to(STAGE)
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        published[relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    for relative, digest in previous.items():
        path = ROOT / relative
        if (relative not in published and path.is_relative_to(ROOT) and path.is_file()
                and hashlib.sha256(path.read_bytes()).hexdigest() == digest):
            path.unlink()
    manifest.write_text(json.dumps(published, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
