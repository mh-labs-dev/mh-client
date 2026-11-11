"""Move legacy Windows dist outputs into release/windows/version/x64 without overwrites."""
import argparse
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from release_layout import release_dir

PATTERN = re.compile(r'MH-([A-Za-z0-9][A-Za-z0-9.-]*)-windows-x64(?:(-source|-sha256)?\.(exe|zip|json))?')


def hashes(path):
    files = sorted(path.rglob('*')) if path.is_dir() else [path]
    result = {}
    for file in [path, *files]:
        if file.is_symlink():
            raise ValueError('Legacy output contains a symbolic link; refusing to move')
    for file in files:
        if file.is_file():
            name = file.relative_to(path).as_posix() if path.is_dir() else '.'
            result[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def plan(root=ROOT):
    root = Path(root).resolve()
    legacy = root / 'dist'
    if not legacy.exists():
        return []
    if legacy.is_symlink():
        raise ValueError('Legacy dist must not be a symbolic link')
    moves = []
    for source in sorted(legacy.iterdir()):
        match = PATTERN.fullmatch(source.name)
        if match:
            base = release_dir('windows', match[1], 'x64', root)
            target = base / ('unpacked' if source.is_dir() else source.name)
        elif source.is_dir():
            # Only recognize a version directory with Windows artifacts for that version.
            entries = list(source.iterdir())
            artifacts = [PATTERN.fullmatch(p.name) for p in entries if p.name != 'unpacked']
            if not artifacts or any(m is None or m[1] != source.name for m in artifacts):
                continue
            target = release_dir('windows', source.name, 'x64', root)
        else:
            continue
        if target.exists():
            raise FileExistsError(f'Destination already exists: {target}')
        if any(target == other or target in other.parents or other in target.parents
               for _, other, _ in moves):
            raise FileExistsError('Legacy outputs overlap; refusing to merge versions')
        moves.append((source, target, hashes(source)))
    return moves


def migrate(root=ROOT, apply=False):
    root = Path(root).resolve()
    moves = plan(root)
    for source, target, expected in moves:
        print(f'{source.relative_to(root)} -> {target.relative_to(root)}')
        if apply:
            if target.exists() or hashes(source) != expected:
                raise RuntimeError('Output changed after planning; no files replaced')
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
            if hashes(target) != expected:
                raise RuntimeError('Moved output failed integrity verification')
    print(f'{"Moved" if apply else "Planned"} {len(moves)} Windows release outputs.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    migrate(apply=parser.parse_args().apply)
