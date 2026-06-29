# Gym ERP — System Architecture

> Status: **living document**. This is the authoritative engineering reference derived from
> Master System Prompt Parts 1–3.1. Every module added to the system must conform to it.

---

## 1. Vision & Constraints

A **commercial, offline-first, native desktop ERP** for gyms, sellable to thousands of
customers worldwide. No cloud, no browser, no web UI, no Internet dependency. One Python
codebase targeting **Windows, Linux, macOS**.

| Concern | Decision |
|---|---|
| Language | Python ≥ 3.11 |
| UI | PySide6 (Qt6) — native desktop only |
| Persistence | SQLAlchemy 2.x ORM over SQLite (PostgreSQL-ready) |
| Migrations | Alembic |
| DTO / validation | Pydantic v2 |
| Security | argon2id (passwords), Fernet (field/settings encryption) |
| Reports | ReportLab (PDF), OpenPyXL (Excel), CSV (stdlib) |
| Codes | qrcode, python-barcode (generation), OpenCV (camera scan) |
| Packaging | Nuitka (per-OS standalone binaries) |

Quality bar: SOLID · DRY · KISS · YAGNI · Clean/Layered Architecture · Repository + Service
patterns · Dependency Injection · strict UI/business separation · no placeholders, no TODOs,
no dead code, no hardcoded values.

---

## 2. Layered (Clean) Architecture

Dependencies point **inward only**. Outer layers depend on inner abstractions, never the reverse.

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation  (PySide6 Views, Dialogs, Widgets, Controllers) │  app/widgets, modules/*/ui, modules/*/controllers
├─────────────────────────────────────────────────────────────┤
│ Application   (Services, DTOs, Validators, Events, Use-cases) │  modules/*/services, modules/*/dtos, app/services
├─────────────────────────────────────────────────────────────┤
│ Domain        (Entities, domain rules, repository interfaces) │  modules/*/models, app/core/base
├─────────────────────────────────────────────────────────────┤
│ Infrastructure(ORM, repositories impl, engine, files, crypto) │  app/database, app/security, app/infrastructure
└─────────────────────────────────────────────────────────────┘
```

**Allowed call path:** `UI → Controller → Service → Repository → Database`.
**Forbidden:** `UI → Database`, `UI → SQL`, `UI → ORM`, `Widget → Repository`, business logic in UI.

### Layer responsibilities
- **Controllers** translate UI intent into service calls and map `Result`/DTOs back to the view. No business rules.
- **Services** own *all* business rules, permission checks, transactions, calculations, workflow, and event publication.
- **Repositories** do persistence only: CRUD, filter, paginate, search, sort. No business logic.
- **Validators** guard every input before it reaches a service's core logic.
- **DTOs** cross every layer boundary. ORM entities never escape the service layer.

---

## 3. Project Structure

```
Gym-Management-System-Enterprise/
├── launcher.py                  # Entry point (composition root → QApplication)
├── pyproject.toml / requirements*.txt / alembic.ini
├── app/
│   ├── core/                    # Framework kernel (innermost, dependency-free)
│   │   ├── result.py            # Result[T] / Error value objects
│   │   ├── errors.py            # AppError hierarchy + ErrorCode
│   │   ├── constants.py         # App identity & defaults (no magic numbers elsewhere)
│   │   ├── pagination.py        # PageRequest / Page[T] / Sort
│   │   ├── di.py                # Dependency-injection container
│   │   ├── events.py            # In-process EventBus + Event base
│   │   └── base/                # Abstractions: DTO, IRepository, IUnitOfWork, Service, Validator
│   ├── database/                # Persistence infrastructure
│   │   ├── base.py              # DeclarativeBase + global-field mixins (Part 3.1)
│   │   ├── engine.py            # Engine/session factory (SQLite pragmas, PG-ready)
│   │   ├── unit_of_work.py      # SqlAlchemyUnitOfWork
│   │   ├── repository.py        # SqlAlchemyRepository[T] base
│   │   └── migrations/          # Alembic environment + versions
│   ├── security/                # password_hasher.py, encryption.py
│   ├── settings/                # paths.py (cross-platform dirs), config.py (AppConfig)
│   ├── logs/                    # logging_service.py (centralized, rotating, audit-ready)
│   ├── localization/            # i18n / RTL-LTR (translations, locale service)
│   ├── services/                # Global app services (Backup, Report, Qr, Printer, …)
│   ├── infrastructure/          # OS adapters, file storage, bootstrap helpers
│   ├── widgets/                 # Reusable UI components (buttons, tables, dialogs, shell)
│   ├── themes/                  # Dark/Light QSS theme assets + manager
│   ├── reports/ printing/ backups/ updates/ resources/   # Cross-cutting feature support
│   ├── plugins/                 # Plugin loader/registry/API/lifecycle
│   └── modules/                 # Business modules (vertical slices, see §4)
├── assets/  docs/  tests/  scripts/  installer/
```

### Module (vertical slice) layout — **mandatory for every business feature**
```
app/modules/<feature>/
├── models/         repositories/   services/      controllers/
├── validators/     dtos/           events/        permissions/
├── ui/{forms,tables,dialogs,reports}/
├── tests/          resources/      translations/   documentation/
```
Modules are isolated. They communicate **only** via shared services or the `EventBus` — never by
importing another module's internals.

---

## 4. Module Catalog (build order)

| # | Module | Depends on | Notes |
|---|--------|-----------|-------|
| 0 | **core / database / security / settings / logs** | — | Foundation kernel (this milestone) |
| 1 | **security/users** (Users, Roles, Permissions, RBAC, Auth, Audit) | 0 | Gatekeeper for everything |
| 2 | **branches / company / settings** | 1 | Multi-branch, lookup tables |
| 3 | **members** | 1,2 | Profiles, photos, medical, measurements, goals, tags |
| 4 | **membership** | 3 | Plans, packages, contracts, freeze/extend/transfer/renew |
| 5 | **attendance / access-control / QR** | 3,4 | Sub-second check-in, turnstile/gate ready |
| 6 | **trainers** | 3 | Schedules, clients, sessions, commissions |
| 7 | **workouts / nutrition** | 3,6 | Exercise library, programs, plans |
| 8 | **inventory** | 2 | Products, suppliers, stock movement, barcodes |
| 9 | **POS / payments / invoices** | 3,4,8 | Cash register, refunds, daily closing |
| 10 | **accounting** | 9 | Income/expenses, taxes, periods |
| 11 | **reports / analytics** | all | KPIs, charts, PDF/Excel/CSV |
| 12 | **notifications** | all | Expiry, birthday, low-stock, summaries |
| 13 | **dashboard** | all | Shell home; hosts module views |

---

## 5. Database Architecture (from Part 3.1)

- **3NF**, FK referential integrity on everywhere, indexed hot columns, unique constraints on
  business identifiers (membership_number, qr_code, barcode, username, email, national_id, invoice/receipt numbers).
- **Global fields on every business table** (via mixins): `id, uuid, created_at, updated_at,
  created_by, updated_by, deleted_at, deleted_by, is_deleted, is_active, version, remarks`.
- **Soft delete** only — physical deletes are forbidden; all reads default to `is_deleted = false`.
- **Audit** — every create/update/delete/restore/login/payment captured (audit + history tables).
- **Optimistic concurrency** via `version` column (SQLAlchemy `version_id_col`).
- **Lookup tables**, not hardcoded enums, for user-extensible domains (statuses, categories…).
- **Engine-neutral SQL**: portable types, no SQLite/PG-specific DDL except guarded pragmas.

---

## 6. Cross-cutting Concerns

- **Error handling:** services return `Result[T]`; infrastructure raises typed `AppError`s; UI
  never sees raw exceptions. The app must never crash on operational errors.
- **Logging:** single `LoggingService` (rotating file + console). Audit log carries timestamp,
  user, module, action, old/new value, device, result, execution time. Logs never auto-deleted.
- **Threading:** long operations (backup, restore, import/export, big reports, camera, scanning,
  printing, DB maintenance) run on Qt worker threads; the UI thread never blocks.
- **Configuration:** `AppConfig` (pydantic-settings) + lookup/settings tables. No hardcoded values.
- **Security:** argon2id password hashing; Fernet encryption for sensitive settings/fields; key
  stored in the OS app-data dir with restrictive permissions; parameterized ORM queries only.
- **i18n:** Qt translation + locale service; full Arabic RTL / English LTR with mirrored layouts.
- **Plugins:** loader + registry + versioned lifecycle; modules are replaceable without edits.

---

## 7. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| SQLite concurrency limits | Med | WAL mode, short write transactions, single-writer UoW; PG upgrade path ready |
| UI freeze on heavy ops | High | Mandatory worker-thread offloading; no blocking calls on GUI thread |
| Schema drift over years | High | Alembic from day one; additive, backward-compatible migrations |
| Cross-platform path/encoding bugs | Med | Central `paths.py`, `pathlib`, UTF-8 everywhere, CI on all 3 OSes |
| Lost/corrupted local DB | High | Auto-backup + integrity checks + restore; WAL checkpointing |
| Encryption key loss | High | Key in app-data dir, included in secure backups, documented recovery |
| Scope (huge surface area) | High | Strict module isolation + build order; foundation proven before features |
| Sub-second QR check-in SLA | Med | Indexed lookups, cached active subscription view, profiled hot path |

---

## 8. Build Strategy

1. **Foundation first (current milestone):** core kernel, DB infra, security, settings, logging,
   runnable PySide6 shell, green unit tests. Proves every pattern end-to-end.
2. **Module by module** in the order of §4, each a full vertical slice with tests & docs.
3. **Never break existing functionality**; additive migrations; refactor only with tests as a net.
