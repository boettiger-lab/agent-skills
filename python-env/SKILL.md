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

   Example:
   ```bash
   docker run --rm -v "$(pwd):/work" -w /work ghcr.io/boettiger-lab/datasets:latest python3 script.py
   ```

3. **Create a venv** — If neither option above fits, create a project-local venv:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate && pip install ...
   ```
