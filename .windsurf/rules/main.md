---
trigger: always_on
---

This project uses uv for dependency management. That means you should use:
- `uv add <package>` for installing dependencies
- `uv run pytest` for testing
- `uv sync` for syncing the environment


After we are done with a new features, we: 
- Bump the version in @pyproject.toml
- Run `uv sync` to upgrade the lock file
- Commit and push, merge to main.
- Don't forget to commit the uv.lock file too
- Generate a new tag
- Generate a new release via the Github cli. 
(the github action workflow will publish it to pypi)

Every time you write new tests, you should test if they are working: `uv run pytest -v`