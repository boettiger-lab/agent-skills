---
name: nrp-k8s
description: "Deploy and manage workloads on the NRP Nautilus Kubernetes cluster. Covers batch jobs (opportunistic priority class, resource requests, GPU node avoidance), ingress with HAProxy CORS and timeout annotations, NRP usage policies, and credential wiring. TRIGGER when the user mentions: kubectl, k8s, kubernetes, NRP, Nautilus, rollout, restart deployment, apply yaml, pod, job, namespace, ingress, or any cluster operation. Namespace is 'biodiversity'. Always load this skill BEFORE running any kubectl command."
license: Apache-2.0
---

# NRP Kubernetes

Shared academic cluster. Namespace: `biodiversity`. [Usage policies](https://nrp.ai/documentation/userdocs/start/policies/) — key rules: no `sleep` in jobs, resource requests must reflect actual usage (~20% tolerance), no interactive pods >6h.

## Batch Job Requirements

All CPU jobs need `priorityClassName: opportunistic`, explicit resource requests=limits, and `restartPolicy: Never`. GPU node avoidance is recommended:

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

Add `ephemeral-storage: "250Gi"` to requests/limits if scratch disk is needed.

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

1. **No `priorityClassName: opportunistic`** — required for all CPU jobs
2. **Missing resource requests/limits** — pod won't schedule
3. **`sleep` in batch jobs** — policy violation, grounds for ban
4. **`rollout restart` without `kubectl apply`** — config changes won't take effect
5. **nginx ingress annotations** — NRP uses HAProxy; nginx annotations are silently ignored
6. **Max 200 completions per indexed job** — hard cluster limit
