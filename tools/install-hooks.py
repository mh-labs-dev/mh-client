"""Enable the repository's local checks without staging or committing files."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
current = subprocess.run(['git', 'config', '--local', '--get', 'core.hooksPath'], cwd=root, capture_output=True, text=True)
if current.returncode not in (0, 1):
    raise SystemExit('Cannot read Git hook configuration')
if current.stdout.strip() not in ('', '.githooks'):
    raise SystemExit('A different hooksPath is configured; merge the hooks explicitly instead of overwriting it')
hook = root/'.githooks/pre-commit'
if not hook.is_file():
    raise SystemExit('Repository hook is missing')
hook.chmod(hook.stat().st_mode | 0o111)
subprocess.run(['git', 'config', '--local', 'core.hooksPath', '.githooks'], cwd=root, check=True)
print('Local pre-commit check enabled. Re-run this installer after each new clone.')
