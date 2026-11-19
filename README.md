# PokerHelper

[![PokerHelper CI](https://github.com/jkoeb8762/PokerHelper/actions/workflows/domain-ci.yml/badge.svg)](https://github.com/jkoeb8762/PokerHelper/actions/workflows/domain-ci.yml)

PokerHelper is a local, offline poker study application being built from a
deterministic poker-domain foundation. The first product milestone is a
six-max, 100 BB, preflop cash-game Trainer.

The project is for post-session study only. It does not read poker clients,
observe live tables, or provide real-time assistance.

## Current milestone

Phase 2 has been reopened because product testing exposed a strategy-coverage
gap. PokerHelper's Study and Trainer mechanics are implemented: exact suit-specific
combos, legal action inputs, immediate or delayed feedback, exact-decimal EV
loss, optional mixed-strategy RNG bands, durable local sessions, replay,
breakdowns, calibration, and targeted redrills. The originally approved
multi-position six-max solution library is not yet complete, so this is not yet
the finished preflop MVP.

The currently bundled pack is a development reference fixture: SB versus BB
after four folds at 100 BB. It exactly reproduces a pinned open-source solver
output, but its postflop continuation model is approximate and rake-free.
Trainer use therefore requires an explicit acknowledgement, and every result is
labelled as EV relative to that exact reference model—not as
accuracy-certified real-game GTO advice. Reopened Phase 2 will use a
project-owned pipeline built from compatible open-source components; its exact
pinned components, continuation-value model, and qualifying solution pack are
still pending.

## Run PokerHelper on Windows

These instructions are intended for someone who only wants to use the app. You
do not need Git, a GitHub account, or any programming experience.

PokerHelper runs only on your computer. The first setup needs an internet
connection to download its software packages; after that, normal study sessions
work offline. Allow roughly 500 MB of free space on the drive where you put the
PokerHelper folder.

### 1. Install the two prerequisites

Install both of these before downloading PokerHelper:

1. [Python for Windows](https://www.python.org/downloads/windows/) — use Python
   3.12 or newer. During installation, enable **Add python.exe to PATH**.
2. [Node.js](https://nodejs.org/en/download) — install the current **LTS**
   Windows version using its normal/default options. It must be version 24 or
   newer; version 24 is the project's tested baseline.

If either installer asks you to restart Windows, do that before continuing.

### 2. Download and extract PokerHelper

1. [Download PokerHelper as a ZIP](https://github.com/jkoeb8762/PokerHelper/archive/refs/heads/master.zip).
2. In File Explorer, right-click the downloaded ZIP and choose **Extract All**.
3. Move the extracted `PokerHelper-master` folder to its permanent location.
   Choose a drive with enough free space before running setup. It is fine to
   rename the folder to `PokerHelper`.

Do not run PokerHelper from inside the ZIP file, and avoid moving the folder
after setup.

### 3. Run the one-time setup

1. Open the extracted PokerHelper folder in File Explorer.
2. Click the File Explorer address bar, type `powershell`, and press Enter. A
   blue or black terminal window should open in the correct folder.
3. Copy the command below, paste it into that window, and press Enter:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup.ps1"
```

Setup downloads the required packages and builds the app. This can take several
minutes. Leave the terminal open until it says:

```text
PokerHelper is ready. Run .\scripts\start.ps1
```

It is safe to run the setup command again if setup was interrupted.

### 4. Start PokerHelper

In the same terminal, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start.ps1"
```

Your default browser should open PokerHelper automatically. If it does not,
open [http://127.0.0.1:8000](http://127.0.0.1:8000) yourself. Keep the terminal
window open while studying.

To stop PokerHelper, return to the terminal and press **Ctrl+C**. Closing only
the browser tab does not stop the local app.

### Starting it on future days

You only need to repeat steps 1 and 2 below:

1. Open the PokerHelper folder, click the File Explorer address bar, type
   `powershell`, and press Enter.
2. Run the start command from step 4. You do not need to run setup again unless
   you download a newer version or setup previously failed.

### Your study data

Training history is stored locally in `data\pokerhelper.db` inside the
PokerHelper folder. Nothing is uploaded by the app. To make a backup, stop
PokerHelper and copy the entire `data` folder somewhere safe. Do not delete that
folder when replacing or updating PokerHelper if you want to keep your history.

The launcher listens only on `127.0.0.1`, so other computers cannot connect to
your copy. The virtual environment, downloaded packages, caches, build output,
and study data also remain inside the PokerHelper folder. For example, placing
the folder on `E:` keeps all PokerHelper-managed files on `E:`; Python and Node
themselves remain wherever their installers placed them.

### Common problems

- **`python` is not recognized:** reinstall Python and make sure **Add
  python.exe to PATH** is enabled, then close and reopen the terminal.
- **`node` is not recognized, or the Node version is too old:** install the
  current Node.js LTS version, then close and reopen the terminal. Run
  `node --version` and confirm the first number is 24 or higher.
- **PokerHelper says it is not prepared:** run the one-time setup command and
  wait for the green success message before using the start command.
- **The browser does not open:** leave the terminal running and manually visit
  [http://127.0.0.1:8000](http://127.0.0.1:8000).
- **Port 8000 is already in use:** stop the other PokerHelper terminal with
  **Ctrl+C**. If you cannot find it, restart Windows and try the start command
  again.
- **Setup stops with a download error:** check the internet connection and run
  the same setup command again.

If the problem persists, copy the complete red error message—or take a
screenshot of the terminal—so the person helping you can see what failed.

## Developer commands

Requirements: Python 3.12+ and Node.js 24 LTS. From PowerShell at the repository
root:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

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
- [Phase 2 coverage recovery and solver audit](docs/product/phase-2-coverage-recovery.md)
- [Phase 2 MVP preflop coverage matrix](docs/product/phase-2-mvp-preflop-coverage-matrix.md)
- [Phase 3 Trainer design](docs/superpowers/specs/2026-11-19-preflop-trainer-design.md)
- [Phase 3 verification evidence](docs/evidence/phase-3-verification.md)
- [Golden-test and accuracy contract](docs/product/golden-test-corpus-and-accuracy.md)
- [MVP wireframes](docs/product/mvp-low-fidelity-wireframes.md)
- [Offline-study and privacy requirements](docs/product/offline-study-data-rights-and-privacy.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

