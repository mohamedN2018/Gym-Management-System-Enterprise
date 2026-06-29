# Gym ERP — Enterprise Gym Management System

A **commercial, offline-first, native desktop ERP** for gyms. One Python codebase targeting
**Windows, Linux and macOS**. No cloud, no browser, no Internet dependency — everything runs
locally.

> **Status:** Foundation milestone complete (core kernel, persistence, security, configuration,
> logging, runnable PySide6 shell, green test suite). Business modules are built next, in the
> order defined in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech stack

| Concern | Choice |
|---|---|
| Language | Python ≥ 3.11 |
| Desktop UI | PySide6 (Qt6) — native desktop only |
| Persistence | SQLAlchemy 2.x over SQLite (PostgreSQL-ready) |
| Migrations | Alembic |
| DTO / validation | Pydantic v2 |
| Security | argon2id (passwords), Fernet (encryption) |
| Reports / Excel | ReportLab / OpenPyXL |
| QR / Barcode / Camera | qrcode / python-barcode / OpenCV |
| Packaging | Nuitka (per-OS standalone binaries) |

## Architecture

Layered / Clean Architecture with dependencies pointing inward
(`UI → Controller → Service → Repository → Database`). Business features are isolated vertical
slices that communicate only through shared services or the event bus. Full design,
database model and risk register: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Getting started (development)

```bash
# 1. Create and activate a virtual environment (Python 3.11+)
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  Linux/macOS:  source .venv/bin/activate

# 2. Install dependencies
python -m pip install -r requirements.txt -r requirements-dev.txt

# 3. Run the application
python launcher.py            # launch the desktop app (shows the login screen)
python launcher.py --check    # headless self-test (bootstrap + DB probe), no GUI
python launcher.py --version  # print version
```

### First login

On first run the database is created and seeded with a default administrator:

| Username | Password |
|---|---|
| `admin` | `admin12345` |

> Change this password after the first login. (A guided first-run/password-change flow is on
> the roadmap.)

### Language (Arabic / English)

The app ships with English (LTR) and Arabic (RTL). Switch live from the **Language** menu (or
the toggle on the login screen), or start in Arabic:

```bash
# Windows PowerShell
$env:GYM_ERP_LANGUAGE = "ar"; python launcher.py
```

Configuration is optional — the app runs with safe offline defaults. To customize, copy
`.env.example` to `.env`. The local database, backups, logs, photos and encryption key are
stored in the OS application-data directory (overridable via `GYM_ERP_DATA_DIR`).

## Quality gates

```bash
python -m pytest          # unit + integration tests
python -m ruff check .    # lint
python -m ruff format .   # format
```

## Build a standalone executable (.exe)

Packaging uses **Nuitka** (compiles to native code). From the project venv:

```bash
python scripts/build.py            # standalone app dir, windowed (no console)
python scripts/build.py --console  # keep a console window (debugging)
python scripts/build.py --onefile  # single-file executable (slower build & first start)
```

Output goes to `build/nuitka/launcher.dist/GymERP.exe` (standalone) or
`build/nuitka/GymERP.exe` (onefile). Nuitka downloads its own C toolchain on first run, so no
compiler needs to be preinstalled. For a fully portable build on other machines, install the
Microsoft Visual C++ Redistributable (2015–2022) on the target, or build with Visual Studio
present to bundle the runtime DLLs.

To just run from source without building, use `scripts/run.bat` (Windows) or
`scripts/run.ps1`.

## Database migrations

```bash
alembic revision --autogenerate -m "describe change"   # create a migration
alembic upgrade head                                    # apply migrations
```

## Project layout

```
launcher.py            Entry point (composition root → Qt event loop)
app/core/              Framework kernel: Result, errors, DI, events, base abstractions
app/database/          ORM base + global fields, engine, unit of work, repository, migrations
app/security/          Password hashing + encryption
app/settings/          Cross-platform paths + typed configuration
app/logs/              Centralized logging + audit trail
app/themes/            Dark/light theming
app/widgets/           Reusable UI components + application shell
app/modules/           Business modules (added incrementally)
tests/                 Unit + integration test suite
docs/ARCHITECTURE.md   Authoritative engineering reference
```

## License

Proprietary. All rights reserved.
