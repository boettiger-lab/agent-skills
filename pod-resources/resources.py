#!/usr/bin/env python3
"""Report CPUs and memory actually available to this container (cgroup v2, with fallbacks),
and a suggested worker count for a multiprocessing pool.

Usage:  python3 ~/.claude/skills/pod-resources/resources.py [MB_PER_WORKER] [HEADROOM_MB]
Import: sys.path.insert(0, os.path.expanduser("~/.claude/skills/pod-resources")); from resources import safe_workers
"""
import os, sys


def _read(path):
    try:
        return open(path).read().strip()
    except OSError:
        return None


def cpus():
    """CPUs usable by this process: affinity, capped by the cgroup CPU quota if one is set.
    (nproc and os.cpu_count() can mislead: nproc honours OMP_NUM_THREADS.)"""
    n = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    q = _read("/sys/fs/cgroup/cpu.max")
    if q and not q.startswith("max"):
        quota, period = map(int, q.split())
        n = min(n, max(1, quota // period))
    return n


def memory_mb():
    """(limit, used, available) in MB for the container. 'used' excludes reclaimable page cache."""
    lim, cur = _read("/sys/fs/cgroup/memory.max"), _read("/sys/fs/cgroup/memory.current")
    if lim and cur and lim != "max":
        limit, used = int(lim), int(cur)
        stat = dict(l.split() for l in (_read("/sys/fs/cgroup/memory.stat") or "").splitlines() if " " in l)
        used -= int(stat.get("inactive_file", 0))           # page cache the kernel can reclaim
    else:                                                    # no cgroup limit: use the host
        info = dict(l.split(":", 1) for l in open("/proc/meminfo"))
        limit = int(info["MemTotal"].split()[0]) * 1024
        used = limit - int(info["MemAvailable"].split()[0]) * 1024
    mb = 2 ** 20
    return limit // mb, used // mb, (limit - used) // mb


def safe_workers(mb_per_worker=250, headroom_mb=3000, max_workers=None):
    """Workers that fit in free memory (minus headroom) and available CPUs."""
    _, _, avail = memory_mb()
    n = min(cpus(), max(1, (avail - headroom_mb) // mb_per_worker))
    return int(min(n, max_workers) if max_workers else n)


if __name__ == "__main__":
    mbw = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    head = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    lim, used, avail = memory_mb()
    print(f"cpus={cpus()} mem_limit_mb={lim} mem_used_mb={used} mem_available_mb={avail} "
          f"OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS')} safe_workers({mbw} MB each)={safe_workers(mbw, head)}")
