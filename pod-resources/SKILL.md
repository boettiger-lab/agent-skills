---
name: pod-resources
description: Read the CPUs, memory and fast disk actually available to this container. `nproc` prints 1 here because OMP_NUM_THREADS=1, which is wrong; never use it. Use whenever you count cores, before sizing any multiprocessing pool, parallel sweep, make -j, or large in-memory job, and before blaming slowness on CPU contention (check `top` for idle CPU first). Allocations change, so never rely on remembered core or RAM numbers; query the cgroup each time. Also use before any I/O-heavy work (clones, builds, large downloads, scratch files, many git worktrees) and before writing anything that queues or waits on cluster work (use cluster Jobs or Armada, not a local polling loop): /home/jovyan is JuiceFS, slow and error-prone under load, while /tmp and the rest of the root filesystem are fast local disk.
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

## Disk: home is JuiceFS, everything else is local

`/home/jovyan` is a JuiceFS FUSE mount (`df -hT ~` shows `fuse.juicefs`). It is network-backed, slow under load, and has failed with `input/output error` on small files such as `~/.kube/config` and the kubectl OIDC token lock while other sessions were busy. Everything outside home, including `/tmp` and the session scratchpad, is the pod's local overlay disk and much faster.

- Put scratch files, build output, downloads and temporary clones or git worktrees under `/tmp` or the scratchpad, not home.
- Keep in home only what must survive a pod restart: the repos themselves, configs, memory.
- An `input/output error` from a file under home is the filesystem, not the program; retry it, and move I/O-heavy work to local disk.

### Don't run work queues from this pod

Batch work belongs in a queue the cluster manages: Kubernetes Jobs, Armada, Kueue. Each task should run to completion there and write its result to S3 or a PVC. Don't run a supervisor or a polling loop from this pod. A local supervisor breaks on things unrelated to the work, and a kubectl loop loads JuiceFS. On 2026-11-25 a local no-harness supervisor lost tasks to an admission-webhook outage, a JuiceFS I/O error and an expired kubectl login. Its `kubectl get` loops, each reading the several hundred small files of `~/.kube/cache` from JuiceFS, exhausted the mount's ports to its metadata database, and writes to home failed.

- To wait for one thing, use a single blocking call (`kubectl wait --for=condition=complete job/NAME --timeout=...`) or a watch, not a loop.
- Only where a loop is truly unavoidable, check no more often than every 30 seconds once things are running.
- Don't move kubectl's cache with `KUBECACHEDIR`. `~/.kube/cache` also holds the NRP login (`oidc-login`), so a moved cache has no token and every call fails with a device-code `invalid_grant` error. Tried on 2026-11-25, it failed every no-harness task started afterwards.
