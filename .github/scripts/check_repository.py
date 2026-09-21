"""Validate repository hygiene; does not execute or evaluate research models."""

import ast
import subprocess
import sys
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    'README.md', 'CONTRIBUTING.md', 'data/README.md',
    'docs/01-problem-definition.md', 'docs/02-data-contract.md',
    '.github/workflows/ci.yml', 'requirements-ci.txt',
)
DATA_SUFFIXES = {
    '.csv', '.tsv', '.parquet', '.feather', '.h5', '.hdf5',
    '.db', '.duckdb', '.sqlite', '.sqlite3', '.pkl', '.pickle', '.joblib',
}


def validate(root, tracked):
    errors = []
    for name in REQUIRED:
        if name not in tracked or not (root / name).is_file():
            errors.append(f'Missing required tracked file: {name}')
    for name in tracked:
        path = root / name
        lower = name.lower()
        if path.is_symlink():
            errors.append(f'Symlinks are not supported: {name}')
            continue
        if not path.is_file():
            errors.append(f'Tracked path is not a regular file: {name}')
            continue
        if path.suffix.lower() in DATA_SUFFIXES:
            errors.append(f'Data/model binary must remain local: {name}')
        if lower.startswith('data/') and name != 'data/README.md':
            errors.append(f'Only data/README.md may be tracked under data/: {name}')
        if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example'):
            errors.append(f'Environment file must remain local: {name}')
        if any(part.lower() in {'.venv', '__pycache__', '.ipynb_checkpoints'} for part in path.parts):
            errors.append(f'Local environment/cache was committed: {name}')
        if path.stat().st_size > 20 * 1024 * 1024:
            errors.append(f'File exceeds the team 20 MiB limit: {name}')
        try:
            if path.suffix == '.py':
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=name)
            elif path.suffix == '.ipynb':
                # nbstripout 필터는 `git add` 시점에 출력을 지우므로 작업 폴더 사본에는
                # 출력이 남아 있을 수 있다. 실제로 커밋되는 사본(스테이징된 blob)을 검사한다.
                staged = subprocess.check_output(
                    ['git', 'cat-file', 'blob', f':{name}'], cwd=root
                ).decode('utf-8')
                notebook = nbformat.reads(staged, as_version=4)
                nbformat.validate(notebook)
                for index, cell in enumerate(notebook.cells, start=1):
                    if cell.cell_type == 'code' and (cell.outputs or cell.execution_count is not None):
                        errors.append(f'Clear notebook output before committing: {name}, cell {index}')
        except Exception as exc:
            errors.append(f'{name}: {type(exc).__name__}: {exc}')
    return errors


def main():
    # Read exactly this repository's tracked files, including staged additions.
    top = subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'], cwd=ROOT
    ).decode('utf-8').strip()
    if Path(top).resolve() != ROOT:
        raise SystemExit('Run inside the standalone project repository, not its parent repository.')
    output = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT)
    tracked = output.decode('utf-8').rstrip('\0').split('\0') if output else []
    errors = validate(ROOT, tracked)
    for error in errors:
        print(f'ERROR: {error}')
    if errors:
        return 1
    print(f'PASS: {len(tracked)} tracked files; repository policy and syntax/schema checks only.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
