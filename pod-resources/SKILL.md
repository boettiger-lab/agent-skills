---
name: pod-resources
description: Read the CPUs and memory actually available to this container before running parallel or memory-heavy work. Use before sizing any multiprocessing pool, parallel sweep, make -j, or large in-memory job. Allocations change, so never rely on remembered core or RAM numbers; query the cgroup each time.
---

# Sizing parallel work to the container

The pod's CPU and memory allocations change over time. Never size a job from a remembered number. Query them at the moment you launch.

## Check

```sh
python3 ~/.claude/skills/pod-resources/resources.py [MB_PER_WORKER] [HEADROOM_MB]
```

This prints the usable CPUs, the cgroup memory limit, the memory in use (excluding reclaimable page cache) and the memory available, plus a suggested worker count.

## In Python

```python
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/pod-resources"))
from resources import safe_workers, cpus, memory_mb
workers = safe_workers(mb_per_worker=250, headroom_mb=3000)
```

## Pitfalls

- `nproc` honours `OMP_NUM_THREADS` and can report 1 on a many-core pod. Use the script (CPU affinity, capped by `/sys/fs/cgroup/cpu.max`).
- Keep `OMP_NUM_THREADS=1` inside workers, so each process uses one thread.
- Estimate per-worker memory from one run (peak RSS), then add headroom: other processes share the limit.
- Exceeding `memory.max` gets the pod OOM-killed. Re-check before each large launch, because other work may have started.
- Never `pkill -f` a pattern that also matches your own shell command line; kill by PID.
