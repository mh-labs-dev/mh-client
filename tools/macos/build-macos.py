"""Build and package an ad-hoc-signed MH macOS test app on the host architecture."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from controller_profile import validate
from release_layout import release_dir

TOOLS = ROOT / '.cache/mh-tools/macos'
FEATURES = 'flutter,hwcodec,unix-file-copy-paste,screencapturekit'


def run(args, env, cwd=ROOT):
    subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, check=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def environment(arch, profile):
    env = os.environ.copy()
    env.update({
        'CARGO_HOME': str(TOOLS / 'cargo'),
        'RUSTUP_HOME': str(TOOLS / 'rustup'),
        'RUSTUP_TOOLCHAIN': '1.81.0',
        'MH_CONTROLLER': 'true',
        'CARGO_TARGET_DIR': str(ROOT / 'target'),
        'PUB_CACHE': str(TOOLS / 'pub-cache'),
        'VCPKG_ROOT': str(TOOLS / 'vcpkg'),
        'VCPKG_DEFAULT_TRIPLET': 'arm64-osx' if arch == 'arm64' else 'x64-osx',
        'LIBCLANG_PATH': '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib',
        'MACOSX_DEPLOYMENT_TARGET': '12.3',
        'FLUTTER_XCODE_MACOSX_DEPLOYMENT_TARGET': '12.3',
        'FLUTTER_XCODE_ARCHS': arch,
        'FLUTTER_XCODE_ONLY_ACTIVE_ARCH': 'YES',
        'FLUTTER_XCODE_CODE_SIGNING_ALLOWED': 'NO',
        'FLUTTER_XCODE_CODE_SIGNING_REQUIRED': 'NO',
        'FLUTTER_XCODE_ENABLE_USER_SCRIPT_SANDBOXING': 'NO',
    })
    env['PATH'] = os.pathsep.join([str(TOOLS / 'cargo/bin'), str(TOOLS / 'flutter/bin'),
                                  str(TOOLS / 'native-tools/bin'), env.get('PATH', '')])
    env.pop('MH_CONTROLLER_PROFILE', None)
    if profile is not None:
        env['MH_CONTROLLER_PROFILE'] = json.dumps(profile)
    return env


def flutter_build_args(profile):
    return ['flutter', 'build', 'macos', '--release', '--dart-define=MH_DESKTOP=true',
            '--dart-define=MH_CONTROLLER=true',
            f'--dart-define=MH_CONTROLLER_CONFIGURED={str(profile is not None).lower()}']


def prepare_icon(env):
    with tempfile.TemporaryDirectory(prefix='mh-icon-') as directory:
        iconset = Path(directory) / 'MH.iconset'
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                suffix = '@2x' if scale == 2 else ''
                output = iconset / f'icon_{size}x{size}{suffix}.png'
                run(['sips', '-z', size * scale, size * scale, ROOT / 'branding/mh-icon.png',
                     '--out', output], env)
        run(['iconutil', '-c', 'icns', iconset, '-o',
             ROOT / 'flutter/macos/Runner/AppIcon.icns'], env)


def sign_local_app(app, env):
    # These local test builds have no Developer ID / Team ID. Hardened-runtime
    # library validation rejects their ad-hoc-signed Flutter frameworks.
    # Do not alter the production Developer ID signing script or OS policy.
    sign = ['codesign', '--force', '--sign', '-', '--options', '0']
    frameworks = app / 'Contents/Frameworks'
    for path in sorted(frameworks.rglob('*')):
        if path.is_file() and not path.is_symlink():
            kind = subprocess.check_output(['file', '-b', str(path)], text=True)
            if 'Mach-O' in kind:
                run([*sign, path], env)
    for path in sorted(frameworks.rglob('*.framework'), key=lambda p: len(p.parts), reverse=True):
        run([*sign, path], env)
    run([*sign, app / 'Contents/MacOS/service'], env)
    run([*sign, '--entitlements', ROOT / 'flutter/macos/Runner/Release.entitlements', app], env)
    run(['codesign', '--verify', '--deep', '--strict', app], env)


def package(version, arch, profile, env):
    destination = release_dir('macos', version, arch)
    if destination.exists():
        raise FileExistsError(f'Release already exists: {destination}')
    app = ROOT / 'flutter/build/macos/Build/Products/Release/MH.app'
    if not app.is_dir():
        raise FileNotFoundError(app)
    local = ROOT / '.local'
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='macos-package-', dir=local) as directory:
        staging = Path(directory)
        output = staging / 'output'
        output.mkdir()
        bundled = output / 'MH.app'
        run(['ditto', app, bundled], env)
        shutil.copy2(ROOT / 'target/release/service', bundled / 'Contents/MacOS/service')
        shutil.copy2(ROOT / 'LICENCE', bundled / 'Contents/Resources/LICENSE.txt')
        sign_local_app(bundled, env)
        run(['lipo', '-verify_arch', arch, bundled / 'Contents/MacOS/MH'], env)
        image_root = staging / 'image'
        image_root.mkdir()
        run(['ditto', bundled, image_root / 'MH.app'], env)
        (image_root / 'Applications').symlink_to('/Applications')
        name = f'MH-{version}-macos-{arch}'
        dmg = output / f'{name}.dmg'
        run(['hdiutil', 'create', '-volname', 'MH', '-srcfolder', image_root,
             '-format', 'UDZO', '-fs', 'HFS+', dmg], env)
        run(['hdiutil', 'verify', dmg], env)
        source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        modified = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
        manifest = {
            'brand': 'MH', 'version': version, 'platform': 'macos', 'arch': arch,
            'minimum_macos': '12.3', 'controller_only': True,
            'server_configured': profile is not None,
            'signature': 'ad-hoc', 'notarized': False,
            'source_commit': source_commit, 'source_modified': modified,
            'built_at_utc': datetime.now(timezone.utc).isoformat(),
            'features': FEATURES.split(','),
            'files': {p.relative_to(bundled).as_posix(): digest(p)
                      for p in sorted(bundled.rglob('*')) if p.is_file()},
        }
        manifest_path = output / 'build-manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        checksums = {p.name: digest(p) for p in (dmg, manifest_path)}
        (output / f'{name}-sha256.json').write_text(json.dumps(checksums, indent=2) + '\n')
        destination.parent.mkdir(parents=True, exist_ok=True)
        output.rename(destination)
    print(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--controller-profile', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        parser.error('Build on macOS with Xcode installed')
    arch = platform.machine()
    destination = release_dir('macos', args.version, arch)
    if destination.exists():
        raise FileExistsError(f'Release already exists: {destination}')
    profile = validate(args.controller_profile) if args.controller_profile else None
    env = environment(arch, profile)
    for tool in ('cargo', 'flutter', 'pod', 'cmake', 'ninja', 'pkg-config', 'nasm'):
        if not shutil.which(tool, path=env['PATH']):
            raise RuntimeError(f'Missing {tool}; run tools/macos/prepare-macos.sh first')
    run([sys.executable, ROOT / 'tools/macos/prepare-bridge.py'], env)
    prepare_icon(env)
    run(['cargo', 'build', '--locked', '--release', '--features', FEATURES, '--lib', '--bin', 'service'], env)
    run(flutter_build_args(profile), env, ROOT / 'flutter')
    package(args.version, arch, profile, env)


if __name__ == '__main__':
    main()
