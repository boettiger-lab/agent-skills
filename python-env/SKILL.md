---
name: python-env
description: >-
  Never install into or run the system Python. Consult BEFORE `pip install`, before
  running a Python script or module, and before choosing an interpreter: prefer an
  existing project venv, then a container image, then a project-local venv you create.
  Triggers on: pip install, python3 script.py, python -m, venv, virtualenv, uv,
  conda, "which python", ModuleNotFoundError, externally-managed-environment.
license: Apache-2.0
metadata:
  author: boettiger-lab
  version: "1.0"
---

# Python Environment

**Never use system Python directly.** Do not `pip install` into the system environment.

## Preferred approaches (in order)

1. **Local venv** — Check for a `.venv/` or `venv/` in the current working directory. If one exists, activate it before running Python:
   ```bash
   source .venv/bin/activate  # or venv/bin/activate
   ```

2. **Docker** — If no local venv exists, use a container:
   - `ghcr.io/boettiger-lab/datasets:latest` — DuckDB, GDAL, geopandas, h3, rasterio, pyarrow, and other geospatial/data tooling
   - `ghcr.io/rocker-org/ml:latest` — R + Python ML stack (torch, scikit-learn, etc.)

   Always pull the latest image before running:
   ```bash
   docker pull ghcr.io/boettiger-lab/datasets:latest
   ```

   Example:
   ```bash
   docker run --rm -v "$(pwd):/work" -w /work ghcr.io/boettiger-lab/datasets:latest python3 script.py
   ```

3. **Create a venv** — If neither option above fits, create a project-local venv:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate && pip install ...
   ```
