---
name: k8s-never-force-delete
description: >-
  Kubernetes deletion safety — never force-delete. Consult BEFORE any `kubectl delete`,
  and especially before reaching for `--force`, `--grace-period=0`, or editing/removing
  finalizers to make a stuck object go away. Graceful deletion only; diagnose stuck
  resources instead of forcing them. Triggers on: kubectl delete, --force, --grace-period,
  stuck Terminating, stuck namespace, remove finalizer, force delete pod/pvc/ns.
---

# Never force-delete in Kubernetes

## The rule

**Do not use `--force`, `--grace-period=0`, or strip finalizers to delete a Kubernetes
object.** Use a normal graceful `kubectl delete` and let termination complete. This applies
to every resource — pods, jobs, deployments, StatefulSets, PVCs, namespaces.

Specifically, never do (on your own initiative):

- `kubectl delete pod X --force --grace-period=0`
- `kubectl delete ... --grace-period=0`
- `kubectl patch ns/pvc ... -p '{"metadata":{"finalizers":[]}}'` (or `--finalize` /
  editing `finalizers` to `null`) to clear a "stuck Terminating" object
- `kubectl delete namespace X` when it hangs, then force-finalizing it

## Why it's dangerous

`--force --grace-period=0` deletes the API object **without confirming the workload actually
stopped**. Consequences:

- **StatefulSet / single-writer pods**: the replacement pod starts while the old container
  may still be running → **two writers at once** (split-brain), data corruption, duplicate
  external side effects. Force-deleting a StatefulSet pod is explicitly unsafe.
- **PVCs / volumes**: force/finalizer-stripping orphans the real backing volume or leaves it
  attached, and can lose data.
- **Namespaces**: clearing finalizers abandons real resources (cloud LBs, disks, external
  records) that the finalizer existed to clean up — silent leaks and cost.

A "stuck Terminating" object is a **symptom**, not the problem. Forcing it hides the cause.

## Do this instead

1. `kubectl describe` the object and look at events, `deletionTimestamp`, and `finalizers`.
2. Find what's blocking termination: a controller/operator, a volume that won't detach, an
   admission/finalizer webhook that's down, a node that's NotReady, a pod with a stuck
   preStop hook.
3. Fix the cause (bring the webhook/controller back, cordon+investigate the node, resolve the
   volume). Graceful deletion then completes on its own.
4. If a pod is stuck because its **node is genuinely gone**, delete/​drain the Node object (or
   let the node controller evict) rather than force-deleting the pod.

## The one exception

Force-delete only with **explicit human authorization**, on a **specifically diagnosed**
resource where the graceful path is confirmed impossible (e.g. a pod on a permanently-dead
node with no StatefulSet single-writer risk). Never as routine, never as a shortcut to "make
it go away," never on a StatefulSet pod without confirming the old container is truly dead.
State why in the moment.
