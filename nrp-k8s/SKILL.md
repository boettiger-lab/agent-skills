---
name: nrp-k8s-batch
description: "Run batch processing jobs on the NRP (National Research Platform) Nautilus Kubernetes cluster. Covers the mandatory requirements for CPU jobs: opportunistic priority class, resource requests/limits, and GPU node avoidance. Use when creating or managing Kubernetes jobs on the NRP Nautilus cluster, or when the user mentions NRP, Nautilus, or needs to run batch workloads on a shared academic cluster."
license: Apache-2.0
compatibility: "Requires kubectl configured for the NRP Nautilus cluster (namespace: biodiversity)."
metadata:
  author: boettiger-lab
  version: "1.0"
---

# NRP Kubernetes Batch Jobs

The NRP (National Research Platform) Nautilus cluster is a shared academic Kubernetes cluster. Read the [NRP usage policies](https://nrp.ai/documentation/userdocs/start/policies/) before running jobs. Key rules:

- **No `sleep` commands** in batch jobs — this is grounds for a ban
- **Resource requests must reflect actual usage** — limits must be within ~20% of requests; pods that chronically over- or under-use their allocation violate policy
- **Long-running Deployments** are auto-deleted after 2 weeks unless whitelisted; use Job controllers for batch work
- **Interactive pods** are limited to 6 hours, 2 GPUs, 32GB RAM, 16 cores

## Namespace

All our jobs run in the `biodiversity` namespace:

```bash
kubectl -n biodiversity get jobs
```

## Mandatory Requirements for CPU Jobs

### 1. Priority class (REQUIRED)

All CPU jobs **must** use the `opportunistic` priority class. This makes pods preemptible so they don't block GPU users. Without this, your job may be rejected or cause problems for other users.

```yaml
spec:
  template:
    spec:
      priorityClassName: opportunistic
```

### 2. Resource requests and limits (REQUIRED)

The NRP cluster **requires** both `requests` and `limits` on every container. Jobs without resource specifications will not be scheduled. Set requests equal to limits, and **request only what you will actually use** — the policies require utilization to stay within ~20% of your request:

```yaml
resources:
  requests:
    cpu: "4"
    memory: "8Gi"
  limits:
    cpu: "4"
    memory: "8Gi"
```

If you need ephemeral scratch disk, request it explicitly:

```yaml
resources:
  requests:
    cpu: "4"
    memory: "32Gi"
    ephemeral-storage: "250Gi"
  limits:
    cpu: "4"
    memory: "32Gi"
```

### 3. GPU node avoidance (recommended)

To avoid wasting GPU node capacity on CPU-only work, add a node anti-affinity:

```yaml
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: feature.node.kubernetes.io/pci-10de.present
                    operator: NotIn
                    values: ["true"]
```

## Minimal Job Example

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

## Secrets

Two secrets are available in the `biodiversity` namespace. See the [nrp-s3 skill](../nrp-s3/SKILL.md) for full details on S3 environment variables.

### `aws` — S3 credentials (environment variables)

```yaml
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: aws
        key: AWS_ACCESS_KEY_ID
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: aws
        key: AWS_SECRET_ACCESS_KEY
```

### `rclone-config` — Rclone configuration (volume mount)

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

NRP uses **HAProxy** as its ingress controller (not nginx). CORS and timeouts are configured via HAProxy annotations on the Ingress resource, not in the application or Service.

Hostnames follow the pattern `<service>.nrp-nautilus.io`. TLS is terminated by the cluster — just list the hostname under `tls.hosts`, no certificate secret needed.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    # CORS — required for browser clients (maps, MCP tools, etc.)
    haproxy-ingress.github.io/cors-enable: "true"
    haproxy-ingress.github.io/cors-allow-origin: "*"
    haproxy-ingress.github.io/cors-allow-methods: "GET, POST, OPTIONS"
    haproxy-ingress.github.io/cors-allow-headers: "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization,mcp-session-id"
    haproxy-ingress.github.io/cors-allow-credentials: "true"
    haproxy-ingress.github.io/cors-max-age: "86400"
    # Extended timeouts for long-lived connections (MCP, WebSockets)
    haproxy-ingress.github.io/timeout-server: "600s"
    haproxy-ingress.github.io/timeout-tunnel: "3600s"
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

The `mcp-session-id` header in `cors-allow-headers` is needed if the service hosts an MCP server. The extended `timeout-tunnel` is required for SSE or WebSocket connections that would otherwise be dropped after the default HAProxy idle timeout.

## Common Pitfalls

1. **Missing resource requests/limits** — Jobs will not schedule without them.
2. **Forgetting `priorityClassName: opportunistic`** — Required for all CPU jobs.
3. **Using `sleep` in batch jobs** — Violates policy and can result in a ban.
4. **Over-requesting resources** — Chronic under-utilization violates policy. Request what you'll actually use.
5. **Max 200 completions per indexed job** — Hard limit to avoid overwhelming the cluster's etcd.
6. **Using nginx ingress annotations** — NRP uses HAProxy; nginx annotations are silently ignored.
7. **Expecting TLS certificates to auto-provision** — Just list the hostname under `tls.hosts`; the cluster handles termination.
