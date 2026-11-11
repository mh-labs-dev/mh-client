import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('macos_build', TOOLS / 'macos/build-macos.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class MacControllerBuildTests(unittest.TestCase):
    def test_registrant_mapping_invalidates_both_flutter_and_xcode_caches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dart_tool = root / 'flutter/.dart_tool'
            cache = dart_tool / 'flutter_build/previous-build'
            cache.mkdir(parents=True)
            (dart_tool / 'package_config.json').write_text(json.dumps({'packages': []}))
            for name in ('kernel_snapshot', 'kernel_snapshot_program', 'kernel_snapshot_native_assets'):
                (cache / f'{name}.stamp').write_text('old absolute URI')
            with patch.object(build, 'ROOT', root):
                build.register_generated_dart_package()
            self.assertEqual(list(cache.glob('*.stamp')), [])
            self.assertTrue((root / 'flutter/macos/Flutter/ephemeral/tripwire').exists())

    def test_privacy_check_rejects_binary_and_utf16_personal_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'native-library'
            for text in ('/Users/private-builder/source/file.rs',
                         '/home/private-builder/source/file.rs',
                         'C:\\Users\\private-builder\\source\\file.rs'):
                for encoding in ('utf-8', 'utf-16-le'):
                    binary.write_bytes(b'\x00\xff' + text.encode(encoding) + b'\x00')
                    with self.assertRaises(RuntimeError) as failure:
                        build.verify_build_privacy(root)
                    self.assertNotIn('private-builder', str(failure.exception))
            binary.write_bytes(b'/build/mh-client/src/file.rs\x00/System/Library/Frameworks')
            build.verify_build_privacy(root)

    def test_privacy_check_rejects_external_absolute_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'external').symlink_to('/tmp/unbundled-dependency')
            with self.assertRaises(RuntimeError):
                build.verify_build_privacy(root)

    def test_missing_profile_does_not_create_a_host_client(self):
        env = build.environment('arm64', None)
        self.assertEqual(env['MH_CONTROLLER'], 'true')
        self.assertNotIn('MH_CONTROLLER_PROFILE', env)
        flags = build.flutter_build_args(None)
        self.assertIn('--dart-define=MH_CONTROLLER=true', flags)
        self.assertIn('--dart-define=MH_CONTROLLER_CONFIGURED=false', flags)

    def test_profile_enables_login_without_changing_product_mode(self):
        profile = json.loads((TOOLS.parent / 'config/controller.example.json').read_text())
        env = build.environment('arm64', profile)
        self.assertEqual(env['MH_CONTROLLER'], 'true')
        self.assertEqual(json.loads(env['MH_CONTROLLER_PROFILE']), profile)
        flags = build.flutter_build_args(profile)
        self.assertIn('--dart-define=MH_CONTROLLER=true', flags)
        self.assertIn('--dart-define=MH_CONTROLLER_CONFIGURED=true', flags)


if __name__ == '__main__':
    unittest.main()
