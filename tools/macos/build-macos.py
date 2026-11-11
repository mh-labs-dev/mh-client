"""Build and package an ad-hoc-signed MH macOS test app on the host architecture."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
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
        'VCPKG_DEFAULT_HOST_TRIPLET': 'arm64-osx' if arch == 'arm64' else 'x64-osx',
        'VCPKG_OVERLAY_TRIPLETS': str(ROOT / 'tools/macos/triplets'),
        'VCPKG_MAX_CONCURRENCY': '8',
        'VCPKG_BINARY_SOURCES': f'clear;files,{TOOLS / "vcpkg-binary-cache"},readwrite',
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
    # Keep build-machine identities out of Rust panic locations and native code.
    # Encoded flags preserve paths containing spaces and any caller-supplied flags.
    rustflags = (list(filter(None, env.get('CARGO_ENCODED_RUSTFLAGS', '').split('\x1f')))
                 if 'CARGO_ENCODED_RUSTFLAGS' in env else shlex.split(env.get('RUSTFLAGS', '')))
    mappings = [(Path.home(), '/build/user-root'), (ROOT, '/build/mh-client')]
    rustflags.extend(f'--remap-path-prefix={source}={target}' for source, target in mappings)
    env['CARGO_ENCODED_RUSTFLAGS'] = '\x1f'.join(rustflags)
    env.pop('RUSTFLAGS', None)
    native_flags = [f'-ffile-prefix-map={source}={target}' for source, target in mappings]
    for key in ('CFLAGS', 'CXXFLAGS'):
        env[key] = shlex.join(shlex.split(env.get(key, '')) + native_flags)
    for key in ('OTHER_CFLAGS', 'OTHER_CPLUSPLUSFLAGS'):
        env[f'FLUTTER_XCODE_{key}'] = '$(inherited) ' + shlex.join(native_flags)
    swift_flags = [arg for source, target in reversed(mappings)
                   for arg in ('-file-prefix-map', f'{source}={target}',
                               '-debug-prefix-map', f'{source}={target}')]
    env['FLUTTER_XCODE_OTHER_SWIFT_FLAGS'] = '$(inherited) ' + shlex.join(swift_flags)
    if profile is not None:
        env['MH_CONTROLLER_PROFILE'] = json.dumps(profile)
    return env


def flutter_build_args(profile):
    return ['flutter', 'build', 'macos', '--release', '--no-pub', '--dart-define=MH_DESKTOP=true',
            f'--split-debug-info={ROOT / ".local/macos-symbols"}',
            '--dart-define=MH_CONTROLLER=true',
            f'--dart-define=MH_CONTROLLER_CONFIGURED={str(profile is not None).lower()}']


def register_generated_dart_package():
    # Flutter 3.24 embeds the registrant URI for runtime plugin lookup even when
    # debug info is split out. Give that generated library a stable package URI,
    # instead of changing the binary string or obfuscating application code.
    config_path = ROOT / 'flutter/.dart_tool/package_config.json'
    config = json.loads(config_path.read_text())
    name = 'mh_build_generated'
    config['packages'] = [p for p in config['packages'] if p['name'] != name]
    config['packages'].append({'name': name, 'rootUri': 'flutter_build/',
                               'packageUri': '', 'languageVersion': '3.0'})
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    # Flutter 3.24's kernel stamp does not track the package-config mapping.
    # Invalidate that generated cache so an earlier file URI is not reused.
    for stamp in (config_path.parent / 'flutter_build').glob('*/kernel_snapshot*.stamp'):
        stamp.unlink()
    # Xcode's outer script phase has its own cache. Its declared input must also
    # change, otherwise it never invokes Flutter to notice the missing stamp.
    tripwire = ROOT / 'flutter/macos/Flutter/ephemeral/tripwire'
    tripwire.parent.mkdir(parents=True, exist_ok=True)
    tripwire.touch()


def strip_build_symbols(app, env):
    for path in sorted(app.rglob('*')):
        if path.is_file() and not path.is_symlink():
            kind = subprocess.check_output(['file', '-b', str(path)], text=True)
            if 'Mach-O' in kind:
                # Retain exported symbols used by Flutter FFI and plugin loading.
                run(['xcrun', 'strip', '-S', '-x', path], env)


def verify_build_privacy(app):
    """Fail before packaging if a personal build path remains, including in binaries."""
    personal_path = re.compile(rb'(?i)(?:/(?:Users|home)/[^/\x00\r\n ]+/|[A-Z]:[\\/]+Users[\\/]+[^\\/\x00\r\n ]+[\\/])')
    leaked = []
    for path in sorted(app.rglob('*')):
        if path.is_symlink():
            if os.path.isabs(os.readlink(path)):
                leaked.append(path.relative_to(app).as_posix() + ' (absolute symlink)')
        elif path.is_file():
            data = path.read_bytes()
            # UTF-16 strings can also appear in native resources.
            if personal_path.search(data) or personal_path.search(data.replace(b'\x00', b'')):
                leaked.append(path.relative_to(app).as_posix())
    if leaked:
        raise RuntimeError('Personal build paths remain in: ' + ', '.join(leaked))


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
        strip_build_symbols(bundled, env)
        sign_local_app(bundled, env)
        verify_build_privacy(bundled)
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
    # Refresh dependency ABIs when macOS privacy flags change, including on an
    # existing checkout that was originally prepared without path remapping.
    (TOOLS / 'vcpkg-binary-cache').mkdir(exist_ok=True)
    run([TOOLS / 'vcpkg/vcpkg', 'install', '--triplet', env['VCPKG_DEFAULT_TRIPLET'],
         '--host-triplet', env['VCPKG_DEFAULT_HOST_TRIPLET'],
         f'--x-install-root={TOOLS / "vcpkg/installed"}'], env)
    native_status = digest(TOOLS / 'vcpkg/installed/vcpkg/status')
    native_marker = ROOT / 'target/mh-macos-vcpkg.sha256'
    if not native_marker.exists() or native_marker.read_text().strip() != native_status:
        # These Rust crates embed vcpkg archives in their rlibs. Cargo does not
        # reliably notice replacement of external static libraries by itself.
        run(['cargo', 'clean', '--release', '-p', 'scrap', '-p', 'hwcodec',
             '-p', 'magnum-opus', '-p', 'rustdesk'], env)
        native_marker.parent.mkdir(exist_ok=True)
        native_marker.write_text(native_status + '\n')
    run(['cargo', 'build', '--locked', '--release', '--features', FEATURES, '--lib', '--bin', 'service'], env)
    run(['flutter', 'pub', 'get'], env, ROOT / 'flutter')
    register_generated_dart_package()
    run(flutter_build_args(profile), env, ROOT / 'flutter')
    package(args.version, arch, profile, env)


if __name__ == '__main__':
    main()
