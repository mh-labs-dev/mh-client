import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('controller', Path(__file__).with_name('controller-profile.py'))
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class ProfileTests(unittest.TestCase):
    def test_public_connection_settings_only(self):
        profile = {'api-server': 'https://example.com', 'custom-rendezvous-server': 'example.com',
                   'relay-server': 'example.com', 'key': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
                   'allow-websocket': 'Y', 'allow-insecure-tls-fallback': 'N'}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            path.write_text(json.dumps(profile))
            self.assertEqual(controller.validate(path), profile)
            for change in ({'password': 'must-not-be-bundled'},
                           {'api-server': 'https://user:password@example.com'},
                           {'relay-server': 'another.example.com'},
                           {'allow-insecure-tls-fallback': 'Y'}):
                with self.subTest(change=list(change)):
                    path.write_text(json.dumps(profile | change))
                    with self.assertRaises(ValueError):
                        controller.validate(path)


if __name__ == '__main__':
    unittest.main()
