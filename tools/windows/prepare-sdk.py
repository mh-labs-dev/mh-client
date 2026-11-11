"""Apply the upstream engine/filter fix and select VS 2022 for Flutter 3.24."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.cache/mh-tools'
FLUTTER = TOOLS / 'flutter'
ENGINE_HASH = 'ec8cabf36ee4ff24c8d98de25b00e70781eb03876265aee84d0fe554a110036e'


def main():
    archive = TOOLS / 'windows-x64-release.zip'
    if not archive.exists():
        urllib.request.urlretrieve(
            'https://github.com/rustdesk/engine/releases/download/main/windows-x64-release.zip', archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ENGINE_HASH:
        raise ValueError('Engine archive changed; review the upstream version before building')
    destination = FLUTTER / 'bin/cache/artifacts/engine/windows-x64-release'
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if '/' in member.filename or '\\' in member.filename:
                raise ValueError('Unexpected engine archive layout')
            with bundle.open(member) as src, (destination / member.filename).open('wb') as out:
                shutil.copyfileobj(src, out)
    patch = ROOT / '.github/patches/flutter_3.24.4_dropdown_menu_enableFilter.diff'
    if subprocess.run(['git', '-C', str(FLUTTER), 'apply', '--reverse', '--check', str(patch)],
                      capture_output=True).returncode != 0:
        subprocess.run(['git', '-C', str(FLUTTER), 'apply', str(patch)], check=True)
    vs = FLUTTER / 'packages/flutter_tools/lib/src/windows/visual_studio.dart'
    text = vs.read_text(encoding='utf-8')
    old = '_minimumSupportedVersion.toString(),'
    new = "'[17,18)',"
    original = text
    if old in text:
        if text.count(old) != 1:
            raise ValueError('Unexpected Flutter Visual Studio discovery code')
        text = text.replace(old, new)
    elif new not in text:
        raise ValueError('Unsupported Flutter SDK')
    if 'final String? mhCmake' not in text:
        text = text.replace('String? get cmakePath {', '''String? get cmakePath {
    final String? mhCmake = _platform.environment['MH_CMAKE_PATH'];
    if (mhCmake != null && _fileSystem.file(mhCmake).existsSync()) {
      return mhCmake;
    }''')
        text = text.replace(
            "      'Microsoft.VisualStudio.Component.VC.CMake.Project': 'C++ CMake tools for Windows',",
            "      if (!_platform.environment.containsKey('MH_CMAKE_PATH'))\n"
            "        'Microsoft.VisualStudio.Component.VC.CMake.Project': 'C++ CMake tools for Windows',")
        text = text.replace('''            if (requiredWorkload != null) ...<String>[
              '-requires',
              requiredWorkload,
            ],''', '''            '-requires',
            if (requiredWorkload != null &&
                !_platform.environment.containsKey('MH_CMAKE_PATH'))
              requiredWorkload,''')
    if text != original:
        vs.write_text(text, encoding='utf-8', newline='\n')
        # Flutter's launcher rebuilds its own cached tool after its stamp is removed.
        (FLUTTER / 'bin/cache/flutter_tools.stamp').unlink(missing_ok=True)
    print('Prepared the pinned Windows engine, dropdown fix and VS 2022 selection.')


if __name__ == '__main__':
    main()
