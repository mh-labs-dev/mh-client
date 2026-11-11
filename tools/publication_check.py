"""Inspect the Git index, working files, or an explicit release source ZIP.

Only paths and rule names are reported; matching content is never printed.
This is a deterministic publication guard, not an exhaustive secret detector.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DIRS = {'.local', '.cache', 'target', 'dist', '__pycache__', '.venv', '.agents', '.codex', '.claude', '.gemini', '.cursor', '.windsurf'}
LOCAL_NAMES = {'agents.md', 'agents.local.md', 'claude.md', 'claude.local.md', 'gemini.md', '.cursorrules', '.windsurfrules', 'copilot-instructions.md', 'progress.md', 'controller-profile.json', 'devices.json', 'credentials.json', 'secrets.json'}
PRIVATE_SUFFIXES = {'.pfx', '.p12', '.keystore', '.sqlite', '.sqlite3', '.log'}
BUILD_SUFFIXES = {'.exe', '.dll', '.pdb', '.msi', '.dmg', '.apk', '.ipa'}
ARCHIVE_SUFFIXES = {'.zip', '.7z', '.gz', '.tgz', '.tar'}
DOC_SUFFIXES = {'.md', '.txt', '.json', '.toml', '.yaml', '.yml', '.env'}
PATTERNS = {
    'private key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'access token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{20,})\b'),
    'temporary tunnel address': re.compile(rb'(?i)\b[a-z0-9-]+\.trycloudflare\.com\b'),
    'credential in URL': re.compile(rb'''(?i)https?://([^\s/:@"']+):([^\s/@"']+)@([a-z0-9.-]+)'''),
}
DOC_PATTERNS = {
    'local machine path': re.compile(rb'(?i)(?:\b[A-Z]:[\\/]+(?:Users|mac-rental|mh-client)[\\/]+|/(?:Users|home)/[a-z0-9_.-]+/)'),
    'private network address': re.compile(rb'(?<![\d.])(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?![\d.])'),
}
ASSIGNMENT = re.compile(rb'''(?im)(?:^|[,{])\s*["']?(?:password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret|license[_-]?key|secret|token)["']?\s*[:=]\s*(?:"([^"\r\n]+)"|'([^'\r\n]+)'|([^\s,#\r\n]+))''')
PLACEHOLDER = re.compile(rb'(?i)^(?:<[^>]+>|\$\{[^}]+\}|example|placeholder|change[_-]?me|your[_-].*|test|dummy|REDACTED)$')


def git(root, *args, input=None):
    result = subprocess.run(['git', '-C', str(root), *args], input=input,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Git inspection failed; initialize required submodules and resolve index conflicts')
    return result.stdout


def exceptions(root):
    # Two exact, documented upstream inputs; a changed blob loses its exception.
    return json.loads((root/'tools/publication-exceptions.json').read_text(encoding='utf-8'))


def rules_for(path, data, approved, artifact=False):
    normalized = path.replace('\\', '/')
    parts = PurePosixPath(normalized).parts
    name = parts[-1].lower() if parts else ''
    suffix = PurePosixPath(name).suffix
    rules = []
    if (any(p.lower() in LOCAL_DIRS or p.lower() == '.git' for p in parts) or name in LOCAL_NAMES
            or normalized.lower().startswith(('.github/instructions/', 'docs/development/', 'docs/upstream/')) or '/.github/instructions/' in normalized.lower()
            or suffix in PRIVATE_SUFFIXES or name in ('id_rsa', 'id_ed25519')
            or ((name.startswith('.env') or suffix == '.env')
                and not name.endswith(('.example', '.sample', '.template', '.example.env'))
                and name not in ('example.env', 'sample.env'))
            or (suffix in DOC_SUFFIXES and any(word in name for word in ('credentials', 'secrets', '账号与密码', '密码本')))):
        rules.append('local/private file')
    entry = approved.get(normalized)
    if artifact and not entry:
        entry = next((value for name, value in approved.items() if normalized.endswith('/'+name)), None)
    approved_blob = bool(entry and hashlib.sha256(data.replace(b'\r\n', b'\n') if entry.get('normalize_lf') else data).hexdigest() == entry['sha256'])
    if suffix in BUILD_SUFFIXES:
        rules.append('compiled binary requires separate release review')
    if suffix in ARCHIVE_SUFFIXES and not approved_blob:
        rules.append('archive requires separate release review')
    for label, pattern in PATTERNS.items():
        if label == 'private key' and approved_blob and entry.get('rule') == label:
            continue
        if label == 'credential in URL':
            sample_pairs = {(b'user', b'pass'), (b'user', b'password'), (b'123', b'123')}
            if any(m[3].lower() != b'example.com' or (m[1], m[2]) not in sample_pairs for m in pattern.finditer(data)):
                rules.append(label)
        elif pattern.search(data):
            rules.append(label)
    if suffix in DOC_SUFFIXES:
        for label, pattern in DOC_PATTERNS.items():
            inspected = data
            if label == 'local machine path':
                # Upstream container examples use this fixed container home, not a host user's path.
                inspected = b'\n'.join(line.replace(b'/home/user/', b'/container-home/')
                    if b'docker run ' in line and b'-v $PWD:/home/user/rustdesk' in line and b'rustdesk-builder' in line
                    else line for line in data.splitlines())
            if pattern.search(inspected):
                rules.append(label)
        values = [next(v for v in m.groups() if v is not None) for m in ASSIGNMENT.finditer(data)]
        if any(not (PLACEHOLDER.fullmatch(value) or value.startswith(b'${{')
                    or value.rstrip(b'}]').lower() in (b'null', b'none', b'true', b'false'))
               for value in values):
            rules.append('literal credential field')
    return sorted(set(rules))


def blobs(root, records):
    ids = sorted({oid for mode, oid, name in records if mode != '160000'})
    if not ids:
        return {}
    stream = io.BytesIO(git(root, 'cat-file', '--batch', input=('\n'.join(ids)+'\n').encode()))
    result = {}
    for oid in ids:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b'blob':
            raise RuntimeError('Unavailable staged blob')
        size = int(header[2])
        result[oid] = stream.read(size)
        if stream.read(1) != b'\n':
            raise RuntimeError('Invalid Git blob response')
    return result


def indexed_files(root, prefix='', revision=None):
    records = []
    command = ('ls-tree', '-r', '-z', revision) if revision else ('ls-files', '--stage', '-z')
    for raw in git(root, *command).split(b'\0'):
        if not raw:
            continue
        metadata, name = raw.split(b'\t', 1)
        a, b, c = metadata.decode().split()
        if revision:
            mode, oid = a, c
        else:
            mode, oid = a, b
            if c != '0':
                raise RuntimeError('Resolve unmerged index entries before checking')
        records.append((mode, oid, name.decode('utf-8')))
    contents = blobs(root, records)
    for mode, oid, name in records:
        full = prefix + name
        if mode == '160000':
            child = root/name
            if not child.is_dir() or child.is_symlink():
                raise RuntimeError('A staged submodule is unavailable')
            yield from indexed_files(child, full+'/', oid)
        else:
            yield full, contents[oid], mode


def working_files(root, prefix=''):
    links = {}
    for raw in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if raw:
            meta, name = raw.split(b'\t', 1)
            if meta.startswith(b'160000 '):
                links[name.decode()] = True
    names = set(git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0'))
    for raw in sorted(names):
        if not raw:
            continue
        name = raw.decode('utf-8'); path = root/name
        if name in links:
            if not path.is_dir():
                raise RuntimeError('Initialize the submodule before checking')
            yield from working_files(path, prefix+name+'/')
        elif path.is_symlink():
            yield prefix+name, b'', '120000'
        elif path.is_file():
            yield prefix+name, path.read_bytes(), '100644'


def archive_files(path):
    with zipfile.ZipFile(path) as archive:
        if sum(x.file_size for x in archive.infolist()) > 512*1024*1024:
            raise RuntimeError('Archive exceeds the review size limit')
        for member in archive.infolist():
            if member.is_dir():
                continue
            name = member.filename.replace('\\', '/')
            if name.startswith('/') or '..' in PurePosixPath(name).parts or re.match(r'^[A-Za-z]:', name):
                raise RuntimeError('Unsafe archive member path')
            yield name, archive.read(member), '100644'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--staged', action='store_true', help='Check the whole proposed index, including pinned submodule blobs (default)')
    group.add_argument('--working-tree', action='store_true', help='Include visible untracked and working files')
    group.add_argument('--source-archive', type=Path, help='Review a release source ZIP separately; never modifies it')
    args = parser.parse_args(argv)
    approved = exceptions(ROOT)
    try:
        files = archive_files(args.source_archive) if args.source_archive else working_files(ROOT) if args.working_tree else indexed_files(ROOT)
        problems = []; count = 0
        for name, data, mode in files:
            count += 1
            violations = ['symbolic link requires manual review'] if mode == '120000' else rules_for(name, data, approved, bool(args.source_archive))
            problems.extend((name, label) for label in violations)
        if problems:
            print('Publication check blocked:')
            for name, label in problems:
                print(f'  {json.dumps(name, ensure_ascii=True)}: {label}')
            print('Keep private data outside Git. Review the staged version, not only the working file.')
            return 1
        print(f'Publication check passed: {count} files. Pattern checks do not replace manual review.')
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile):
        print('Publication check could not complete; inspect repository/submodule/archive availability.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
