# Offline Study, Data Rights, and Privacy Requirements

**Status:** Approved product requirement  
**Date:** 2026-11-17  
**Roadmap checkpoint:** P0.10

## Product boundary

PokerHelper is an after-the-fact study application. It must not observe,
interpret, or advise on a hand while that hand is being played. This boundary is
a product requirement even where local law or a poker operator would permit
more.

## Prohibited real-time-assistance behavior

PokerHelper must not:

- read a poker client's process memory, window contents, accessibility tree,
  network traffic, log stream, or live hand-history file;
- capture or interpret the screen, table, cards, action, timer, or opponent
  information from an active game;
- overlay advice on a poker client;
- select, click, size, queue, or automate a poker action;
- expose a low-latency endpoint intended for live decisions;
- watch a directory and analyze hands before a session is explicitly imported
  after play;
- market itself as undetectable, compliant real-time assistance, or a way to
  evade operator rules.

The optional mixed-strategy RNG is a manual study aid inside an offline drill.
It never reads live context and never submits an action.

## Defensive product controls

- The application binds only to `127.0.0.1` for the local MVP.
- It has no poker-client integration, overlay mode, global hotkeys, screen
  capture, or continuous file watcher.
- Scenario selection is manual and uses published, precomputed solution data.
- Any future hand-history import requires an explicit user-selected file or
  paste action and is labelled post-session study.
- Product copy and help text repeat the study-only boundary where solution
  access or import could be misunderstood.
- A proposed feature that weakens this boundary requires a roadmap change and
  explicit owner review; ordinary implementation authority is insufficient.

## Solution and content rights

Every solution artifact must carry:

- source owner/creator;
- acquisition or generation method;
- authorization basis (`SELF_GENERATED`, `LICENSED`, `PUBLIC_DOMAIN`, or another
  reviewed value);
- license or usage terms reference;
- redistribution permission;
- solver/generator and version where known;
- creation/import timestamp and content hashes;
- transformations, EV normalization, and limitations.

An artifact is rejected from publication when its provenance is absent,
ambiguous, incompatible with intended use, or forbids required local storage.
PokerHelper must not scrape, reverse engineer, repackage, or redistribute a
commercial strategy library without explicit permission.

Example and test strategy values must be synthetic or separately authorized and
clearly marked so they cannot be mistaken for production recommendations.

## User data and privacy

### MVP collection

The local MVP stores only data needed for study:

- application and schema version;
- imported solution metadata and integrity state;
- selected scenarios;
- training sessions and immutable decisions;
- preferences and derived summaries;
- local operational logs.

It does not require a name, email, account, advertising identifier, contacts,
location, payment data, or cloud telemetry. It makes no analytics request by
default.

### Location and access

User data remains under the configured local `data/` directory. The application
must document that path, provide an open-folder action later, and never copy
study history outside it without an explicit export or future opt-in service.

Logs minimize sensitive detail. Routine logs do not include full session
decision history or imported raw hands. A user-initiated diagnostic export must
preview included files and allow study data to be excluded.

### Public source repository boundary

The PokerHelper source repository is public so its deterministic test matrix can
run on public-repository GitHub Actions. Public source control contains code,
documentation, tests, deliberately non-sensitive fixtures, and only those seed
solution artifacts that have received an explicit provenance and redistribution
review. Each bundled seed must be content-addressed, immutable, reproducible,
non-user data, and covered by compatible terms recorded in its manifest and the
third-party notice. Local study history, user-imported solutions, imported hand
histories, logs, database files, credentials, tokens, environment files, and
diagnostic exports must not be committed. The project-level ignore rules exclude
the standard local data, log, environment, cache, and credential paths;
contributors must still inspect every change before publishing it.

### Retention and control

- Sessions persist until the user deletes them.
- Deleting a session removes its decisions and derived caches transactionally.
- Deleting an imported source removes raw source data and derived user-owned
  records where safe, while immutable shared solution artifacts follow their
  own dependency warning flow.
- Export uses documented, versioned formats and includes solution/version
  references needed to interpret results.
- A factory reset shows the exact local targets, requires confirmation, and is
  implemented as a recoverable operation where the platform permits.
- Backups are user-controlled; the application does not promise deletion from
  copies the user made independently.

## Security requirements

- Treat imported artifacts and hand histories as untrusted input.
- Enforce file-size, decompression, path, schema, and reference limits before
  publication.
- Never honor archive paths that escape the import staging directory.
- Store no executable code in a solution artifact and never evaluate imported
  expressions.
- Do not send crashes or logs externally without a separate informed opt-in.
- Dependencies and release artifacts must be locked and integrity checked.
- Unexpected failures must not expose absolute paths or study history through
  the UI.

## Future hosted mode

Hosting requires a new privacy and security review before deployment. At
minimum it adds authenticated data ownership, authorization tests, encryption
in transit, secrets management, retention/deletion jobs, account export,
breach-response planning, audit logs, and a published privacy notice. Local MVP
approval does not authorize collecting or transferring user data to a server.

## Review checklist

Every user-facing phase asks:

1. Can this feature react to a live hand or poker client? If yes, reject it.
2. Is every strategy input authorized and traceable? If no, block publication.
3. Is new personal data truly required? If yes, document purpose and control.
4. Can the user inspect, export, and delete the resulting data?
5. Does failure preserve the study-only boundary and avoid silent transfer?

## Approval record

The project owner approved the offline-study guardrail as a founding product
principle and delegated completion through P1.10 on 2026-11-17. This document
records the enforceable MVP requirements; it does not provide legal advice.

**Phase 3 implementation note (2026-11-19):** local sessions and immutable
decisions are stored in the configured repository-local SQLite database.
Session deletion cascades to its decisions transactionally, retained redrills
detach deleted provenance links safely, and active delayed-feedback results are
redacted from detail and aggregate APIs until the session ends. No telemetry or
external history transfer was added.
