#!/usr/bin/env python3
"""Create an allowlisted hand-in kit without survey data or Git credentials."""

import hashlib
import json
import zipfile
from pathlib import Path

from evs_model import __version__

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'submission'
folder.mkdir(exist_ok=True)
archive = folder / f'filip_karika_develop_v{__version__}.zip'
prefix = f'evs-develop-v{__version__}'
files = set()
for name in ('.gitattributes', '.gitignore', 'Makefile', 'README.md', 'pyproject.toml', 'requirements.txt',
             'requirements-lock.txt', 'requirements-model-lock.txt', 'data/README.md', '02_develop/SUBJECT_COMPLIANCE.md', '02_develop/DEFINE_TO_DEVELOP.md'):
    files.add(ROOT / name)
for pattern in ('src/**/*.py', 'scripts/*.py', 'tests/*.py', '.github/workflows/*.yml',
                'examples/*.csv', 'models/*', 'notebooks/*.ipynb', '02_develop/report/*.md',
                '02_develop/results/*.json', '02_develop/results/*.csv',
                '02_develop/figures/*.png', '02_develop/output/*.pdf'):
    files.update(p for p in ROOT.glob(pattern) if p.is_file())
wheel = ROOT / f'dist/evs_life_satisfaction-{__version__}-py3-none-any.whl'
if not wheel.is_file():
    raise SystemExit('Build the current wheel first: make package')
manifest = {}
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for path in sorted(files):
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = path.relative_to(ROOT).as_posix()
        if any(part in ('.git', 'raw', 'local', '.venv', '.venv-develop', '.venv-verify') for part in path.relative_to(ROOT).parts):
            raise RuntimeError(f'Forbidden submission member: {relative}')
        output.write(path, f'{prefix}/{relative}')
        manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    release_path = f'release/{wheel.name}'
    output.write(wheel, f'{prefix}/{release_path}')
    manifest[release_path] = hashlib.sha256(wheel.read_bytes()).hexdigest()
    output.writestr(f'{prefix}/MANIFEST.sha256.json', json.dumps(manifest, indent=2, sort_keys=True))
print(f'Created {archive}: {len(manifest)} files, {archive.stat().st_size:,} bytes; no source survey or Git history.')
