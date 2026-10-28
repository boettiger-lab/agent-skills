---
name: nrp-kubernetes
description: >
  Operating the NRP (National Research Platform / Nautilus) shared Kubernetes
  cluster with kubectl — deployments, pods, configmaps, rollouts, and diagnosing
  bad rollouts. Use whenever running kubectl against NRP (namespaces such as
  `biodiversity`, `geo-workflows` and `schmidtdse`). #1 safety rule: NEVER
  force-delete pods. A pod stuck in ContainerCreating or pulling an image for
  more than ~5 minutes is a bad node: gracefully delete it, never wait it out.
  Also covers batch Job requirements, secrets wiring, HAProxy ingress (CORS,
  timeouts), the dedicated Berkeley node, and NRP's pod usage policy (CPU/memory/GPU use vs
  request, the small-pod exemption, the 4-pod limit) and check-usage.py; read it
  before launching a batch job or when a rollout is denied with "utilization is
  too low".
metadata:
  author: boettiger-lab
  version: "1.3"
---

# NRP Nautilus — kubectl operations

NRP Nautilus is a **shared, multi-tenant** academic cluster. Be a good neighbor.

## ⛔ NEVER force-delete a pod

**Do not** run `kubectl delete pod ... --force --grace-period=0` (or `--force`).

Force-delete removes the pod from the API server *before* the kubelet confirms the
container stopped. On a shared cluster this:
- **orphans the container** — it can keep running on the node, consuming resources;
- **corrupts StatefulSet / RWO-PVC workloads** — the volume can end up
  double-mounted or two copies running at once;
- **violates NRP etiquette** and hides real problems.

If a pod is stuck `Terminating`, **investigate** (`describe`, events, node health)
or wait it out; escalate to NRP admins on Matrix. Never force.

## To reschedule a pod off a bad node — normal delete

A crashlooping/stuck pod caused by a **node** problem (DNS timeout, bad mount) is
fixed by a plain graceful delete — the controller recreates it, often on a healthy
node:

```bash
kubectl delete pod <pod> -n <ns>      # NO --force, NO --grace-period=0
```

### ⛔ A pod stuck in `ContainerCreating` / `Pulling` is a bad node — delete it, do not wait

On NRP an image pull that has not finished after **~5 minutes** is a network or DNS fault on
that node, not a slow download. It does not recover: on 2026-10-26 an orchestrator pod sat in
`Pulling image "bitnami/kubectl:latest"` on `nrp-00.rcac.purdue.edu` for 4 hours until the
runner's timeout killed it. One graceful delete would have cost a minute.

```bash
kubectl -n <ns> get pods | grep -E 'ContainerCreating|Pending'          # age > ~5 min?
kubectl -n <ns> describe pod <pod> | grep -E '^Node:|Pulling|Failed|Back-off'
kubectl -n <ns> delete pod <pod>                                        # graceful; the Job recreates it
```

If the replacement lands on the same node and hangs again, keep the workload off that node
with a `kubernetes.io/hostname NotIn [...]` node affinity (several manifests in
data-workflows already exclude known broken-egress hosts this way).

**Never let a script wait hours on a pod that never started.** A runner that only waits for
`Complete` with a long timeout turns a one-minute bad-node fix into a lost afternoon. Watch for
the stuck state explicitly and act on it:

```bash
# inside a wait loop: any pod of the job still not running after 5 min -> bad node, reschedule it
kubectl -n <ns> get pods -l job-name=<job> -o json | python3 -c '
import json, sys, datetime as d
now = d.datetime.now(d.timezone.utc)
for p in json.load(sys.stdin)["items"]:
    cs = (p["status"].get("containerStatuses") or [{}])[0].get("state", {})
    age = (now - d.datetime.fromisoformat(p["metadata"]["creationTimestamp"].replace("Z", "+00:00"))).total_seconds()
    if "waiting" in cs and age > 300: print(p["metadata"]["name"])' | xargs -r kubectl -n <ns> delete pod
```

The old ReplicaSet keeps serving until the new pod is `Ready`, so a crashlooping
*new* pod during a rollout is usually **not yet an outage**.

## Everyday ops

- **Always pass `-n <namespace>`.** Our apps live in `biodiversity` (and
  `schmidtdse` for some SchmidtDSE apps). Nothing is in `default`.
- **Config change → apply + restart:**
  ```bash
  kubectl apply -f k8s/configmap.yaml -n <ns>
  kubectl rollout restart deployment/<name> -n <ns>
  kubectl rollout status  deployment/<name> -n <ns> --timeout=90s
  ```
  Pods re-render `config.json` (envsubst) at start, so a restart is required for a
  ConfigMap change to take effect.
- **Deployment name ≠ repo name.** Check first: `kubectl get deploy -n <ns>`.
  (e.g. the geo-agent template deploys as `padus`; biodiversity as
  `biodiversity-maplibre`.)
- **Diagnose a bad rollout:**
  ```bash
  kubectl get pods -n <ns>
  kubectl describe pod <pod> -n <ns>            # State/Reason/Events
  kubectl logs <pod> -n <ns> -c <initContainer> # git-clone init failures show here
  ```

## Usage policy

Pods must use what they request. The NRP portal checks running pods every 10 minutes, and a pod is outside the policy when its use falls outside these ranges of its request:

| Resource | Allowed use | Checked only when the pod requests |
|---|---|---|
| GPU | above 40% | any GPU |
| CPU | 20%–200% | more than 1 core |
| Memory | 20%–150% | more than 2 GiB |

**Small pods are exempt.** A pod requesting at most 1 core is never checked on CPU, and one requesting at most 2 GiB is never checked on memory. Our web apps and MCP servers are designed around this exemption: they request 1 core or less and 2Gi or less, so they are never checked even though they sit idle most of the time. Do not raise them above either threshold. An idle server just over 2Gi would be checked and out of range.

**Never checked:** opportunistic (negative-priority) pods, JupyterHub pods, and pods younger than 30 minutes.

**The limit is 4 pods per user across all namespaces.** A user may have no more than 4 pods outside the ranges, counted over every namespace they use (`biodiversity`, `geo-workflows`, `schmidtdse`, …). Past that, the admission webhook `deployment.nrp-nautilus.io` denies every Deployment change on the account, including restarts of small exempt apps, with "Your pods resources utilization is too low for account …". Namespaces that keep requesting more than they use risk being banned. When a restart is denied this way, the cause is almost always a batch job in another namespace, not the app being restarted.

**Limits must stay close to requests.** NRP separately enforces a limit/request ratio (`container-must-meet-memory-and-cpu-ratio`). A memory limit 1.5 times the request has been rejected, and 1.2 times passes.

### Priority and sizing for batch jobs

- **Pods that run under about an hour** use `priorityClassName: opportunistic`. They are exempt from the usage check, and a preempted pod costs little to redo. This covers setup jobs, daily CronJob runs and short fan-out units.
- **Long work** is split into short units where that is practical, so it can run at opportunistic. Multi-hour pods at opportunistic are preempted repeatedly.
- **Pods that must run long** use default priority, and their requests are sized to measured use: memory 20–150% of the request, CPU 20–200%, and the limit no more than about 1.2 times the request. Check them about 30 minutes after launch, before the portal does, and keep the job under the 4-pod limit.

### Checking usage

`check-usage.py` in this skill's directory lists every pod the portal would check and flags those outside the ranges:

```bash
python3 <this skill's directory>/check-usage.py                    # biodiversity geo-workflows schmidtdse
python3 <this skill's directory>/check-usage.py geo-workflows      # one namespace
```

It reads pod specs with `kubectl` and use from NRP's Prometheus (`https://prometheus.nrp-nautilus.io`, no authentication needed), averaged over 30 minutes. It exits 1 when any checked pod is outside the policy. The portal's own measurement may differ in detail, so treat a result near a boundary as a warning. Run it:

- about 30 minutes after launching a job that requests more than 1 core or 2 GiB at default priority;
- before a rollout, if anything large is running;
- whenever the webhook denies a Deployment change.

Full policy: https://nrp.ai/documentation/userdocs/start/policies/ — per-user status: https://nrp.ai/userinfo/

## Batch Job Requirements

CPU jobs whose pods run under about an hour use `priorityClassName: opportunistic` (see Usage policy for longer pods). All jobs need explicit resource requests and limits, with the limit at most about 1.2 times the request, and `restartPolicy: Never`. GPU node avoidance is recommended:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: my-job
spec:
  backoffLimit: 2
  ttlSecondsAfterFinished: 10800
  template:
    spec:
      priorityClassName: opportunistic
      restartPolicy: Never
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: feature.node.kubernetes.io/pci-10de.present
                    operator: NotIn
                    values: ["true"]
      containers:
        - name: worker
          image: ghcr.io/boettiger-lab/datasets:latest
          command: ["bash", "-c", "echo hello"]
          resources:
            requests:
              cpu: "4"
              memory: "8Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
```

Add `ephemeral-storage` to requests/limits sized to the scratch disk the job needs. In `geo-workflows` 50Gi is only the LimitRange default, not a cap; larger requests are admitted, and node free disk is the real ceiling.

## Secrets

**S3 credentials** (`aws` secret):
```yaml
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom: {secretKeyRef: {name: aws, key: AWS_ACCESS_KEY_ID}}
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom: {secretKeyRef: {name: aws, key: AWS_SECRET_ACCESS_KEY}}
```

**Rclone config** (`rclone-config` secret):
```yaml
volumeMounts:
  - name: rclone-config
    mountPath: /root/.config/rclone
    readOnly: true
volumes:
  - name: rclone-config
    secret:
      secretName: rclone-config
```

## Ingress

NRP uses **HAProxy** (not nginx). TLS is cluster-terminated — just list the hostname, no cert secret needed.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    haproxy-ingress.github.io/cors-enable: "true"
    haproxy-ingress.github.io/cors-allow-origin: "*"
    haproxy-ingress.github.io/cors-allow-methods: "GET, POST, OPTIONS"
    haproxy-ingress.github.io/cors-allow-headers: "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization,mcp-session-id"
    haproxy-ingress.github.io/cors-allow-credentials: "true"
    haproxy-ingress.github.io/cors-max-age: "86400"
    haproxy-ingress.github.io/timeout-server: "600s"
    haproxy-ingress.github.io/timeout-tunnel: "3600s"  # required for SSE/WebSocket
spec:
  ingressClassName: haproxy
  tls:
    - hosts:
        - my-service.nrp-nautilus.io
  rules:
    - host: my-service.nrp-nautilus.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
```

Add `mcp-session-id` to `cors-allow-headers` for MCP servers.

## Dedicated Node

`stratus1.nrp-espm.berkeley.edu` is our Berkeley-owned node — use when jobs get preempted on shared nodes. It carries a `nautilus.io/issue` taint; tolerate it with `operator: Exists`:

```yaml
nodeSelector:
  kubernetes.io/hostname: stratus1.nrp-espm.berkeley.edu
tolerations:
  - key: "nautilus.io/issue"
    operator: Exists
    effect: NoSchedule
```

To discover taints on other nodes, check the scheduler error from a pending pod: `kubectl -n biodiversity describe pod <pod>` — the message lists every untolerated taint verbatim. Use exact `key`/`value` pairs (not `operator: Exists` globally — the admission webhook may reject it).

## Deployment Rollouts

Always `kubectl apply` ConfigMaps **before** restarting — `rollout restart` recycles pods using whatever is already in the cluster; git push alone does nothing:

```bash
kubectl apply -f k8s/my-configmap.yaml
kubectl -n biodiversity rollout restart deployment/<name>
```

**Stuck rollout?** If `rollout status` hangs >2 min, the pod likely landed on a broken node. Check with `kubectl -n biodiversity get pods -o wide` and `describe pod`. If it's a node issue (not your image), delete the stuck pod — it reschedules, and the old pod stays live throughout (`maxUnavailable: 0`):

```bash
kubectl -n biodiversity delete pod <stuck-pod>
```

## Common Pitfalls

1. **Default priority with oversized requests** — a pod above 1 core or 2 GiB that uses less than 20% of its request counts against the 4-pod limit, and past that NRP blocks every Deployment change on the account. Use opportunistic for short pods, and size long ones to measured use
2. **Missing resource requests/limits** — pod won't schedule
3. **`sleep` in batch jobs** — policy violation, grounds for ban
4. **`rollout restart` without `kubectl apply`** — config changes won't take effect
5. **nginx ingress annotations** — NRP uses HAProxy; nginx annotations are silently ignored
6. **Max 200 completions per indexed job** — hard cluster limit

## Don'ts

- No `--force` / `--grace-period=0` on pods (see above).
- Don't `kubectl delete` PVCs, StatefulSets, or Namespaces casually — data loss.
- Don't request more CPU/memory than you use (see Usage policy); don't schedule
  CPU work onto GPU nodes.
- Don't edit live objects with `kubectl edit` for tracked apps — change the
  manifest in the repo and `kubectl apply`, so git stays authoritative.
