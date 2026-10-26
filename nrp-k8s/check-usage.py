#!/usr/bin/env python3
"""Check running pods against the NRP usage policy.

A running pod is outside the policy when its use falls outside these ranges of
its request: GPU above 40%, CPU 20%-200%, memory 20%-150%. CPU is checked only
on pods requesting more than 1 core, memory only on pods requesting more than
2 GiB. Opportunistic (negative-priority) pods, JupyterHub pods and pods younger
than 30 minutes are not checked. A user may have at most 4 pods outside the
ranges across all their namespaces.

Pod specs come from kubectl; use comes from NRP's Prometheus, averaged over the
last 30 minutes. The portal's own measurement may differ in detail, so treat a
result near a boundary as a warning.

Usage: check-usage.py [namespace ...]   (default: biodiversity geo-workflows schmidtdse)
Exit status is 1 when any checked pod is outside the policy.
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

PROM = "https://prometheus.nrp-nautilus.io/api/v1/query"
DEFAULT_NAMESPACES = ["biodiversity", "geo-workflows", "schmidtdse"]
GIB = 1024 ** 3
ALLOWANCE = 4
MIN_AGE_MIN = 30
WINDOW = "30m"


def cpu_cores(q):
    q = str(q)
    if q.endswith("m"):
        return float(q[:-1]) / 1000
    return float(q)


def mem_bytes(q):
    q = str(q)
    units = {"Ki": 1024, "Mi": 1024 ** 2, "Gi": 1024 ** 3, "Ti": 1024 ** 4,
             "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
    for u in sorted(units, key=len, reverse=True):
        if q.endswith(u):
            return float(q[: -len(u)]) * units[u]
    return float(q)


def prom(query):
    url = PROM + "?" + urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    out = {}
    for row in data["data"]["result"]:
        m = row["metric"]
        key = (m.get("namespace") or m.get("exported_namespace"), m.get("pod") or m.get("exported_pod"))
        out[key] = out.get(key, 0.0) + float(row["value"][1])
    return out


def pods(namespace):
    res = subprocess.run(["kubectl", "-n", namespace, "get", "pods", "-o", "json"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(f"warning: cannot read pods in {namespace}: {res.stderr.strip()}", file=sys.stderr)
        return []
    return json.loads(res.stdout)["items"]


def is_jupyterhub(pod):
    labels = pod["metadata"].get("labels", {})
    return labels.get("component") == "singleuser-server" or labels.get("app") == "jupyterhub"


def main():
    namespaces = sys.argv[1:] or DEFAULT_NAMESPACES
    sel = "|".join(namespaces)
    mem_use = prom(f'sum by (namespace, pod) (avg_over_time(container_memory_working_set_bytes{{namespace=~"{sel}",container!=""}}[{WINDOW}]))')
    cpu_use = prom(f'sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{{namespace=~"{sel}",container!=""}}[{WINDOW}]))')
    gpu_use = prom(f'avg by (namespace, pod) (avg_over_time(DCGM_FI_DEV_GPU_UTIL{{namespace=~"{sel}"}}[{WINDOW}]))')
    now = datetime.now(timezone.utc)

    checked, outside = [], []
    for ns in namespaces:
        for pod in pods(ns):
            name = pod["metadata"]["name"]
            spec, status = pod["spec"], pod.get("status", {})
            if status.get("phase") != "Running":
                continue
            if spec.get("priority", 0) < 0 or is_jupyterhub(pod):
                continue
            started = status.get("startTime")
            if not started:
                continue
            age = (now - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds() / 60
            if age < MIN_AGE_MIN:
                continue

            req_cpu = req_mem = req_gpu = 0.0
            for c in spec.get("containers", []):
                r = c.get("resources", {}).get("requests", {})
                req_cpu += cpu_cores(r.get("cpu", 0))
                req_mem += mem_bytes(r.get("memory", 0))
                req_gpu += float(r.get("nvidia.com/gpu", 0))

            problems, notes = [], []
            if req_cpu > 1:
                use = cpu_use.get((ns, name), 0.0)
                pct = 100 * use / req_cpu
                notes.append(f"cpu {use:.2f}/{req_cpu:g} cores {pct:.0f}%")
                if not 20 <= pct <= 200:
                    problems.append("cpu")
            if req_mem > 2 * GIB:
                use = mem_use.get((ns, name), 0.0)
                pct = 100 * use / req_mem
                notes.append(f"mem {use / GIB:.1f}/{req_mem / GIB:g}Gi {pct:.0f}%")
                if not 20 <= pct <= 150:
                    problems.append("memory")
            if req_gpu > 0:
                use = gpu_use.get((ns, name))
                if use is None:
                    notes.append("gpu use unknown")
                else:
                    notes.append(f"gpu {use:.0f}%")
                    if use <= 40:
                        problems.append("gpu")
            if not notes:
                continue  # small pod: exempt on every resource
            row = f"{ns}/{name}  age {age:.0f}m  " + ", ".join(notes)
            checked.append(row)
            if problems:
                outside.append(row + "  OUTSIDE: " + ", ".join(problems))

    print(f"Checked pods (above 1 core or 2 GiB, at least {MIN_AGE_MIN} min old, not opportunistic): {len(checked)}")
    for row in checked:
        print("  " + row)
    print(f"Outside the policy: {len(outside)} (allowance {ALLOWANCE} across all namespaces)")
    for row in outside:
        print("  " + row)
    return 1 if outside else 0


if __name__ == "__main__":
    sys.exit(main())
