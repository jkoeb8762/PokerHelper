# Technology Stack and Local Deployment Design

**Status:** Approved for implementation  
**Date:** 2026-11-17  
**Roadmap checkpoint:** P0.6

## Decision summary

PokerHelper will begin as a local-only modular monolith. It will use a Python
backend, a React/TypeScript frontend, SQLite for user and index data, and
immutable solution artifacts on the local filesystem. One local process will
serve both the production frontend and a versioned JSON API on `127.0.0.1`.

The MVP has no user accounts, cloud dependency, background queue, Redis,
microservices, or on-demand solver. The architecture preserves clean seams for
PostgreSQL, object storage, authentication, and hosted deployment later.

## Selected stack

| Concern | Choice | Reason |
|---|---|---|
| Backend language | Python | Strong poker/numerical ecosystem and owner familiarity |
| HTTP API | FastAPI | Typed boundaries, generated OpenAPI, small local runtime |
| API validation | Pydantic 2 | Strict parsing and structured boundary errors |
| Domain model | Standard-library dataclasses, enums, and `Decimal` | Framework-independent, deterministic core |
| Persistence | SQLAlchemy 2 and Alembic | Database-neutral repository boundary and migrations |
| MVP database | SQLite | Zero-cost, embedded, transactional local storage |
| Solution storage | Immutable local files behind `SolutionStore` | Avoids loading large strategy trees into transactional tables |
| Frontend | React with strict TypeScript | Well-supported interactive desktop UI |
| Frontend build | Vite | Fast development server and static release build |
| Server-state client | TanStack Query | Explicit loading, error, and cache behavior |
| Navigation | React Router | Bookmarkable Study and Trainer routes |
| Styling | CSS Modules plus shared design tokens | Local ownership without a large UI framework |
| Python environment | `uv`, `pyproject.toml`, and `uv.lock` | Reproducible toolchain and dependencies |
| JavaScript environment | npm and `package-lock.json` | Reproducible frontend dependencies |
| Backend tests | `unittest` for zero-dependency domain bootstrap; pytest/Hypothesis when API work begins | Phase 1 can run on a clean Python install |
| Frontend tests | Vitest, Testing Library, and Playwright | Unit, component, and end-to-end coverage |
| CI | GitHub Actions | Deterministic cross-platform checks |

Primary release toolchains are Python 3.14 and Node.js 24 LTS. The pure domain
package keeps a Python 3.12 compatibility floor so it can run on the current
development machine; CI must exercise both the floor and primary version.

Python's `Decimal` is the canonical numeric type for BB amounts, probabilities,
weights, and EV. This follows Python's documented exact-decimal behavior and
the P0.5 contract prohibition on binary floating point as an authority.

## Repository shape

```text
PokerHelper/
├── backend/
│   ├── src/pokerhelper/
│   │   ├── api/
│   │   ├── application/
│   │   ├── domain/
│   │   └── infrastructure/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── package.json
├── data/                  # ignored; database and imported solutions
│   ├── pokerhelper.db
│   └── solutions/
├── docs/
├── scripts/
└── .github/workflows/
```

Dependencies point inward:

```text
HTTP API → application services → poker domain
                                  ↑
SQLite / filesystem adapters → persistence ports
```

The domain package must not import FastAPI, Pydantic, SQLAlchemy, a web client,
or the filesystem. This keeps poker rules usable in import validation, Study,
Trainer, tests, and future solver tools without duplicated logic.

## Backend boundaries

### API

- Routes are prefixed `/api/v1`.
- Pydantic request and response models own transport validation.
- OpenAPI is the source for generated frontend transport types.
- Stable errors use the P0.5 `{code, path, message, details}` shape.
- Exact decimals cross JSON boundaries as normalized strings, never JSON
  floating-point numbers.

Example:

```json
{
  "targetBb": "11",
  "frequency": "0.425",
  "actionEvBb": "0.184",
  "evLossBb": "0.005"
}
```

### Application services

Application services coordinate use cases such as replaying a scenario,
loading a solution node, recording a decision, and summarizing a session. They
depend on protocols for repositories, clocks, ID generation, and solution
storage rather than concrete adapters.

### Domain

The domain owns cards, hands, positions, action order, betting rules, rake,
ranges, canonical serialization, and stable identifiers. It accepts only
validated domain values and fails with explicit stable error codes.

### Infrastructure

Infrastructure implements SQLAlchemy repositories, the SQLite connection,
Alembic migrations, configuration loading, and local solution storage. No
SQLite-specific SQL may escape this layer.

## Data storage

### SQLite

SQLite stores:

- scenario catalog metadata;
- solution indexes and integrity state;
- training sessions and immutable decisions;
- derived summary caches;
- schema, identity-profile, and scoring-policy versions.

The default database path is `data/pokerhelper.db`. Foreign keys and WAL mode
are enabled on each connection. Writes use explicit transactions. Database
location comes from configuration rather than a hard-coded absolute path.

Exact decimals are stored as normalized text in SQLite and converted to
`Decimal` at the adapter boundary. MVP ordering and aggregation of these values
happens in Python. A hosted PostgreSQL adapter may use `NUMERIC`; domain and API
types remain unchanged.

### Solution artifacts

Published solutions live below `data/solutions/` and are accessed only through
`SolutionStore`. The interface supports deterministic lookup, manifest and
node loading, content-hash verification, atomic publication after validation,
and immutable reads. The Phase 2 artifact specification will choose concrete
encoding and compression; the interface does not assume one monolithic file.

**Phase 2 implementation note (2026-11-18):** the immutable artifact directory
is authoritative and a deterministic `index.json` is rebuildable from its
manifests. SQLAlchemy, Alembic, and `pokerhelper.db` are intentionally introduced
with Phase 3's first mutable session records instead of creating an otherwise
empty database during the read-only Study slice. This changes introduction
order, not the approved persistence boundary. Phase 3 must migrate scenario
catalog metadata into SQLite before adding training writes.

Validated solution-node GET responses also use direct deterministic JSON
serialization after import-time schema validation. This avoids a costly second
recursive conversion over 1,326 combos and meets the 200 ms p95 contract.
Pydantic remains required for request/write boundaries and smaller structured
responses as those boundaries arrive.

### Local data safety

`data/` is not committed. A future backup/export command must copy the SQLite
database with SQLite's backup API and include referenced manifests. The app
must never discover or read poker-client files automatically.

## Frontend architecture

- React components render data but do not implement poker rules.
- Generated API types are transport types; small mapping functions convert
  decimal strings into explicit display models.
- TypeScript treats canonical decimal strings as a branded `DecimalString`.
- TanStack Query owns API request state; component-local state owns transient
  UI selections.
- No global state framework, server-side rendering, or large component kit is
  required for the MVP.
- CSS tokens define spacing, typography, focus, semantic colors, and the range
  matrix palette. Meaning must never depend on color alone.

## Development and local release

### Development

- FastAPI listens on `127.0.0.1:8000`.
- Vite listens on `127.0.0.1:5173` and proxies `/api` to FastAPI.
- Backend and frontend support hot reload.
- A root launcher prepares the environment, applies migrations, starts both
  development processes, and opens the browser.

### Release mode

Vite produces static assets. FastAPI serves those assets and `/api/v1` from a
single process and one localhost port. The server binds only `127.0.0.1`; it is
not exposed to the LAN. With no network identity boundary, MVP release mode has
no login, cookies, HTTPS termination, or cross-origin configuration.

The launcher must:

1. verify compatible Python and Node runtimes;
2. prepare locked dependencies;
3. apply pending migrations;
4. start the local server on an available configured port;
5. open the user's default browser; and
6. provide a clear stop command and log location.

## Testing and quality gates

The deterministic domain suite is the first gate and has no network or database
dependency. Later layers add repository integration, API contract, component,
and browser tests. CI runs on Windows and Linux against supported Python
versions and blocks merges on any deterministic failure.

Required tools by the end of the MVP are:

- Ruff for Python formatting and linting;
- a strict Python type checker;
- `unittest`/pytest and Hypothesis for examples and properties;
- TypeScript strict mode and ESLint;
- Vitest and Testing Library for UI logic;
- Playwright for the approved journey;
- generated-OpenAPI drift detection.

P0.8 defines numeric tolerances and the golden corpus. A test may not loosen a
tolerance merely to accommodate an implementation result.

## Failure handling and observability

- Domain failures have stable codes and precise paths.
- Boundary validation fails closed; unsupported data is not coerced.
- Application logs are local, structured, and exclude hole-card history unless
  needed for an explicit diagnostic export.
- An unexpected exception receives a correlation ID; the UI shows a safe
  message while the local log retains the traceback.
- Health and version endpoints expose application, schema, and build versions,
  but no personal study data.

## Hosted evolution path

Hosting is deliberately deferred. The migration trigger is a decision to use
PokerHelper from multiple devices or share it with other people. At that point:

1. build the already single-process release in a container;
2. switch the configured SQLAlchemy URL from SQLite to PostgreSQL;
3. implement an object-storage `SolutionStore`;
4. add authentication, authorization, CSRF/cookie policy, HTTPS, secrets, and
   per-user data ownership;
5. run migration, backup/restore, privacy, and load tests.

For the current scope, a private single-user hosted transition is expected to be
measured in roughly one to two focused engineering weeks once a provider is
chosen. That estimate is not a commitment and excludes public multi-user product
work such as abuse protection, support, billing, and operational monitoring.

## Alternatives considered

### Django plus React

Django would provide an admin and mature authentication early, but those are
not MVP needs. Its additional conventions would not reduce Phase 1 domain work.

### Full-stack TypeScript

A single language would simplify some transport typing, but Python better fits
the expected poker-analysis and solver ecosystem and the owner's familiarity.

### Hosted-first deployment

Hosted-first would add auth, managed data, secrets, HTTPS, and recurring cost
before the preflop strategies are useful. The selected boundaries preserve that
route without paying its complexity now.

## Sources

- [FastAPI features](https://fastapi.tiangolo.com/features/)
- [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Vite guide](https://vite.dev/guide/)
- [React with TypeScript](https://react.dev/learn/typescript)
- [SQLAlchemy dialects](https://docs.sqlalchemy.org/en/20/dialects/)
- [uv projects](https://docs.astral.sh/uv/concepts/projects/)
- [Python `Decimal`](https://docs.python.org/3.14/library/decimal.html)
- [GitHub Actions: building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)

## Approval record

The project owner approved the local-first deployment, Python/FastAPI and
React/Vite architecture, SQLite plus local solution files, two-toolchain setup,
and migration-friendly boundaries during the P0.6 design discussion. On
2026-11-17 the owner authorized completion through P1.10, making the remaining
P0.6 implementation-detail decisions above delegated project decisions.
