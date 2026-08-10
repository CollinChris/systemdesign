# CLAUDE.md — Development Guidelines for system_design_app

## Project Overview
This is a Python project managed with `uv`. Follow these practices consistently.

## Package Management
- Use `uv` for all dependency management — never use `pip` directly
- Add dependencies: `uv add <package>`
- Add dev dependencies: `uv add --dev <package>`
- Run scripts: `uv run <script>`
- Sync environment: `uv sync`
- Never manually edit `uv.lock`

## Code Style
- Follow PEP 8 strictly
- Max line length: 88 characters (Black default)
- Use Black for formatting: `uv run black .`
- Use Ruff for linting: `uv run ruff check .`
- Use type hints on all function signatures
- Prefer `pathlib.Path` over `os.path`

## Project Structure
```
system_design_app/
  src/
    system_design_app/   # main package
  tests/                 # mirrors src structure
  pyproject.toml
  CLAUDE.md
  README.md
```

## Testing
- Use `pytest` for all tests: `uv run pytest`
- Place tests in `tests/`, mirroring `src/` structure
- Aim for meaningful coverage on business logic
- Use `pytest-cov` for coverage reports: `uv run pytest --cov`
- Every new feature or bug fix must include a corresponding test

## Type Checking
- Use `mypy` for static type checking: `uv run mypy src/`
- All public functions and methods must have type annotations
- Avoid `Any` unless absolutely necessary and document why

## Git Hygiene
- Write clear, imperative commit messages (e.g., "Add diagram export feature")
- Commit only relevant files — never commit `.env`, `__pycache__`, or `.venv`
- Keep commits small and focused on a single change
- Use `.gitignore` to exclude: `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `dist/`, `.mypy_cache/`

## Security
- Never hardcode secrets, API keys, or credentials in source files
- Use environment variables for all secrets; load with `python-dotenv` or similar
- Validate all external inputs at system boundaries
- Avoid `eval()`, `exec()`, and `subprocess` with shell=True unless unavoidable

## Error Handling
- Use specific exception types — never bare `except:`
- Let unexpected exceptions propagate; only catch what you can handle
- Use logging (not print) for diagnostics: `import logging`
- Return meaningful error messages to callers

## Naming Conventions
- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

## Do Not
- Do not use `pip install` — always use `uv add`
- Do not commit `.venv/` or generated files
- Do not add unnecessary abstractions or over-engineer solutions
- Do not suppress linter warnings without a documented reason
- Do not write comments that restate what the code already says clearly

## Recommended Dev Dependencies
```
uv add --dev black ruff mypy pytest pytest-cov
```
