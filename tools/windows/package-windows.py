"""Stage the Windows build and create an auditable portable/source bundle."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT
PACKAGES = ROOT / 'dist'
VERSION = os.environ.get('MH_PACKAGE_VERSION', '1.5.1-mh.6-controller-test')
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', VERSION):
    raise ValueError('Invalid package version')
PROFILE = os.environ.get('MH_CONTROLLER_PROFILE_PATH')
NAME = f'MH-{VERSION}-windows-x64'
RELEASE = PACKAGES / VERSION
DIST = RELEASE / 'unpacked'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args, cwd=SOURCE):
    return subprocess.check_output(['git', *args], cwd=cwd)


def stage():
    release = SOURCE / 'flutter/build/windows/x64/runner/Release'
    for name in ('MH.exe', 'librustdesk.dll', 'flutter_windows.dll',
                 'dylib_virtual_display.dll', 'data/app.so'):
        if not (release / name).is_file():
            raise FileNotFoundError(f'Missing build output: {name}')
    if RELEASE.exists():
        raise FileExistsError('Version directory already exists; select a new version without overwriting history')
    RELEASE.mkdir(parents=True)
    shutil.copytree(release, DIST, ignore=shutil.ignore_patterns('*.pdb', '*.lib', '*.exp'))
    shutil.copy2(SOURCE / 'LICENCE', DIST / 'LICENSE.txt')
    (DIST / 'README.txt').write_text(
        'MH Windows x64 preview — based on RustDesk 1.5.1\n\n'
        'Run MH.exe. This build is unsigned. Keep the entire extracted folder together.\n'
        'Configure your ID server, relay, API URL and server public key in Network settings.\n'
        'Server addresses, account passwords and trial licenses are not embedded in this package.\n'
        'MH uses its own application configuration. Upstream RustDesk is not overwritten.\n'
        'Virtual display and printer driver installers are not bundled.\n'
        'Source: the accompanying MH source archive. Upstream copyright and AGPL license are retained.\n',
        encoding='utf-8')
    if PROFILE:
        (DIST / 'README.txt').write_text(
            'MH Windows 控制端预览\n\n打开 MH.exe，使用 Pro Server 普通账号登录，然后选择 Mac 并点击连接。\n'
            '服务地址与服务器公钥可在设置 > 网络中修改。连接需要有效服务与设备权限。\n'
            '远控密码认证保持原流程。设备接入、分配及权限由管理员另行完成。\n'
            '应用配置保存在独立的 MH Test 目录。\n'
            '本包未签名，不自动安装服务；不包含账号密码、许可证或服务器私钥。\n'
            '保留上游版权与 AGPL 许可，修改后的对应源码随同提供。\n', encoding='utf-8')
    print(DIST)


def source_bundle(output):
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        if PROFILE:
            archive.write(PROFILE, 'controller-profile.json')
        included = set()
        for base in (SOURCE, SOURCE / 'libs/hbb_common'):
            paths = git('ls-files', '--cached', '--others', '--exclude-standard', '-z', cwd=base)
            for raw in sorted(set(paths.split(b'\0'))):
                if not raw:
                    continue
                file = base / raw.decode('utf-8')
                rel = file.relative_to(SOURCE).as_posix()
                if file.is_file() and rel not in included:
                    archive.write(file, rel)
                    included.add(rel)
        for name in ('src/bridge_generated.rs', 'src/bridge_generated.io.rs',
                     'flutter/lib/generated_bridge.dart', 'flutter/lib/generated_bridge.freezed.dart'):
            if name not in included:
                archive.write(SOURCE / name, name)
        archive.writestr('SOURCE-README.txt',
            'MH modified source, including hbb_common and native bridge files.\n'
            'See README.md for build steps and upstream.json for pinned versions.\n'
            'No Git metadata is included. For Git-dependent packaging, use a clone of the MH\n'
            'repository at the matching release commit with its submodule initialized.\n')


def finalize():
    portable = SOURCE / 'target/release/rustdesk-portable-packer.exe'
    output_exe = RELEASE / (NAME + '.exe')
    shutil.copy2(portable, output_exe)
    source_zip = RELEASE / (NAME + '-source.zip')
    source_bundle(source_zip)
    files = {p.relative_to(DIST).as_posix(): digest(p)
             for p in sorted(DIST.rglob('*')) if p.is_file()}
    manifest = {
        'brand': 'MH', 'version': VERSION, 'origin': 'self-built',
        'controller_only': bool(PROFILE),
        'controller_profile_sha256': digest(Path(PROFILE)) if PROFILE else None,
        'source_commit': git('rev-parse', 'HEAD').decode().strip(),
        'hbb_common_commit': git('rev-parse', 'HEAD', cwd=SOURCE / 'libs/hbb_common').decode().strip(),
        'source_modified': True, 'signed': False,
        'built_at_utc': datetime.now(timezone.utc).isoformat(),
        'features': ['flutter', 'hwcodec', 'vram'],
        'toolchain': {
            'rust': '1.75.0', 'flutter': '3.24.5', 'target': 'x86_64-pc-windows-msvc',
            'python': sys.version.split()[0], 'msvc_client': os.environ.get('VCToolsVersion'),
            'vcpkg_commit': '9e593bb18ea69cc5095e012465dcd675a822ed0d',
            'engine_zip_sha256': 'ec8cabf36ee4ff24c8d98de25b00e70781eb03876265aee84d0fe554a110036e',
        },
        'source_archive': {'name': source_zip.name, 'sha256': digest(source_zip)},
        'portable_exe': {'name': output_exe.name, 'sha256': digest(output_exe)},
        'files': files,
    }
    (DIST / 'build-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    zip_path = RELEASE / (NAME + '.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in sorted(DIST.rglob('*')):
            if file.is_file():
                archive.write(file, NAME + '/' + file.relative_to(DIST).as_posix())
    checksums = {p.name: digest(p) for p in (output_exe, zip_path, source_zip)}
    (RELEASE / (NAME + '-sha256.json')).write_text(json.dumps(checksums, indent=2), encoding='utf-8')
    print(json.dumps({'artifacts': list(checksums), 'files': len(files)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['stage', 'finalize'])
    args = parser.parse_args()
    stage() if args.action == 'stage' else finalize()
