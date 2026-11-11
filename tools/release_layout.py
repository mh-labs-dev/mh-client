"""Shared local release paths. Build outputs are never committed to Git."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURES = {
    'windows': {'x64', 'x86', 'arm64'},
    'macos': {'arm64', 'x86_64', 'universal'},
    'ios': {'arm64', 'simulator'},
    'android': {'arm64-v8a', 'armeabi-v7a', 'x86_64', 'universal'},
}


def release_dir(platform, version, arch, root=ROOT):
    if platform not in ARCHITECTURES or arch not in ARCHITECTURES[platform]:
        raise ValueError('Unsupported release platform or architecture')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', version):
        raise ValueError('Invalid release version')
    base = Path(root).resolve() / 'release'
    path = base / platform / version / arch
    if not path.resolve().is_relative_to(base):
        raise ValueError('Release path escapes the local release directory')
    return path
