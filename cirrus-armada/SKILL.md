---
name: cirrus-armada
description: Running batch jobs on the lab's cirrus cluster through its Armada queue (armadactl context `cirrus`). Use before submitting, watching or cancelling cirrus Armada jobs, sizing their memory or GPU requests, choosing nodes, or moving data in and out of them. Covers the difference from NRP's Armada (`main`), the job spec, nodes and GPUs, MinIO for data and logs, and how to check job state without kubectl.
---

# Lab Armada on cirrus

## Two Armada clusters

`~/.armadactl.yaml` has two contexts, and the default is NRP.

| Context | Cluster | Notes |
|---|---|---|
| `main` | NRP Armada (armada.nrp-nautilus.io) | Shared; NRP usage policy applies (see the `nrp-kubernetes` skill) |
| `cirrus` | Lab k3s cluster (armada-api.carlboettiger.info) | Carl's own machines; namespace `armada-jobs`; queue `cboettig` |

Always write `armadactl -c cirrus ...`. A bare `armadactl` goes to NRP. Name the cluster in every message about Armada.

The user may have access to both. This skill covers only cirrus. For work on NRP's Armada, read the
`nrp-kubernetes` skill (its "Armada on NRP" section: the usage policy applies to every Armada pod, and
preempted jobs are not rescheduled) and the `armada-pipeline` and `pod-preemption` skills in
boettiger-lab/data-workflows. Choose cirrus for long single jobs that cannot meet NRP's usage policy, and
NRP for large fan-outs of short units.

## Access

- There is no kubectl access to cirrus from the Jupyter pod. Carl applies cirrus kubectl himself, including
  creating secrets in `armada-jobs`.
- Do not use the pod's service-account token.
- Problems with the cluster itself (scheduler, executor, nodes) go to Carl or his armada agent. Do not work
  around them by hand.

## Job spec

Submit with `armadactl -c cirrus submit jobs.yaml`. A minimal spec:

```yaml
queue: cboettig
jobSetId: myproject-experiment1        # group related jobs; watch and cancel by job set
jobs:
  - priority: 1
    namespace: armada-jobs
    annotations: {myproject/task: "instance-a solver-x"}   # shows up in watch output; use it to label tasks
    podSpec:
      restartPolicy: Never
      priorityClassName: armada-default
      tolerations:
        - {key: dedicated, operator: Equal, value: gb10}  # lets the job use the GB10 nodes
      containers:
        - name: worker
          image: ghcr.io/boettiger-lab/<image>:<sha12>    # pin a tag, never :latest
          command: ["bash", "-c", "..."]
          env:
            - {name: OMP_NUM_THREADS, value: "1"}
            - name: NODE_NAME
              valueFrom: {fieldRef: {fieldPath: spec.nodeName}}
          resources:
            requests: {cpu: "1", memory: "16Gi"}
            limits:   {cpu: "1", memory: "16Gi"}
          volumeMounts: [{name: work, mountPath: /work}]
      volumes:
        - {name: work, emptyDir: {sizeLimit: 30Gi}}
```

- Generate specs from a task list with a script rather than writing them by hand. hexplanner's
  `scripts/armada_cirrus.py` is a worked example: one job per TSV line, the source tarball uploaded to MinIO
  and unpacked at start, results uploaded at the end.
- Set requests equal to limits. Size memory from measured peaks. Oversized memory requests are what keep jobs
  queued, because the queue has a total memory cap.
- Record the node and the CPU model in each job's output (`NODE_NAME`, `/proc/cpuinfo`) so results can be
  attributed to hardware.

## Nodes and GPUs

- Nodes have different CPUs, including an AMD Threadripper 3990X (cirrus), a Ryzen 9 3900X (thelio) and two
  NVIDIA GB10 systems with Arm Grace cores (nimbus, nimbus3). A GB10 core is about 2 to 2.5 times faster than a
  Threadripper core on single-thread work, so timings from different nodes are not comparable.
- By default let Armada place jobs. When a benchmark needs one CPU type, pin it with a node selector; on
  2026-11-16 `nodeSelector: {kubernetes.io/arch: arm64}` placed jobs on the GB10s. Images used there must be
  built for arm64 (multi-arch).
- GB10 nodes carry the taint `dedicated=gb10`; jobs need the toleration above. LLM pods on the GB10s have
  priority over batch jobs.
- GPUs (Quadro RTX 8000s and GB10s) are time-sliced into 8 `nvidia.com/gpu` slices. Slices are bookkeeping:
  every pod sees the whole card and its memory. Request 1 slice normally, or 8 to keep a GPU to one job for
  timing. GB10 GPU memory is the machine's unified RAM, so the pod's memory request is what reserves it.

## Data and logs

- Pods cannot be inspected while they run, and their logs are not retrievable afterwards. Write every log and
  result to object storage before the job exits, including on failure (`trap` in the entry script).
- Use the lab MinIO (https://minio.carlboettiger.info) with a bucket-scoped key per project. Carl puts the key
  in a k8s secret in `armada-jobs`; jobs read it with `secretKeyRef`. Keep the local copy in
  `~/.config/<project>/`, never print it, and never put a key in a job spec or a repo.
- rclone works without a config file through environment variables (`RCLONE_CONFIG_S3_TYPE=s3`,
  `RCLONE_CONFIG_S3_PROVIDER=Minio`, `RCLONE_CONFIG_S3_ENV_AUTH=true`, `RCLONE_CONFIG_S3_ENDPOINT=...`,
  `RCLONE_CONFIG_S3_NO_CHECK_BUCKET=true`).
- Copy results back with a collect script (hexplanner's `scripts/collect_cirrus.py`).

## Job state

- `armadactl -c cirrus watch cboettig <jobset> --raw` streams the job set's event history, one JSON event per
  line, and then waits. Run it under `timeout` and parse the history: `JobSubmittedEvent` carries the
  annotations, `JobRunningEvent` the node, `JobFailedEvent` the reason (`OOMKilled` means the memory limit was
  hit). hexplanner's `scripts/armada_status.py` summarizes job sets this way.
- `armadactl -c cirrus get queue-report cboettig` shows the last scheduling round and the allocated
  resources; `get job-report <job-id>` explains why one job is not scheduled.
- `armadactl -c cirrus cancel job-set cboettig <jobset>` cancels a job set.
- Armada does not always queue a job that cannot fit now. When pods it does not manage (the LLM pods on the
  GB10s) hold a node's memory, it fails the job at submission with "insufficient resources available", in
  the same second as `JobSubmittedEvent`. Resubmit later, or loop until the job is accepted (hexplanner's
  `scripts/armada_submit_retry.sh`). A job that is accepted and then killed with exit code 137 but no
  `OOMKilled` was probably killed for memory pressure on the node, not for exceeding its own limit.
- To wait for jobs, run a background loop that checks every 10 minutes and exits when nothing is queued or
  running; do not poll by hand.
