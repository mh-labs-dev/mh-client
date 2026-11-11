"""Verify a Windows release, its corresponding source and embedded portable payload."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import brotli

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from build_privacy import check_tree, inspect_bytes


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(release):
    release = release.resolve()
    if not release.is_relative_to(ROOT / 'release/windows'):
        raise ValueError('Expected a release/windows version directory')
    download = release
    release = ROOT / '.local/windows-builds' / download.relative_to(ROOT / 'release/windows')
    download_record = json.loads((release / 'download.json').read_text('utf-8'))
    exe_path = download / download_record['name']
    if exe_path.suffix != '.exe' or sorted(p.name for p in download.iterdir()) != [exe_path.name]:
        raise ValueError('Download directory must contain only one EXE')
    if sha(exe_path.read_bytes()) != download_record['sha256']:
        raise ValueError('Download EXE checksum mismatch')
    checksum_files = list(release.glob('*-sha256.json'))
    if len(checksum_files) != 1:
        raise ValueError('Expected one checksum manifest')
    checksums = json.loads(checksum_files[0].read_text('utf-8'))
    for name, expected in checksums.items():
        if Path(name).name != name or sha((release / name).read_bytes()) != expected:
            raise ValueError('Artifact checksum mismatch')
    expected_text = ''.join(f'{value}  {name}\n' for name, value in checksums.items())
    if (release / 'SHA256SUMS.txt').read_text('utf-8') != expected_text:
        raise ValueError('Text checksums differ from manifest')
    unpacked = release / 'unpacked'
    check_tree(unpacked)
    manifest = json.loads((unpacked / 'build-manifest.json').read_text('utf-8'))
    for name, expected in manifest['files'].items():
        path = (unpacked / name).resolve()
        if not path.is_relative_to(unpacked) or sha(path.read_bytes()) != expected:
            raise ValueError('Application file mismatch')
    profile_path = ROOT / 'config/controller.default.json'
    if manifest['controller_profile_sha256'] != sha(profile_path.read_bytes()):
        raise ValueError('Release was built for another profile')
    profile = json.loads(profile_path.read_text('utf-8'))
    native = (unpacked / 'librustdesk.dll').read_bytes()
    for key in ('custom-rendezvous-server', 'api-server', 'key'):
        if profile[key].encode() not in native:
            raise ValueError('Default server configuration is missing from native library')
    if b'.trycloudflare.com' in native:
        raise ValueError('Native library contains an obsolete temporary tunnel')
    portable = (release / manifest['portable_exe']['name']).read_bytes()
    if exe_path.read_bytes() != portable:
        raise ValueError('Download EXE differs from verified portable application')
    if (unpacked / 'LICENSE.txt').read_bytes() != (ROOT / 'LICENCE').read_bytes():
        raise ValueError('Embedded license differs from repository license')
    if inspect_bytes(portable):
        raise ValueError('Portable launcher contains a local build path')
    if not portable.startswith(b'MZ'):
        raise ValueError('Portable executable is not a Windows PE file')
    # The packer embeds this exact payload. Verify every decompressed member.
    payload = (ROOT / 'libs/portable/data.bin').read_bytes()
    if payload not in portable or not payload.startswith(b'rustdesk'):
        raise ValueError('Portable payload differs from the current build')
    offset = 8
    members = set()
    while payload[offset:offset + 8] != b'rustdesk':
        size = int.from_bytes(payload[offset:offset + 4], 'big'); offset += 4
        name = payload[offset:offset + size].decode().replace('\\', '/').removeprefix('./'); offset += size
        size = int.from_bytes(payload[offset:offset + 4], 'big'); offset += 4
        data = brotli.decompress(payload[offset:offset + size]); offset += size
        md5 = payload[offset:offset + 32].decode(); offset += 32
        if hashlib.md5(data).hexdigest() != md5 or manifest['files'].get(name) != sha(data):
            raise ValueError('Portable member differs from application manifest')
        members.add(name)
    if members != set(manifest['files']) or payload[offset + 8:].decode().replace('\\', '/') != './MH.exe':
        raise ValueError('Portable member list or entry point mismatch')
    for name in checksums:
        if name.endswith('.zip'):
            with zipfile.ZipFile(release / name) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Corrupt ZIP')
    source = release / manifest['source_archive']['name']
    with zipfile.ZipFile(source) as archive:
        if archive.read('config/controller.default.json') != profile_path.read_bytes():
            raise ValueError('Source profile differs from release')
    subprocess.run([sys.executable, str(ROOT / 'tools/publication_check.py'),
                    '--source-archive', str(source)], check=True)
    print(json.dumps({'artifacts_verified': len(checksums), 'portable_members_verified': len(members),
                      'fixed_profile_embedded': True, 'source_check': 'passed',
                      'actual_remote_control_tested': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release', type=Path)
    verify(parser.parse_args().release)
