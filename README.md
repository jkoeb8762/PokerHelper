# PokerHelper

[![Domain CI](https://github.com/jkoeb8762/PokerHelper/actions/workflows/domain-ci.yml/badge.svg)](https://github.com/jkoeb8762/PokerHelper/actions/workflows/domain-ci.yml)

PokerHelper is a local, offline poker study application being built from a
deterministic poker-domain foundation. The first product milestone is a
six-max, 100 BB, preflop cash-game Trainer.

The project is for post-session study only. It does not read poker clients,
observe live tables, or provide real-time assistance.

## Current milestone

Phase 1 is complete. It implements cards, exact hand evaluation, six-max preflop betting,
versioned rake, exact-combo ranges, canonical serialization, and stable content
identities. It has no network, database, or third-party runtime dependency. The
project is paused for product testing and code review before Phase 2 begins.

## Run the deterministic suite

From PowerShell at the repository root:

```powershell
.\scripts\test.ps1
```

Or on any supported shell:

```text
PYTHONPATH=backend/src python -m unittest discover -s backend/tests -p "test_*.py" -v
```

Supported compatibility floor: Python 3.12. Primary release toolchain: Python
3.14. CI runs the same suite on Windows and Linux for both versions.

## Documentation

- [Product roadmap](roadmap.md)
- [Canonical contracts](docs/superpowers/specs/2026-08-17-canonical-contracts-design.md)
- [Technology and deployment design](docs/superpowers/specs/2026-11-17-technology-stack-and-deployment-design.md)
- [Golden-test and accuracy contract](docs/product/golden-test-corpus-and-accuracy.md)
- [MVP wireframes](docs/product/mvp-low-fidelity-wireframes.md)
- [Offline-study and privacy requirements](docs/product/offline-study-data-rights-and-privacy.md)

