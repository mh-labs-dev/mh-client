"""Restore the pinned desktop bridge, including the macOS Swift C header."""
from pathlib import Path
import re
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    # Reuse the archive digest and Rust API checks already used by Windows.
    runpy.run_path(str(ROOT / 'tools/windows/prepare-bridge.py'), run_name='__main__')
    with zipfile.ZipFile(ROOT / 'tools/windows/bridge/bridge-upstream.zip') as archive:
        name = 'flutter/macos/Runner/bridge_generated.h'
        text = archive.read(name).decode().replace('\r\n', '\n')
    # Match the pinned API: session_add_sync predates the login_method argument.
    text, count = re.subn(r',\n\s*struct wire_uint_8_list \*login_method\);', ');', text)
    if count != 1:
        raise ValueError('Unexpected macOS bridge header signature')
    (ROOT / name).write_text(text)
    print(f'Restored {name}')


if __name__ == '__main__':
    main()
