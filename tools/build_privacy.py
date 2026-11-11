"""Remap build paths and reject host-specific paths in distributed files."""
import argparse
import json
import os
from pathlib import Path
import re
import platform
import tomllib

ROOT = Path(__file__).resolve().parents[1]
# This literal belongs to the pinned upstream cursor plugin, not a build machine.
UPSTREAM_CURSOR_EXAMPLE = r"C:\Users\kingtous\Desktop\mouse.png"
HOME_PATH = re.compile(rb"(?:[A-Za-z]:[/\\]Users[/\\]|/(?:Users|home)/)[A-Za-z0-9_.-]+[/\\]")


def variants(path):
    value = str(path).rstrip("/\\")
    return sorted({value, value.replace("\\", "/"), value.replace("/", "\\")})


def environment_updates(env, root=ROOT, home=None, target=None):
    home = Path.home() if home is None else home
    target = target or platform.system().lower()
    mappings = [(home, "./build-home"), (root, "./mh")]
    for key, destination in (("CARGO_HOME", "./dependencies/cargo"),
                             ("RUSTUP_HOME", "./dependencies/rust")):
        if env.get(key):
            mappings.append((env[key], destination))
    encoded = env.get("CARGO_ENCODED_RUSTFLAGS")
    if encoded:
        flags = encoded.split("\x1f")
    elif env.get("RUSTFLAGS"):
        flags = env["RUSTFLAGS"].split()
    else:
        settings = tomllib.loads((ROOT / '.cargo/config.toml').read_text('utf-8'))
        target = target or platform.system().lower()
        key = env.get('CARGO_BUILD_TARGET', 'x86_64-pc-windows-msvc') if target == 'windows' else 'cfg(target_os="macos")'
        flags = list(settings.get('target', {}).get(key, {}).get('rustflags', []))
    for source, destination in mappings:
        for prefix in variants(source):
            flag = f"--remap-path-prefix={prefix}={destination}"
            if flag not in flags:
                flags.append(flag)
    updates = {"CARGO_ENCODED_RUSTFLAGS": "\x1f".join(flags)}
    if target == 'windows':
        # Verified with the pinned MSVC compiler; the package scan checks the result.
        native_flags = '/d1trimfile:' + str(root).rstrip('/\\') + '\\'
    else:
        native_flags = ' '.join(f'-ffile-prefix-map={source}={destination}'
                                for source, destination in mappings)
    for key in ('CFLAGS', 'CXXFLAGS'):
        previous = env.get(key, '')
        updates[key] = previous if native_flags in previous else (previous + ' ' + native_flags).strip()
    return updates


def inspect_bytes(data, root=ROOT, home=None):
    home = Path.home() if home is None else home
    data = data.replace(UPSTREAM_CURSOR_EXAMPLE.encode(), b"upstream-cursor-example")
    data = data.replace(UPSTREAM_CURSOR_EXAMPLE.encode("utf-16le"), b"upstream-cursor-example")
    findings = set()
    for encoding in ("utf-8", "utf-16le"):
        for path in (root, home):
            for prefix in variants(path):
                # Require a separator so /home/build does not match /home/builder.
                for separator in ("/", "\\"):
                    if (prefix + separator).encode(encoding).lower() in data.lower():
                        findings.add("local build root")
    if HOME_PATH.search(data) or HOME_PATH.search(data[::2]) or HOME_PATH.search(data[1::2]):
        findings.add("user home path")
    return sorted(findings)


def check_tree(directory, root=ROOT, home=None, exclude_suffixes=()):
    directory = Path(directory)
    findings = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix in exclude_suffixes:
            continue
        for label in inspect_bytes(path.read_bytes(), root, home):
            findings.append({"file": path.relative_to(directory).as_posix(), "rule": label})
    if findings:
        raise ValueError("Build privacy check failed: " + json.dumps(findings))
    return {"build_path_check": "passed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("environment", "check"))
    parser.add_argument("directory", nargs="?", type=Path)
    args = parser.parse_args()
    if args.action == "environment":
        print(json.dumps(environment_updates(os.environ)))
    else:
        if args.directory is None or not args.directory.is_dir():
            parser.error("check requires an application directory")
        print(json.dumps(check_tree(args.directory)))


if __name__ == "__main__":
    main()
