# PokerHelper

[![PokerHelper CI](https://github.com/jkoeb8762/PokerHelper/actions/workflows/domain-ci.yml/badge.svg)](https://github.com/jkoeb8762/PokerHelper/actions/workflows/domain-ci.yml)

PokerHelper is a local, offline poker study application being built from a
deterministic poker-domain foundation. The first product milestone is a
six-max, 100 BB, preflop cash-game Trainer.

The project is for post-session study only. It does not read poker clients,
observe live tables, or provide real-time assistance.

## Current milestone

Phase 3 is complete and ready for product testing. PokerHelper now adds a
range-weighted preflop Trainer to the validated Study browser: exact suited
combos, legal action inputs, immediate or delayed feedback, exact-decimal EV
loss, optional mixed-strategy RNG bands, durable local sessions, replay,
breakdowns, calibration, and targeted redrills.

The bundled pack is deliberately narrow: SB versus BB after four folds at 100
BB. It exactly reproduces a pinned open-source solver output, but its postflop
continuation model is approximate and rake-free. Trainer use therefore requires
an explicit acknowledgement, and every result is labelled as EV relative to
that exact reference model—not as accuracy-certified real-game GTO advice.

## Run the app locally

Requirements: Python 3.12+ and Node.js 24 LTS.

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

The launcher binds only to `127.0.0.1`, opens
`http://127.0.0.1:8000`, and keeps application data under `data/`. The setup,
development, and test scripts keep PokerHelper's virtual environment,
`node_modules`, caches, build output, and local data inside the repository. If
the repository is on `E:`, all project-managed files remain on `E:`; existing
Python and Node executables may be invoked from their installed locations.

For frontend development with live reload:

```powershell
.\scripts\dev.ps1
```

## Run the complete suite

From PowerShell at the repository root:

```powershell
.\scripts\test.ps1
```

The script runs 87 backend tests, 4 frontend component tests, and the production
frontend build. The original zero-dependency domain suite can still run on any
supported shell:

```text
PYTHONPATH=backend/src python -m unittest discover \
  -s backend/tests -p "test_[a-r]*.py" -v
```

Supported compatibility floor: Python 3.12. Primary release toolchains: Python
3.14 and Node.js 24. Backend dependencies are locked in `backend/uv.lock` and
frontend dependencies in `frontend/package-lock.json`.

## Documentation

- [Product roadmap](roadmap.md)
- [Canonical contracts](docs/superpowers/specs/2026-08-17-canonical-contracts-design.md)
- [Technology and deployment design](docs/superpowers/specs/2026-11-17-technology-stack-and-deployment-design.md)
- [Phase 2 artifact and Study design](docs/superpowers/specs/2026-11-18-solution-artifact-and-study-browser-design.md)
- [Phase 2 source and scope](docs/product/phase-2-source-and-scope.md)
- [Phase 3 Trainer design](docs/superpowers/specs/2026-11-19-preflop-trainer-design.md)
- [Phase 3 verification evidence](docs/evidence/phase-3-verification.md)
- [Golden-test and accuracy contract](docs/product/golden-test-corpus-and-accuracy.md)
- [MVP wireframes](docs/product/mvp-low-fidelity-wireframes.md)
- [Offline-study and privacy requirements](docs/product/offline-study-data-rights-and-privacy.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

