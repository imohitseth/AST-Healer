# Contributing to AST-Healer

Thanks for your interest in contributing. This document covers how to set up a development environment, coding standards, and how to submit a pull request.

---

## Development setup

```bash
git clone https://github.com/imohitseth/AST-Healer.git
cd AST-Healer

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install ruff             # linter used in CI

cp .env.example .env        # add your GEMINI_API_KEY
```

---

## Running the tests

```bash
PYTHONPATH=. pytest tests/ -v
```

The mock tests in `tests/` do not require a live API key — they operate on the bundled `mock_code.py` and `mock_run.py` targets. Tests that invoke the Gemini agent are skipped automatically when `GEMINI_API_KEY` is not set.

---

## Coding standards

- **Python 3.11+** — use `asyncio`, `ast`, and standard library features where possible before reaching for third-party packages.
- **Linting** — run `ruff check . --select E,W,F --ignore E501` before pushing. CI will fail on lint errors.
- **Type hints** — add type annotations to all new functions and method signatures.
- **Docstrings** — one-line summary for simple functions; full Args/Returns for anything public-facing.
- No new dependencies should be added to `requirements.txt` without discussion in an issue first.

---

## Submitting a pull request

1. Fork the repo and create a branch from `main`: `git checkout -b feat/your-feature-name`
2. Make your changes. Add or update tests as needed.
3. Run `ruff check .` and `pytest tests/ -v` locally — both must pass.
4. Open a PR against `main` with a clear description of what changed and why.
5. Reference any related issues with `Closes #N`.

---

## Reporting bugs

Open a GitHub Issue with:
- Python version and OS
- Steps to reproduce
- Full traceback output
- The target file that caused the failure (if shareable)

---

## Feature requests

Open an issue with the `enhancement` label. Describe the use case, not just the implementation — it's easier to discuss tradeoffs that way.
