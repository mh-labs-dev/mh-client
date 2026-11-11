import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from release_layout import release_dir

spec = importlib.util.spec_from_file_location('organize_packages', TOOLS / 'windows/organize-packages.py')
organizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(organizer)


class ReleaseLayoutTests(unittest.TestCase):
    def test_platforms_and_architectures_are_separated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [release_dir(platform, '1.2-test', arch, root)
                     for platform, arch in [('windows', 'x64'), ('macos', 'arm64'),
                                             ('ios', 'arm64'), ('android', 'arm64-v8a')]]
            self.assertEqual(len(set(paths)), 4)
            for path in paths:
                self.assertTrue(path.is_relative_to(root.resolve() / 'release'))
            for version in ('../outside', '/tmp/outside', '', '..'):
                with self.assertRaises(ValueError):
                    release_dir('macos', version, 'arm64', root)
            with self.assertRaises(ValueError):
                release_dir('windows', '1.2', 'arm64-v8a', root)

    def test_legacy_versions_move_without_altering_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'dist/1.2-test'
            (source / 'unpacked').mkdir(parents=True)
            (source / 'unpacked/MH.exe').write_bytes(b'application fixture')
            (source / 'MH-1.2-test-windows-x64.zip').write_bytes(b'archive fixture')
            before = organizer.hashes(source)
            organizer.migrate(root)
            self.assertTrue(source.exists())
            organizer.migrate(root, apply=True)
            target = release_dir('windows', '1.2-test', 'x64', root)
            self.assertEqual(organizer.hashes(target), before)
            self.assertFalse(source.exists())
            self.assertEqual(organizer.plan(root), [])

    def test_flat_outputs_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist').mkdir()
            source = root / 'dist/MH-1.2-windows-x64.exe'
            source.write_bytes(b'portable fixture')
            target = release_dir('windows', '1.2', 'x64', root) / source.name
            target.parent.mkdir(parents=True)
            target.write_bytes(b'existing release')
            with self.assertRaises(FileExistsError):
                organizer.migrate(root, apply=True)
            self.assertEqual(target.read_bytes(), b'existing release')
            self.assertTrue(source.exists())
            target.unlink()
            organizer.migrate(root, apply=True)
            self.assertEqual(target.read_bytes(), b'portable fixture')

    def test_symlink_destination_cannot_escape_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'release').mkdir()
            (root / 'elsewhere').mkdir()
            (root / 'release/macos').symlink_to(root / 'elsewhere')
            with self.assertRaises(ValueError):
                release_dir('macos', '1.2', 'arm64', root)


if __name__ == '__main__':
    unittest.main()
