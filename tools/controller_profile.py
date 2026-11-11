"""Validate public build configuration; never contacts a server."""
import argparse
import base64
import json
from pathlib import Path
from urllib.parse import urlparse
KEYS = {'custom-rendezvous-server', 'relay-server', 'api-server', 'key',
        'allow-websocket', 'allow-insecure-tls-fallback'}


def validate(path):
    profile = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if set(profile) != KEYS or any(not isinstance(v, str) for v in profile.values()):
        raise ValueError('Only the six public connection settings are allowed')
    url = urlparse(profile['api-server'])
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment or url.port):
        raise ValueError('Expected an HTTPS origin')
    if any(profile[k] != url.hostname for k in ('custom-rendezvous-server', 'relay-server')):
        raise ValueError('ID and relay must match the API host')
    if len(base64.b64decode(profile['key'], validate=True)) != 32:
        raise ValueError('Expected a 32-byte public key')
    if profile['allow-websocket'] != 'Y' or profile['allow-insecure-tls-fallback'] != 'N':
        raise ValueError('Secure WebSocket is required')
    return profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['validate'])
    parser.add_argument('path')
    args = parser.parse_args()
    validate(args.path)
    print('Public controller profile validated.')


if __name__ == '__main__':
    main()
