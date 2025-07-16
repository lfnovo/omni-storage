# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Omni-Storage is a unified Python interface for file storage that provides a consistent API across multiple storage backends (Local, S3, GCS). It uses an abstract base class pattern with a factory for backend selection.

## Key Architecture

- **Abstract Base**: `src/omni_storage/base.py` defines the `Storage` interface that all backends implement
- **Factory Pattern**: `src/omni_storage/factory.py` contains `get_storage()` which selects backends based on environment variables or explicit configuration
- **Lazy Loading**: Cloud storage providers (S3, GCS) are imported only when needed to avoid dependency issues
- **Type Safety**: Project includes `py.typed` for full type checking support

## Development Commands

```bash
# Install all dependencies (including dev tools)
uv sync --all-extras

# Install specific backend dependencies
uv sync --extra gcs    # Google Cloud Storage
uv sync --extra s3     # Amazon S3

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=omni_storage

# Run linter
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/
```

## Testing Guidelines

- All storage backends have comprehensive test coverage using mocks
- Tests use pytest fixtures with temporary directories for isolation
- Mock cloud services (boto3, google-cloud-storage) to avoid external dependencies
- Test both automatic backend selection (env vars) and explicit selection (storage_type parameter)

## Environment Variables

The factory automatically selects storage backend based on these environment variables:
- **S3**: `AWS_S3_BUCKET` (required), `AWS_REGION` (optional)
- **GCS**: `GCS_BUCKET` (required)
- **Local**: `DATADIR` (optional, defaults to `./data`)

## Adding New Storage Backends

1. Create a new file in `src/omni_storage/` (e.g., `azure.py`)
2. Subclass `Storage` from `base.py` and implement all abstract methods
3. Add lazy import and initialization logic to `factory.py`
4. Create comprehensive tests in `tests/test_<backend>_storage.py`
5. Add optional dependencies to `pyproject.toml` under a new extra

## Code Style

- Use type hints for all function signatures
- Follow existing patterns for error handling (RuntimeError for operations, ValueError for config)
- Maintain consistency with existing backends when implementing new ones
- All imports should be at the top of files except for lazy-loaded backends in factory.py