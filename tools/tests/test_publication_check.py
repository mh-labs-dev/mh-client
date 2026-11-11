import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
spec = importlib.util.spec_from_file_location('publication_check', TOOLS/'publication_check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class PublicationTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        subprocess.run(['git','init','-q',str(root)],check=True)
        (root/'tools').mkdir()
        (root/'.githooks').mkdir()
        for name in ('publication_check.py','publication-exceptions.json'):
            shutil.copy2(TOOLS/name,root/'tools'/name)
        shutil.copy2(ROOT/'.githooks/pre-commit',root/'.githooks/pre-commit')
        (root/'.githooks/pre-commit').chmod(0o755)
        subprocess.run(['git','config','core.hooksPath','.githooks'],cwd=root,check=True)
        return root

    def run_hook(self, root):
        return subprocess.run(['git','hook','run','pre-commit'],cwd=root,capture_output=True,text=True)

    def test_hook_checks_staged_bytes_and_never_prints_the_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            token = 'gh'+'p_'+'aB7cD9'*8
            path = root/'README.md'
            path.write_text(token)
            subprocess.run(['git','add','README.md'],cwd=root,check=True)
            path.write_text('Clean working copy; the staged content is still sensitive.')
            result = self.run_hook(root)
            self.assertEqual(result.returncode,1,result.stderr)
            self.assertIn('access token',result.stdout+result.stderr)
            self.assertNotIn(token,result.stdout+result.stderr)
            subprocess.run(['git','add','README.md'],cwd=root,check=True)
            self.assertEqual(self.run_hook(root).returncode,0)

    def test_forced_local_file_is_blocked_and_staged_deletion_is_respected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            (root/'.gitignore').write_text('.local/\n')
            (root/'.local').mkdir()
            (root/'.local/devices.json').write_text('{}')
            subprocess.run(['git','add','-f','.local/devices.json'],cwd=root,check=True)
            result = self.run_hook(root)
            self.assertIn('local/private file',result.stdout+result.stderr)
            subprocess.run(['git','rm','--cached','-f','.local/devices.json'],cwd=root,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(self.run_hook(root).returncode,0)

    def test_assistant_files_are_blocked_even_if_forced_into_the_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            (root/'.gitignore').write_text('AGENTS.md\n.codex/\n')
            for name in ('AGENTS.md', 'docs/CLAUDE.md', 'GEMINI.md', '.codex/session.md'):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Local instructions')
                subprocess.run(['git','add','-f',name], cwd=root, check=True)
            result = self.run_hook(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn('local/private file', result.stdout+result.stderr)
            self.assertIn('local/private file', checker.rules_for('docs/development/en/BUILD.md', b'Local build notes', {}))
            self.assertEqual(checker.rules_for('tools/windows/README.md', b'Build instructions', {}), [])
            self.assertEqual(checker.rules_for('src/main.rs', b'fn main() {}', {}), [])

    def test_reviewed_fixture_exception_does_not_cover_a_modified_key(self):
        approved = checker.exceptions(ROOT)
        name = 'libs/hbb_common/tests/data/websocket-key.pem'
        data = (ROOT/name).read_bytes()
        self.assertNotIn('private key',checker.rules_for(name,data,approved))
        self.assertIn('private key',checker.rules_for(name,data+b'changed',approved))
        self.assertIn('private key',checker.rules_for('config/server.pem',data,approved))
        encoded = json.dumps({'workspace':str(Path('C:/Users/private-person/config'))}).encode()
        self.assertIn('local machine path',checker.rules_for('config/workspace.json',encoded,approved))
        for data in (json.dumps({'password':'private-value'}).encode(), b'api_key: private-value'):
            self.assertIn('literal credential field',checker.rules_for('config/service.yaml',data,approved))
        self.assertNotIn('literal credential field',checker.rules_for('config/service.yaml',b'token: ${{ secrets.TOKEN }}',approved))
        self.assertIn('local/private file',checker.rules_for('license.env',b'',approved))
        self.assertIn('local/private file',checker.rules_for('02-账号与密码.txt',b'',approved))
        self.assertIn('credential in URL',checker.rules_for('config/service.json',b'https://'+b'user:opaque-secret@service.example',approved))

    def test_source_zip_profile_is_blocked_without_displaying_its_host(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source.zip'
            host = 'https://'+'private-demo'+'.trycloudflare.com'
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('controller-profile.json',json.dumps({'api-server':host}))
            result = subprocess.run([sys.executable,str(TOOLS/'publication_check.py'),'--source-archive',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stderr)
            self.assertIn('temporary tunnel address',result.stdout)
            self.assertIn('local/private file',result.stdout)
            self.assertNotIn(host,result.stdout+result.stderr)

    def test_submodule_scan_uses_the_staged_commit_and_fails_if_it_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            child = root/'libs/hbb_common'
            child.parent.mkdir()
            subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(ROOT/'libs/hbb_common'),str(child)],check=True)
            oid = subprocess.check_output(['git','rev-parse','HEAD'],cwd=child,text=True).strip()
            subprocess.run(['git','update-index','--add','--cacheinfo','160000,'+oid+',libs/hbb_common'],cwd=root,check=True)
            key = child/'tests/data/websocket-key.pem'
            key.parent.mkdir(parents=True)
            key.write_text('A clean working file cannot replace the staged submodule object.')
            files = {name:data for name,data,mode in checker.indexed_files(root)}
            pinned = subprocess.check_output(['git','show',oid+':tests/data/websocket-key.pem'],cwd=child)
            self.assertEqual(files['libs/hbb_common/tests/data/websocket-key.pem'],pinned)
            subprocess.run(['git','update-index','--cacheinfo','160000,'+'f'*40+',libs/hbb_common'],cwd=root,check=True)
            with self.assertRaises(RuntimeError):
                list(checker.indexed_files(root))


if __name__ == '__main__':
    unittest.main()
