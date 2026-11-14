# Feature Specification: Persistent Store on a Free Host

**Feature**: `004-persistent-store`
**Created**: 2026-11-14
**Status**: Draft – awaiting approval by the repository owner
**Domain**: Operation of the claim store (no change to the pipeline)
**Builds on**: [001-claim-foundation](../001-claim-foundation/spec.md) (the store),
[002-interpretation-gate](../002-interpretation-gate/spec.md) (schema version 2)
**Relates to**: `003-web-ui` (ideation only; it will run on top of this feature)

## Purpose

Axiomate keeps everything it knows in one SQLite file. Free hosting services
run an application in a disposable container: the disk is erased when the
service goes idle, restarts or is redeployed. Without a remedy, every claim,
flag and assumption collected so far would be lost each time.

This feature makes the store survive. The SQLite file is replicated
continuously to private object storage, and restored when the container
starts. It adds no pipeline stage and changes no claim, rule or verdict. It
belongs to the operation of stage 5 (claim store).

It delivers a container image that runs *any* Axiomate command under
replication. The web service that will run inside it belongs to `003-web-ui`
and is not part of this feature.

## User Scenarios

### Story 1 – Data survives a restart (Priority: P1)

The owner uses a hosted Axiomate, stores documents and claims, and the host
puts the service to sleep or restarts it. On the next start, everything stored
before is there, identical.

**Why this priority**: this is the whole point of the feature. Without it a
hosted store is a toy.

**Independent test**: run the container, store the development filings and the
hand-written claims, stop it in each of the ways a host can (clean stop, kill),
start a fresh container with an empty disk, and compare `axiomate export`
before and after.

**Acceptance scenarios**:

1. **Given** a running service with stored data, **when** the container is
   stopped normally, **then** a fresh container with an empty disk starts with
   an identical store.
2. **Given** a running service, **when** the container is killed without
   warning, **then** a fresh container starts with every write that was made
   more than a few seconds before the kill.
3. **Given** the very first start, with no replica yet, **when** the service
   starts, **then** it starts with an empty store and begins replicating.
4. **Given** a restored store, **when** an attempt is made to alter or delete
   a stored claim, **then** it is refused exactly as before the restart.

### Story 2 – A failed restore never becomes an empty store (Priority: P1)

If the replica cannot be read (the storage is unreachable, the credentials are
wrong, the copy is damaged), the service must not start with an empty store
and begin replicating that emptiness over the real data.

**Why this priority**: the worst outcome of this feature is not downtime but a
silent overwrite of the only copy.

**Independent test**: start the container with an unreachable bucket, wrong
credentials and a damaged replica; confirm that each time it exits with an
error, serves nothing, and writes nothing to the replica.

**Acceptance scenarios**:

1. **Given** a replica exists and cannot be read, **when** the container
   starts, **then** it exits with an error naming the cause and writes nothing
   to storage.
2. **Given** a replica exists and the restored file fails an integrity check,
   **when** the container starts, **then** it exits with an error and keeps the
   replica untouched.
3. **Given** no replica exists *and* storage is reachable, **when** the
   container starts, **then** it starts empty (Story 1, scenario 3). No replica
   is told apart from an unreachable one explicitly, never by assumption.

### Story 3 – One writer at a time (Priority: P2)

During a redeploy a host may briefly run the old and the new container
together. Two containers replicating one store would write divergent copies.

**Independent test**: start a second container while the first is running and
confirm that it refuses to start, and that the first is unaffected.

**Acceptance scenarios**:

1. **Given** a running container holding the lease on the replica, **when** a
   second container starts, **then** the second exits with an error naming the
   lease, and the replica is unchanged.
2. **Given** a container that was killed and cannot release its lease,
   **when** the lease has not been renewed for its expiry time, **then** a new
   container takes it over and starts.

### Story 4 – The owner can run it in minutes, free (Priority: P3)

The owner follows a short guide, creates a free storage bucket and a free host
service, sets the secrets, and has a working deployment.

**Independent test**: the guide is followed on a clean account by someone who
did not write it, and it ends with a restored store.

**Acceptance scenarios**:

1. **Given** the guide, **when** it is followed, **then** it states what each
   secret is, where it is set, and what it costs (nothing within the free
   limits).
2. **Given** the free limits, **when** the service runs, **then** the guide
   says what is used and how to see it.

### Edge cases

- The first start after a **schema upgrade** (version 1 store restored by a
  version 2 program): the store is restored, then upgraded in place as today,
  and the upgraded file is replicated.
- A **cold start** restores a store that has grown large; restore time grows
  with size (see SC-005).
- The container disk is **full** or read-only.
- The replica contains **older generations**; retention removes them without
  removing the newest recoverable state.
- **Clock skew** between the container and storage affects the lease.
- The storage service has a **short outage** while the service is running:
  writes continue locally and replication catches up.
- Credentials are **rotated** while a container is running.

## Requirements

### Functional requirements – replication and restore

- **FR-001**: The store file MUST be replicated continuously to a private
  S3-compatible bucket while the service runs.
- **FR-002**: On start, if no local store file exists and a replica exists,
  the system MUST restore the newest recoverable state before anything else
  runs.
- **FR-003**: On start, if no local store file exists and storage is
  reachable and holds no replica for this store, the system MUST start with an
  empty store.
- **FR-004**: On start, if a replica exists but cannot be read, or the
  restored file fails `PRAGMA integrity_check`, the system MUST exit with an
  error and MUST NOT write to the bucket.
- **FR-005**: On a normal stop (SIGTERM), the system MUST finish replicating
  pending changes before exiting, within the host's grace period.
- **FR-006**: A restored store MUST be identical to the replicated one:
  `axiomate export` of the two is byte-identical, and the immutability
  triggers of the schema are present.
- **FR-007**: After a restore the system MUST bring the store to the current
  schema version using the existing in-place upgrade, then continue
  replicating the upgraded file.
- **FR-008**: Old replica data MUST be pruned by a retention rule, and pruning
  MUST never remove the newest recoverable state.

### Functional requirements – safety

- **FR-009**: A lease object in the bucket MUST ensure at most one container
  replicates a given store. A container that cannot take the lease MUST exit
  with an error. A lease not renewed within its expiry time MAY be taken over.
- **FR-010**: Credentials MUST be read from environment variables supplied by
  the host. They MUST NOT be in the repository, in the image, in logs or in
  error messages.
- **FR-011**: The bucket MUST be private. Only the store file's replica and
  the lease are written to it.
- **FR-012**: Every start MUST log what it did (restored, started empty,
  refused) and the replica's last known position, without secrets.

### Functional requirements – packaging

- **FR-013**: One container image MUST run any `axiomate` command, or any
  other command given to it, under replication.
- **FR-014**: The image MUST contain no data: no filings, claims or replies.
- **FR-015**: All settings (bucket, endpoint, store path, sync interval,
  retention, lease expiry) MUST come from environment variables with
  documented defaults.
- **FR-016**: The repository MUST contain a deployment guide for a free
  storage bucket and a free host service, with the limits of each and how to
  check usage.

### Key entities

- **Replica**: the continuously updated copy of the store in the bucket.
- **Lease**: a small object in the bucket naming the container that currently
  owns the replica and when it last renewed.
- **Start record**: the log line of what a start did.

## Out of scope

- The web service, its API and user interface (`003-web-ui`).
- Replicating to Git, or any data export in a human-readable form (decided
  2026-11-14 to defer; may become a later feature).
- Several simultaneous writers, sharding or any scale beyond one SQLite file.
- Point-in-time recovery for the user. Retention exists to bound storage.
- Backing up the stored model replies (`eval/replies/`), which live in the
  repository.
- Choosing or paying for a paid host.

## Success criteria

- **SC-001**: After a clean stop and after a kill, a fresh container's store
  export is identical to the export before the stop, for every write made
  more than 5 seconds before a kill, and for every write before a clean stop.
- **SC-002**: In every failure start (unreachable bucket, wrong credentials,
  damaged replica, failed integrity check) the container exits with an error
  and writes nothing to the bucket: 100% of injected failures.
- **SC-003**: A second container started while the first holds the lease
  always refuses to start, and a container started after the lease expired
  always starts: 100%.
- **SC-004**: No secret value appears in the repository, the image layers, the
  logs or the error output of any test.
- **SC-005**: Restoring the store of the development data takes no more than
  30 seconds, and the measured time is reported with the store's size.
- **SC-006**: A month of expected use stays within the free limits of the
  storage service. The expected use and the limits are written in the guide.

## Verification

This feature covers the operation of stage 5. It adds no pipeline stage. The
project-wide strategy is in [../verification.md](../verification.md); its
principle (VIII) is applied here: method, data and threshold are fixed before
the work is built.

| What is verified | Method | Data | Threshold |
|---|---|---|---|
| Clean stop loses nothing (SC-001) | Store data, `docker stop`, restore on an empty disk, compare `axiomate export` | The development filings and the 21 hand-written claims of spec 001, plus the interpretation counts of spec 002 | Exports identical |
| A kill loses at most the last seconds (SC-001) | Write numbered claims at a steady rate, kill the container at a random moment, restore, find the last restored claim; 20 trials | Generated claims in the claim schema | Every claim written more than 5 s before the kill is present; report the largest loss in seconds |
| Failed restore never becomes an empty store (SC-002) | Inject each failure and compare the bucket's contents before and after | Bucket with a good replica; unreachable endpoint; wrong key; truncated and bit-flipped replica | Exit code non-zero; bucket unchanged: 100% |
| First start is empty and replicates (Story 1) | Start against an empty bucket, write one claim, restore elsewhere | Empty bucket | One claim restored |
| Restored store is as before (FR-006) | After restore: `integrity_check`; try `UPDATE` and `DELETE` on a claim | Restored development store | Check passes; both attempts refused |
| Upgrade after restore (FR-007) | Replicate a version 1 store, restore with the current program | A version 1 store built from spec 001 fixtures | Upgraded, export equals the upgrade of the original |
| Single writer (SC-003) | Start a second container; start another after the first was killed and the lease expired | Same bucket | Refused while live; accepted after expiry: 100% |
| No secrets leak (SC-004) | Search repository, image layers, logs and test output for the secret values used in the tests | Random secrets generated for the run | None found |
| Restore time (SC-005) | Time the restore of the development store | Development store | ≤ 30 s, reported with size |
| Within free limits (SC-006) | Count requests and bytes from the storage's own statistics over a day of scripted use, then extrapolate | One day of typical use (about 200 writes) | Extrapolated month below the limits in the guide |
| The guide works (Story 4) | A person follows it on a clean account | Real free bucket and host | Ends with a restored store; recorded once |

**Data collection**

- **Automated tests** run against a local S3-compatible server (MinIO) in a
  container, in continuous integration. They never touch a real account.
- **One real run** against a real free bucket and a real free host is made by
  the repository owner when the feature is built, and its result is recorded
  in the plan. It is the only check that the real service behaves like the
  local one.
- Test data are the project's own development fixtures; no new data is
  collected.

**What these checks will not show**

- Behaviour under a real host's shutdown policy, which differs between hosts
  and changes over time. The kill test simulates the worst case, not a
  particular host.
- Free limits and prices as they will be later: they are read from the
  providers when the feature is built and stated with the date.
- Loss caused by a bug in the replication tool itself beyond the cases tested.
  The owner keeps the option of a manual `axiomate export` as a second copy.

## Dependencies and assumptions

- **Replication tool**: Litestream, open source, run next to the service. The
  version is pinned in the plan after reading its release notes.
- **Storage**: a free S3-compatible bucket; Cloudflare R2 is the intended
  choice (free tier, no charge for reading). The owner creates the account and
  the bucket; credentials are never given to the repository.
- **Host**: any service that runs a container and provides a grace period on
  stop; Render, Hugging Face Spaces and Google Cloud Run are candidates. The
  host is chosen when the web service exists (`003-web-ui`).
- The store stays a single SQLite file as in spec 001. If the store ever
  becomes more than one file, this feature must be revisited.
- Free tiers can change or end. The design depends on the S3 protocol only,
  so another provider can replace R2 by changing settings.

## Clarifications

Resolved on 2026-11-14:

- **Persistence method**: continuous replication of the SQLite file to
  object storage (Litestream with a free S3-compatible bucket), instead of a
  Git branch per run. Reason: shutdown on free hosts is not reliable enough
  for a save-at-exit design, and a binary database file cannot be merged.
- **Git as a store**: deferred; not part of this feature.
- **Separate feature**: persistence is specified apart from `003-web-ui`,
  because it can be built and verified with the command line alone.

## Constitution check

- I–VII: no change to claims, gate, rules or verdicts. This feature only keeps
  stored data. Constitution principles II and V are *served*: a restored
  store is identical, so every claim still traces to its stored text and a
  re-run gives the same result.
- VIII: method, data and threshold are written above before any build.
- IX: `status.html` is updated with this spec (table row, planned work, the
  claim store panel, a decision).
- No violations.
