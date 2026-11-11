"""Warm the pinned vcpkg MSYS downloads in parallel, preserving upstream hashes."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
VCPKG = ROOT / '.cache/mh-tools/vcpkg'


def main():
    table = (VCPKG / 'scripts/cmake/vcpkg_acquire_msys.cmake').read_text(encoding='utf-8')
    packages, aliases = {}, {}
    for block in re.findall(r'^\s*z_vcpkg_acquire_msys_declare_package\((.*?)\n\s*\)', table, re.S | re.M):
        url = re.search(r'URL "(https://mirror\.msys2\.org/[^"\s]+)"', block)
        sha = re.search(r'SHA512 ([0-9a-f]{128})', block)
        if not url or not sha:
            continue
        filename = url[1].rsplit('/', 1)[1]
        name = re.match(r'(.+)-[^-]+-[^-]+-[^-]+\.pkg\.tar\.', filename)
        if not name:
            continue
        name = name[1]
        deps = re.search(r'\bDEPS ([^\n]+)', block)
        provides = re.search(r'\bPROVIDES ([^\n]+)', block)
        packages[name] = (url[1], sha[1], filename, deps[1].split('#', 1)[0].split() if deps else [])
        if provides:
            aliases.update({alias: name for alias in provides[1].split('#', 1)[0].split()})
    pending = 'bash coreutils file gawk grep gzip diffutils make pkgconf sed automake1.16 perl msys2-runtime'.split()
    selected = {}
    while pending:
        name = pending.pop()
        if name not in packages:
            name = aliases.get(name, name)
        if name in selected:
            continue
        if name not in packages:
            raise ValueError(f'Unknown pinned MSYS package: {name}')
        selected[name] = packages[name]
        pending.extend(packages[name][3])

    def fetch(item):
        url, sha, filename, _ = item
        destination = VCPKG / 'downloads' / ('msys2-' + filename)
        if destination.exists() and hashlib.sha512(destination.read_bytes()).hexdigest() == sha:
            return 'cached'
        direct = url.replace('https://mirror.msys2.org/', 'https://repo.msys2.org/')
        with urllib.request.urlopen(direct, timeout=60) as response:
            data = response.read()
        if hashlib.sha512(data).hexdigest() != sha:
            raise ValueError(f'MSYS checksum mismatch: {filename}')
        # Each worker has a distinct package; vcpkg only sees complete, verified files.
        temporary = destination.with_suffix(destination.suffix + '.mh-download')
        temporary.write_bytes(data)
        temporary.replace(destination)
        return 'downloaded'

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, selected.values()))
    print(f'MSYS cache ready: {len(results)} packages, {results.count("downloaded")} downloaded.')


if __name__ == '__main__':
    main()
