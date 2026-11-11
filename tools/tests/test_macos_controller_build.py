import importlib.util
import json
from pathlib import Path
import unittest

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('macos_build', TOOLS / 'macos/build-macos.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class MacControllerBuildTests(unittest.TestCase):
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
