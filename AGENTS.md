# AGENTS.md

## Project Overview
`math-worksheet-generator` is a small Python CLI tool that generates printable math practice worksheets as PDF files. It creates question pages and an answer sheet for addition, subtraction, multiplication, division, or mixed exercises, with an optional front page for classroom use.

The repository is intentionally lightweight: the main logic, PDF layout, and CLI all live in a single script. Contributions should preserve that simplicity unless a change clearly justifies broader restructuring.

## Tech Stack
- Python `3.11` is the supported runtime in CI and the version documented in the repository.
- `fpdf2==2.7.4` is the only runtime dependency listed in `requirements.txt`.
- `unittest` from the Python standard library is the active test framework in `tests/test_math_worksheet_generator.py`.
- `flake8` is the configured linter via `setup.cfg`.
- GitHub Actions on Ubuntu runs the default CI workflow from `.github/workflows/python-app.yml`, installing `flake8`, `pytest`, and the runtime requirements before linting and running tests.

## Essential Commands
Setup:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install flake8 pytest
```

Development:
```bash
python3 run.py --type +
python3 run.py --type mix --digits 3 -q 100 --output worksheet.pdf
python3 run.py --type x --title "Math Quiz 1"
python3 run.py --help
```

Testing:
```bash
python3 -m unittest tests/test_math_worksheet_generator.py
python3 -m unittest discover -s tests
```

Linting:
```bash
python3 -m flake8 .
```

Build / artifact generation:
```bash
python3 run.py --type + --output worksheet.pdf
```
There is no separate packaging or compile step; generating the PDF is the build artifact for this project.

## Directory Structure & Architecture
- `run.py`: the application entry point, CLI parser, worksheet generator class, question generation logic, and PDF rendering implementation.
- `tests/`: unit tests for math generation helpers and pagination/layout behavior.
- `.github/workflows/`: CI automation for linting and test execution.
- `requirements.txt`: pinned runtime dependency list.
- `setup.cfg`: `flake8` configuration.
- Sample assets in the repository root such as `division.png` and sample PDFs/PNGs are required for rendered output or documentation.

Architecture notes:
- `MathWorksheetGenerator` is the core class. It owns worksheet configuration, random question generation, page splitting, and FPDF drawing.
- `main(...)` wires together question generation, optional front page creation, worksheet pages, answer page creation, and final PDF output.
- Division questions are constrained to integer answers through factor-based question generation.
- First-page capacity differs from later pages because the first worksheet page reserves space for a header row; pagination changes should be validated against existing tests.

## Code Style & Conventions
- Follow the current style of the repository: straightforward Python, minimal abstraction, and small helper methods around PDF rendering.
- Preserve compatibility with Python `3.11`.
- Keep changes ASCII unless a file already requires other characters.
- Use descriptive names and maintain the existing public CLI flags rather than introducing aliases casually.
- Keep line length and complexity within the existing `flake8` configuration in `setup.cfg`.
- Prefer extending `MathWorksheetGenerator` and existing helper methods over scattering new worksheet behavior across unrelated modules.
- Avoid silent behavioral changes to page geometry, question ordering, or answer formatting; these are user-visible outputs.

## Testing Requirements
- Add or update unit tests in `tests/test_math_worksheet_generator.py` for every behavior change in question generation, pagination, front-page handling, or PDF assembly flow.
- For logic that depends on randomness, use patching or controlled assertions rather than brittle exact-output expectations.
- When modifying pagination or layout rules, cover both page counts and method call patterns, following the existing mocked tests.
- Run `python3 -m unittest tests/test_math_worksheet_generator.py` before finishing work.
- Run `python3 -m flake8 .` when `flake8` is installed locally; CI also enforces linting.

## Security & Compliance
- Keep the tool local-first. It does not need network access to generate worksheets, and new features should not introduce remote dependencies without strong justification.
- Treat CLI inputs such as `--output` and `--title` as untrusted user input. Do not add shell execution, dynamic imports, or unsafe file operations based on those values.
- Preserve deterministic safety constraints in generated math content, especially the non-negative subtraction behavior and integer-only division behavior unless requirements explicitly change.
- Do not commit generated personal/student data. Front-page fields are intended to be filled in after generation, not stored in source control.
- Preserve license and attribution files. The repository is distributed under the license in `LICENSE`.

## Git Workflow & Commit Conventions
- Create feature branches with the `codex/` prefix for Codex-authored work.
- Keep commits focused and reviewable; avoid mixing functional changes, fixture/sample asset churn, and documentation-only edits in one commit unless they are tightly coupled.
- Rebase or merge from `master` as needed, but target `master` for pull requests because CI is configured on that branch.
- Match the existing commit history style: short imperative subjects, optionally referencing issue or PR numbers when relevant.
- Mention test coverage in the pull request description for changes that affect generation logic or pagination.
- Do not commit transient local artifacts such as ad hoc generated worksheets unless the repository explicitly needs a new sample output.
