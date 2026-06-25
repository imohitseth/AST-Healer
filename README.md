# AST-Healer

[![CI](https://github.com/imohitseth/AST-Healer/actions/workflows/ci.yml/badge.svg)](https://github.com/imohitseth/AST-Healer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-multi--stage-informational.svg)](https://docs.docker.com/build/building/multi-stage/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**AST-Healer** is a self-healing Python developer tool that detects runtime exceptions, surgically extracts the failing function using Python's native Abstract Syntax Tree parser, repairs it via a Gemini LLM agent, and re-verifies the fix in a closed loop — without modifying any surrounding code.

It ships as both a CLI tool and a production-ready FastAPI web service with async background task execution.

---

## Demo

> **CLI healing loop** — intentional bugs in `tests/mock_code.py` are auto-detected, repaired, and verified sequentially:

<img width="1418" height="1035" alt="image" src="https://github.com/user-attachments/assets/5be33af2-b34c-433b-9cf1-2f0d43e1fd84" />
<img width="1418" height="966" alt="image" src="https://github.com/user-attachments/assets/e7a45722-18b9-4140-b264-b30260fcc96d" />
<img width="825" height="575" alt="image" src="https://github.com/user-attachments/assets/8e43e24e-914b-49ec-bf5a-9685feb90e79" />


---

## Why this exists

Most LLM-based code repair tools send the entire source file into the model's context window. This has three concrete problems:

1. **Token waste** — hundreds of lines of unrelated code consume context that could be used for the actual fix.
2. **Model distraction** — longer context degrades LLM attention and increases hallucinations and off-target edits.
3. **Untargeted rewrites** — LLMs frequently modify surrounding code that wasn't broken, introducing secondary bugs.

AST-Healer resolves this by using Python's `ast` module to surgically extract only the `FunctionDef` node corresponding to the failing function — typically 10–20 lines — and submits only that block to the model. The corrected function is written back at the exact line range, with indentation automatically re-matched to the original.

---

## How it works

```
Run script / pytest
       │
       ▼
   Exit 0? ──── Yes ──► Done ✓
       │
       No
       │
       ▼
 Parse traceback (scan backwards, skip <module> frames)
       │
       ▼
 Extract file path + failing function name
       │
       ▼
 ast.parse() → walk tree → find FunctionDef node
       │
       ▼
 ast.get_source_segment() → extract function source (~10–20 lines)
       │
       ▼
 Send [function code + error log] to Gemini agent
       │
       ▼
 Clean LLM response (strip markdown fences, re-indent)
       │
       ▼
 Replace lines [lineno : end_lineno] in source file
       │
       ▼
 Sleep 8s (API rate-limit pacing) → loop
```

### Key engineering decisions

**AST traversal vs. regex substitution.** Text-based find-and-replace fails when the same function name appears in multiple scopes (inner classes, helpers, overloads). `ast.walk()` with `isinstance(node, ast.FunctionDef)` guarantees we target the exact node whose identifier appears in the traceback, regardless of file structure.

**Subprocess sandbox isolation.** Target scripts run in a separate Python subprocess with a propagated `PYTHONPATH`. This prevents exceptions in user code from corrupting the FastAPI event loop, and prevents import state from leaking between healing iterations.

**Async non-blocking API.** `POST /heal/auto` returns `202 Accepted` with a task ID immediately. The healing loop runs inside `asyncio.create_task()`. Clients poll `GET /tasks/{task_id}` for completion — the server stays responsive during long-running LLM calls.

**Backward traceback parsing.** The traceback parser scans frames from the bottom up to find the innermost non-`<module>` frame. This correctly handles exceptions that propagate through multiple call sites — we target the origin function, not an intermediate caller.

**Indentation-preserving replacement.** `target_node.col_offset` gives the original function's indentation level. The healed code is dedented then re-indented to match before writing, preventing `IndentationError` on the next run.

---

## Tech stack

| Component | Technology | Notes |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async ASGI, non-blocking endpoints |
| Input validation | Pydantic v2 | `extra="forbid"` blocks unexpected fields |
| AI integration | google-antigravity (Gemini 1.5 Flash) | Agentic SDK with async context manager |
| AST parsing | Python `ast` stdlib | Zero third-party dependencies for core parsing |
| Deployment | Docker (multi-stage) | `python:3.11-slim`, non-root `appuser` UID 10001 |
| Testing | Pytest | Used as healing target and verification runner |
| CI | GitHub Actions | Lint + test on every push and PR |

---

## Project structure

```
AST-Healer/
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: lint + test pipeline
├── tests/
│   ├── mock_code.py          # Target file with intentional runtime bugs
│   ├── mock_run.py           # Standalone script execution target
│   └── test_mock_code.py     # Pytest suite for the healing harness
├── app.py                    # FastAPI routes and async background workers
├── main.py                   # Core healing loop, traceback parser, subprocess runner
├── parser.py                 # AST extraction and line-range replacement
├── schemas.py                # Pydantic v2 request models
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Local dev setup
├── requirements.txt
├── .env.example              # Credential template
├── CONTRIBUTING.md
└── LICENSE
```

---

## Setup

**Prerequisites:** Python 3.11+, Git, a free [Gemini API key](https://aistudio.google.com/).

```bash
# 1. Clone
git clone https://github.com/imohitseth/AST-Healer.git
cd AST-Healer

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\Activate.ps1    # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials (copy the template, then fill in your key)
cp .env.example .env
```

---

## Usage

### CLI — auto-heal a script

```bash
python main.py --mode script --target tests/mock_run.py --max-attempts 5
```

### CLI — auto-heal a pytest suite

```bash
python main.py --mode pytest --target tests/test_mock_code.py --max-attempts 5
```

### FastAPI web service

```bash
# Do NOT use --reload; Uvicorn restarts on file saves, killing active healing tasks
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Interactive API docs: `http://localhost:8000/docs`

### Docker Compose (recommended for local dev)

```bash
docker compose up --build
```

### Docker (manual)

```bash
docker build -t ast-healer .
docker run -e GEMINI_API_KEY=your_key_here -p 8000:8000 ast-healer
```

---

## API reference

### `POST /heal/auto`

Triggers the automated run → detect → repair → verify loop in the background.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `"script"` | `"script"` or `"pytest"` |
| `file_path` | string | `tests/mock_run.py` | Path to the target file |

**Response `202 Accepted`:**
```json
{
  "task_id": "ee39104126d1421e9f882f5ecd0519a1",
  "status": "PENDING",
  "message": "Auto-healing task (script mode) started in background for target: tests/mock_run.py"
}
```

---

### `GET /tasks/{task_id}`

Poll for healing task status and result.

**Response `200 OK`:**
```json
{
  "task_id": "ee39104126d1421e9f882f5ecd0519a1",
  "status": "SUCCESS",
  "result": "Code executed, bug auto-detected, and code healed successfully in script mode.",
  "error": null
}
```

Possible `status` values: `PENDING` → `RUNNING` → `SUCCESS` / `FAILED`

---

### `POST /heal`

Manual trigger — provide the file path, function name, and error log directly (skip auto-detection).

**Request body:**
```json
{
  "file_path": "tests/mock_code.py",
  "function_name": "divide_numbers",
  "error_log": "ZeroDivisionError: division by zero"
}
```

---

### `GET /`

Health check. Returns `{"status": "healthy", "service": "AST-Healer API"}`.

---

## Challenges and solutions

**Uvicorn auto-reload killing active workers.** When the healer writes a fixed function back to the source file, Uvicorn's `--reload` watcher detects the file change and immediately restarts the server — killing the background task mid-execution. Solution: documented the no-reload requirement for self-healing environments; for local development, add `# type: ignore` markers or use a separate dev server instance that watches only non-target files.

**`PYTHONPATH` not propagated to subprocesses.** Running target scripts from the project root caused `ModuleNotFoundError` in subprocesses because relative imports failed. Solution: `os.environ.copy()` combined with explicit `PYTHONPATH=os.getcwd()` injection into each subprocess environment dictionary.

**`<module>` frames surfacing as the "failing function".** When an exception originates at module scope (outside any function), the traceback parser initially extracted `<module>` as the function name, causing `ast.walk()` to find no matching `FunctionDef` node. Solution: scan the call stack in reverse, skipping any frame where `func == "<module>"`, and continue until a valid function-scoped identifier is found.

---

## Security

- Docker container runs as `appuser` (UID 10001), not root, preventing privilege-escalation container escapes.
- Pydantic `extra="forbid"` rejects any unexpected JSON fields at the API boundary.
- API credentials are loaded from `.env` via `python-dotenv` and never hardcoded or logged.

> **Warning:** AST-Healer reads and overwrites Python source files on the host filesystem using LLM-generated code. For production or multi-tenant use, run target execution inside an isolated sandbox (Docker-in-Docker, gVisor, or Firecracker microVMs) to contain untrusted generated code.

---

## Known limitations

- Only handles `FunctionDef` nodes. Module-scope errors, class-method bugs where the traceback points to `<module>`, and deeply nested inner functions may not be correctly targeted.
- Traceback parsing is Python-specific. Other languages require a separate parser implementation.
- The in-memory `tasks_db` dict is not persistent and not safe for multi-process or multi-replica deployments. A Celery + Redis task queue is the correct production replacement.
- Multi-function failures in a single run are resolved one at a time (one function per healing iteration), which may require several loop passes for files with multiple independent bugs.

---

## Roadmap

- [ ] GitHub Actions CI with live build badge *(added)*
- [ ] Docker Compose for local dev *(added)*
- [ ] Docker-in-Docker sandboxing for untrusted code execution
- [ ] Celery + Redis distributed task queue
- [ ] Persistent task history (SQLite or Redis)
- [ ] Tree-sitter extension for Go, TypeScript, and Java
- [ ] Web UI for real-time healing loop progress visualization

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, coding standards, and how to submit a pull request.

---

## License

MIT — see [LICENSE](LICENSE).
