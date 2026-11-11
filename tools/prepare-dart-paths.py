"""Give Flutter's generated plugin registry a portable package URI."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / 'flutter/.dart_tool/package_config.json'
    config = json.loads(path.read_text('utf-8'))
    owner = next(package for package in config['packages'] if package['name'] == 'flutter_hbb')
    name = 'mh_generated_build'
    config['packages'] = [package for package in config['packages'] if package['name'] != name]
    config['packages'].append({
        'name': name, 'rootUri': 'flutter_build', 'packageUri': '',
        'languageVersion': owner['languageVersion'],
    })
    path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    print('Generated Dart sources use package URIs.')


if __name__ == '__main__':
    main()
