# Tasks: Persistent Store on a Free Host

**Inputs**: [spec.md](spec.md), [plan.md](plan.md)

`[P]` marks tasks that can run in parallel. Tests are written first and must
fail before the implementation is written (constitution principle VIII).
Nothing here starts before the owner approves the spec and plan.

## Phase 1 – Research and local fixture

- [ ] T001 Read the Litestream release notes and pin a version; read the free limits of the intended storage and host and record them with the date in the plan.
- [ ] T002 [P] Test fixture: start a MinIO container, create a bucket, give the tests helpers to list, corrupt and empty it.
- [ ] T003 [P] Test fixture: build the image (once it exists) and run it with a command, a kill, a stop and a fresh disk.

**Checkpoint**: the tests can start and inspect a local bucket.

## Phase 2 – Restore and replicate (Story 1)

- [ ] T004 Tests for Story 1, scenarios 1–4: clean stop, kill, first start, immutability after restore. Include the version-1 upgrade case.
- [ ] T005 Add the write-ahead-logging option to `store.db.connect`, off by default, with a test that the command line is unchanged.
- [ ] T006 Write the Dockerfile and `litestream.yml.tmpl`.
- [ ] T007 Implement the restore path of `ops/entrypoint.py`: list the bucket, restore if a replica exists, start empty if it holds none, integrity check, start the command under replication.
- [ ] T008 Write `tools/kill_trials.py`: numbered claims at a steady rate, kill at a random moment, restore, report the largest loss. Run 20 trials and record them.

**Checkpoint**: SC-001 measured on the local bucket.

## Phase 3 – Refuse to overwrite (Story 2)

- [ ] T009 Tests for Story 2: unreachable endpoint, wrong credentials, truncated replica, bit-flipped replica, failed integrity check. Each must exit non-zero and leave the bucket unchanged.
- [ ] T010 Implement the "refuse" outcomes and the start record (FR-012).
- [ ] T011 Test and implement the graceful stop: pending changes flushed on SIGTERM within the grace period.

**Checkpoint**: SC-002 met; no failure path writes to the bucket.

## Phase 4 – One writer (Story 3)

- [ ] T012 Tests for the lease: live lease blocks, expired lease is taken over, losing the lease stops the service, renewal timing.
- [ ] T013 Implement `ops/lease.py` and wire it into the entrypoint.

**Checkpoint**: SC-003 met.

## Phase 5 – Package and document (Story 4)

- [ ] T014 Secrets test (SC-004): random secrets, search repository, image layers, logs and error output.
- [ ] T015 Measure restore time and store size (SC-005).
- [ ] T016 Measure one day of scripted use against the storage statistics; extrapolate a month (SC-006).
- [ ] T017 Write `ops/README.md`: create the bucket, set the secrets, deploy, check usage, restore by hand, what is lost on a kill.
- [ ] T018 Add the integration tests to continuous integration with a MinIO service; skip them where Docker is absent.

**Checkpoint**: everything passes locally and in continuous integration.

## Phase 6 – Real run

- [ ] T019 The owner creates a free bucket and a free host service following the guide, runs the service, stores data, forces a restart and confirms the data is back. Record the result, the date and the problems the guide had in the plan.
- [ ] T020 Update the guide with what T019 found; update `status.html`.
