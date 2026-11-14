# Implementation Plan: Persistent Store on a Free Host

**Feature**: `004-persistent-store` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)
**Status**: Draft – awaiting approval of the spec

## Summary

Wrap the existing store in a container that restores it from a private bucket
on start, replicates it continuously while running, and flushes it on stop.
Build the safety behaviour first (a failed restore never becomes an empty
store; one writer at a time), prove it against a local S3-compatible server,
and only then package it, document it and run it once against real free
services. No pipeline code changes.

## Technical context

| Item | Choice |
|---|---|
| Replication | Litestream, pinned version (chosen in T001 after reading the release notes) |
| Store | The SQLite file of spec 001, unchanged; write-ahead logging switched on for hosted runs |
| Storage | Any S3-compatible bucket; Cloudflare R2 intended |
| Entrypoint | A short Python script (`ops/entrypoint.py`): lease, restore, check, run |
| Lease | One small object in the bucket, written with a conditional put |
| Image | One Dockerfile: Python 3.12 slim, the Litestream binary, the package |
| Tests | pytest with a MinIO container; marked `integration`, skipped when Docker is absent |
| New dependencies | `boto3` inside the image and the `ops` test extra only; none for the product |

## Constitution check

| Principle | How this plan complies |
|---|---|
| I–VII | No change to claims, gate, rules or verdicts; nothing here touches a model. |
| II, V | A restore is verified byte-identical by `axiomate export`, so traceability and reproducibility carry over a restart. |
| VIII | Each phase starts with its tests; method, data and thresholds are in the spec. |
| IX | `status.html` updated at each checkpoint. |

No violations.

## Project structure

```
ops/
  Dockerfile          # the image
  entrypoint.py       # lease → restore → integrity check → run under replication
  lease.py            # take, renew, release, expire; conditional put
  litestream.yml.tmpl # settings filled from environment variables
  README.md           # the deployment guide (FR-016)
tests/ops/
  conftest.py         # starts MinIO, builds the image, helpers to kill and restore
  test_restore.py     # Story 1
  test_failed_restore.py  # Story 2
  test_lease.py       # Story 3
  test_secrets.py     # SC-004
tools/
  kill_trials.py      # writes numbered claims, kills at random, reports the loss
specs/004-persistent-store/
```

`src/axiomate/` is not changed, except for one setting: `store.db.connect`
accepts an option to switch on write-ahead logging, off by default, so the
command line behaves as before.

## Design decisions

1. **Replication, not shutdown-save.** Free hosts stop containers with a few
   seconds of warning, or none. A copy made only at stop is lost on a crash.
   Litestream ships every committed change within about a second, so the loss
   window is seconds, not a whole session.
2. **The entrypoint is the safety logic; Litestream is the mechanism.** The
   order is fixed: take the lease → decide *restore / empty / refuse* → check
   integrity → start the command under `litestream replicate -exec`. Litestream's
   own "restore if the replica exists" flags are not trusted to tell an empty
   bucket from an unreachable one, so the entrypoint lists the bucket itself
   first and only then calls restore.
3. **Three start outcomes, never a fourth.** *Restored*, *started empty* (the
   bucket answered and holds nothing for this store) or *refused* (anything
   else). Anything ambiguous is refused. A refused start writes nothing.
4. **Single writer through a lease object.** The object holds the container id
   and a renewal time. It is created with a conditional put ("only if absent");
   a live lease blocks a second container; a lease not renewed within the
   expiry (default 60 s, renewed every 15 s) may be replaced with a conditional
   put on its previous version. Renewal runs beside the service; losing the
   lease stops the service rather than let two replicate.
5. **Integrity before use.** After a restore, `PRAGMA integrity_check` and the
   schema-version check run before the store is handed to the service. The
   in-place upgrade of spec 002 then runs as it does today.
6. **WAL on, set by the entrypoint.** Litestream needs write-ahead logging. It
   is switched on for hosted runs only. A long write transaction blocks
   replication of later changes, so the service keeps transactions short; the
   store code already commits per operation.
7. **Retention.** Snapshots every 24 hours, kept for 7 days; older data is
   pruned. This bounds storage far below the free limit for a store of this
   size and still leaves a week of fallbacks.
8. **Secrets only through the environment.** `AXIOMATE_S3_ENDPOINT`,
   `AXIOMATE_S3_BUCKET`, `AXIOMATE_S3_ACCESS_KEY_ID`,
   `AXIOMATE_S3_SECRET_ACCESS_KEY`, plus settings with defaults (path, interval,
   retention, lease expiry). The entrypoint never prints them and errors are
   rewritten to drop any value that looks like one of them.
9. **No data in the image.** The store file is created or restored at start.
   The image is the same for every user; the bucket makes it theirs.
10. **Provider-neutral.** Only the S3 protocol is used, so R2, Backblaze B2 or
    a self-run MinIO differ only in settings.

## Cost and limits

To be written from the providers' pages when T001 is done, with the date.
Expected shape: storage far below 1 GB for this store, and request counts
driven by changes, not by time, because Litestream uploads only when the store
changes. The lease renewal adds about 4 small requests a minute while the
service runs, which is checked against the free request limit in T016.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Replication tool bug or format change between versions | Unrecoverable replica | Pin the version; the restore test runs on every change; `axiomate export` remains a manual second copy |
| Free-tier terms change | Service stops or costs money | S3-only design; change the settings to move; the guide says where to check the limits |
| Overlap during redeploy | Two writers | The lease; tested in Story 3 |
| A host kills faster than the sync interval | A few seconds lost | Reported by the kill trials; stated in the guide |
| Credentials leak in logs | Bucket exposed | Rewriting of errors; a test that searches output for the secrets |
| Lease expiry too short for a long outage of storage | The service stops itself | Default 60 s; the service stops cleanly and the host restarts it |

## Phases

1. **Research and local fixture** – pin the tool, read the limits, MinIO fixture.
2. **Restore and replicate (Story 1)** – the happy path and the kill trials.
3. **Refuse to overwrite (Story 2)** – the failure injections.
4. **One writer (Story 3)** – the lease.
5. **Package and document (Story 4)** – image, guide, secrets test, limits.
6. **Real run** – the owner's one run against real free services.
