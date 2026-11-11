"""Check standalone build inputs and locally archived release checksums."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, encoding='utf-8').strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    def check(ok, description):
        if not ok:
            errors.append(description)

    pins = json.loads((ROOT / 'upstream.json').read_text(encoding='utf-8'))
    check(git('rev-parse', 'HEAD:libs/hbb_common') == pins['hbb_common_commit'], 'Submodule pin differs from upstream.json')
    check(git('rev-parse', 'HEAD', cwd=ROOT / 'libs/hbb_common') == pins['hbb_common_commit'], 'Submodule checkout differs from its pin')
    check(not (ROOT / '.git/objects/info/alternates').exists(), 'Git objects depend on another local repository')
    check(not (ROOT / 'libs/hbb_common/.git/objects/info/alternates').exists(), 'Submodule objects depend on another local repository')
    check(sha(ROOT / 'tools/windows/bridge/bridge-upstream.zip') ==
          '15cb37d5b94554f1d5b965eae99de33219b5864b9aa633dbd65e53322eab9221', 'Bridge input checksum mismatch')
    for path in ('.local/probe.json', '.cache/probe', 'dist/probe.exe', 'PROGRESS.md', 'AGENTS.md', 'CLAUDE.md', 'GEMINI.md', '.codex/probe', 'docs/development/probe.md', 'target/probe', 'release/windows/test/x64/probe.zip', 'release/macos/test/arm64/MH.app/probe', 'release/ios/test/arm64/probe.ipa', 'release/android/test/universal/probe.apk'):
        check(subprocess.run(['git', 'check-ignore', '-q', path], cwd=ROOT).returncode == 0, f'Local path is not ignored: {path}')
    visible = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0'))
    for path in visible:
        check(not path.startswith(('.local/', '.cache/', 'dist/', 'target/')), f'Local output visible to Git: {path}')
    required = ['README.md', 'docs/user/en/README.md', 'LICENCE', 'upstream.json',
                'branding/mh-icon.png', 'config/controller.example.json',
                'tools/windows/bridge/bridge-upstream.zip', 'tools/windows/build-windows.ps1',
                'tools/windows/package-windows.ps1']
    required += [f'docs/user/{lang}/USAGE.md' for lang in ('zh-CN', 'en')]
    for name in required:
        check(name in visible and (ROOT / name).is_file(), f'Missing or ignored distribution input: {name}')
    shared = [ROOT / name for name in required if name.endswith(('.md', '.json'))]
    shared += list((ROOT / 'tools/windows').glob('*.py')) + list((ROOT / 'tools/windows').glob('*.ps1'))
    shared += list((ROOT / 'docs/user/releases').glob('*.md'))
    private_patterns = [r'https?://[\w-]+\.trycloudflare\.com',
                        r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
                        r'(?i)\b[A-Z]:[\\/](?:Users|mac-rental|mh-client)[\\/]']
    for file in shared:
        content = file.read_text(encoding='utf-8-sig')
        rel = file.relative_to(ROOT)
        check(not any(re.search(pattern, content) for pattern in private_patterns), f'Private local data in shared file: {rel}')
        if file.suffix in ('.py', '.ps1'):
            check(not re.search(r'mac-rental|projects/rustdesk-client|deploy/client', content), f'Old project path dependency: {rel}')
        if file.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', content):
                if '://' in link or link.startswith('#'):
                    continue
                check((file.parent / link.split('#')[0]).exists(), f'Broken document link: {rel} -> {link}')
    release_files = 0
    manifests = list((ROOT / 'dist').glob('*/*-sha256.json'))
    manifests += list((ROOT / 'release').glob('*/*/*/*-sha256.json'))
    for manifest in manifests:
        checksums = json.loads(manifest.read_text(encoding='utf-8'))
        for name, expected in checksums.items():
            path = manifest.parent / name
            check(path.is_file() and sha(path) == expected, f'Release checksum mismatch: {name}')
            if path.is_file() and path.suffix == '.zip':
                with zipfile.ZipFile(path) as archive:
                    check(archive.testzip() is None, f'Corrupt release archive: {name}')
            release_files += 1
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'standalone_inputs': 'passed', 'document_links': 'passed',
                      'release_files_verified': release_files}, indent=2))


if __name__ == '__main__':
    main()
