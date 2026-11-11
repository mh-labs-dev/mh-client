"""Move flat build outputs into version directories without replacing files."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = (ROOT / 'dist').resolve()
RECORD = ROOT / '.local/client-tests/package-layout-migration.json'
PATTERN = re.compile(r'MH-([A-Za-z0-9][A-Za-z0-9.-]*)-windows-x64(?:(-source|-sha256)?\.(exe|zip|json))?')


def checked(path):
    resolved = path.resolve()
    if resolved == PACKAGES or not resolved.is_relative_to(PACKAGES):
        raise ValueError('Package move must stay inside dist')
    return path


def hashes(path):
    checked(path)
    files = sorted(path.rglob('*')) if path.is_dir() else [path]
    return {str(p.relative_to(path)) if path.is_dir() else '.':
            hashlib.sha256(checked(p).read_bytes()).hexdigest()
            for p in files if p.is_file()}


def save(plan):
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    temporary = RECORD.with_suffix('.tmp')
    temporary.write_text(json.dumps(plan, indent=2), encoding='utf-8')
    temporary.replace(RECORD)


def main(apply):
    if RECORD.exists():
        plan = json.loads(RECORD.read_text(encoding='utf-8'))
    else:
        plan = []
        for source in sorted(PACKAGES.iterdir()):
            match = PATTERN.fullmatch(source.name)
            if not match:
                continue
            version = match[1]
            target = PACKAGES / version / ('unpacked' if source.is_dir() else source.name)
            checked(source)
            checked(target)
            if target.exists():
                raise FileExistsError('Version destination already exists; refusing to merge')
            plan.append({'source': str(source), 'target': str(target), 'hashes': hashes(source), 'moved': False})
        if apply:
            save(plan)
    for item in plan:
        source, target = checked(Path(item['source'])), checked(Path(item['target']))
        if not apply:
            print(f'{source.name} -> {target.relative_to(PACKAGES)}')
            continue
        if source.exists():
            if target.exists():
                raise FileExistsError('Both old and new paths exist; no files replaced')
            if hashes(source) != item['hashes']:
                raise RuntimeError('Source changed after planning; no move performed')
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
        if not target.exists() or hashes(target) != item['hashes']:
            raise RuntimeError('Moved output failed integrity verification')
        item['moved'] = True
        save(plan)
    if apply:
        print(f'Organized {len(plan)} outputs; every file hash preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
