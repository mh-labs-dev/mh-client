from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_privacy import environment_updates, inspect_bytes, check_tree


class BuildPrivacyTests(unittest.TestCase):
    def test_paths_detected_without_disclosing_them(self):
        for text in ("file:///Users/builder/project/main.dart", r"C:\Users\builder\src\main.rs"):
            for encoding in ("utf-8", "utf-16le"):
                self.assertIn("user home path", inspect_bytes(text.encode(encoding)))
        self.assertEqual(inspect_bytes(b"./mh/src/main.rs"), [])

    def test_target_linker_flags_survive_path_mapping(self):
        windows = environment_updates({}, target='windows')['CARGO_ENCODED_RUSTFLAGS'].split('\x1f')
        macos = environment_updates({}, target='macos')['CARGO_ENCODED_RUSTFLAGS'].split('\x1f')
        self.assertIn('-Ctarget-feature=+crt-static', windows)
        self.assertIn('link-args=-sectcreate __CGPreLoginApp __cgpreloginapp /dev/null', macos)
        self.assertEqual(environment_updates({'CARGO_ENCODED_RUSTFLAGS': '\x1f'.join(windows)}, target='windows')['CARGO_ENCODED_RUSTFLAGS'].split('\x1f'), windows)

    def test_custom_root_and_existing_flags_are_preserved(self):
        env = {"RUSTFLAGS": "-C opt-level=2", "CARGO_HOME": "D:/build/cache"}
        updates = environment_updates(env, root="D:/build/project", home="D:/people/builder")
        flags = updates["CARGO_ENCODED_RUSTFLAGS"].split("\x1f")
        self.assertEqual(flags[:2], ["-C", "opt-level=2"])
        self.assertIn("--remap-path-prefix=D:/build/project=./mh", flags)
        self.assertIn("--remap-path-prefix=D:/build/cache=./dependencies/cargo", flags)
        self.assertTrue(inspect_bytes(b"D:/build/project/src/main.rs", root="D:/build/project"))

    def test_packaging_blocks_leaked_paths_but_keeps_symbols_local(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.exe").write_bytes(b"MZ./mh/src/main.rs")
            (root / "app.pdb").write_bytes(b"/Users/builder/project/main.rs")
            self.assertEqual(check_tree(root, exclude_suffixes=(".pdb",))["build_path_check"], "passed")
            (root / "app.exe").write_bytes(b"MZ/Users/builder/project/main.rs")
            with self.assertRaisesRegex(ValueError, "app.exe") as error:
                check_tree(root, exclude_suffixes=(".pdb",))
            self.assertNotIn("/Users/builder", str(error.exception))


if __name__ == "__main__":
    unittest.main()
