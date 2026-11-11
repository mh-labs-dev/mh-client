"""Restore the official native bridge and align it to the pinned 1.5.1 API.

Input is the unmodified bridge-artifact from rustdesk/rustdesk run 42735021293,
artifact 13725909613 (commit 1fbb7f7b436a05e38bbfe8720ab8d81c91b50a51).
That revision adds only login_method to the exported session_add_sync API.
The pinned source predates it. No bridge generator is invoked.
"""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT
ARCHIVE = Path(__file__).with_name('bridge') / 'bridge-upstream.zip'
EXPECTED = '15cb37d5b94554f1d5b965eae99de33219b5864b9aa633dbd65e53322eab9221'


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError(f'Unexpected bridge content: {old!r}')
    return text.replace(old, new)


def main():
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != EXPECTED:
        raise ValueError('Official bridge archive checksum mismatch')
    api = (SOURCE / 'src/flutter_ffi.rs').read_text(encoding='utf-8')
    api_digest = hashlib.sha256(api.replace('\r\n', '\n').encode()).hexdigest()
    if api_digest != '400191f6761117e67562a68bb02cf0adb834e8e01134cbfc47ed0b634fa9d607':
        raise ValueError('The pinned Flutter FFI source changed; review the bridge before rebuilding')
    signature = api.split('pub fn session_add_sync(', 1)[1].split(') ->', 1)[0]
    if 'login_method' in signature or 'conn_token: Option<String>' not in signature:
        raise ValueError('This bridge adapter is only for the pinned 1.5.1 API')
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in ('src/bridge_generated.rs', 'src/bridge_generated.io.rs',
                     'flutter/lib/generated_bridge.dart',
                     'flutter/lib/generated_bridge.freezed.dart'):
            text = archive.read(name).decode('utf-8').replace('\r\n', '\n')
            if name.endswith('.rs'):
                text = ''.join(line for line in text.splitlines(keepends=True)
                               if 'login_method' not in line)
            elif name.endswith('generated_bridge.dart'):
                text = ''.join(line for line in text.splitlines(keepends=True)
                               if 'loginMethod' not in line and 'login_method' not in line)
                text = replace(text, 'arg10, arg11, arg12),', 'arg10, arg11),')
                text = replace(text,
                    '              ffi.Pointer<wire_uint_8_list>,\n'
                    "              ffi.Pointer<wire_uint_8_list>)>>('wire_session_add_sync');",
                    "              ffi.Pointer<wire_uint_8_list>)>>('wire_session_add_sync');")
                start = text.index('  late final _wire_session_add_sync =')
                end = text.index('  void wire_session_start(', start)
                section = replace(text[start:end],
                    '          ffi.Pointer<wire_uint_8_list>,\n'
                    '          ffi.Pointer<wire_uint_8_list>)>();',
                    '          ffi.Pointer<wire_uint_8_list>)>();')
                text = text[:start] + section + text[end:]
            (SOURCE / name).write_text(text, encoding='utf-8', newline='\n')
            print(f'Restored {name}')


if __name__ == '__main__':
    main()
