# Accounting implementation journal using the Odoo 19 ontology

Language policy: repository documentation and this local journal are maintained in English. The external implementation gist remains in Russian, including future entries, as explicitly requested by the user on 2026-09-08. Translate new entries separately; do not overwrite the Russian gist with this English file.

Started: 2026-09-05. This journal records decisions, actual changes, checks, and open questions. A plan is not considered an implemented feature.

Original analysis: https://gist.github.com/litnimax/7985e3bb4f7a0a829df17e424fdee800

## 001 — Scope

**Decision.** Odoo 19 supplies the business ontology and scenario catalog. Accounting rules remain in `/workspace/arpee-angee/addons/arp/accounting`. Shared Angee improvements land in `/home/paseo/.paseo/worktrees/1s29tjir/exotic-pony`, a worktree of `/workspace/angee-django`, on `astra/invoice-form-contract`. Moving accounting into angee-django is unnecessary. The original analysis's suggestion to discuss such a move was withdrawn after the user's clarification.

**Initial snapshots:** arpee `fa5c444125595e82260d45e2e53d4c7994ed3ce5`; Angee `64f1d1750f7a9f5afbefc3ce3196fa190ee44280`; Odoo `1a13ceeaee12fe5cc50f287c31f217d4be2a2eaf`.

## 002 — First package

**Plan.** First establish a reproducible build and existing accounting-test baseline, then fix payment registration: residual instead of total, independent money direction and partner type, payment-group and bank-account validation. Reconciliation graphs, posting guards, and later stages remain queued under the original plan.

**Owners.** PaymentManager owns registration and group locks; Invoice/JournalItem own debt/residual; Payment owns partner type, direction, and its entry; GraphQL owns authorization and calling the domain operation; React declares the form. Django/PostgreSQL own transactions/constraints; Angee provides existing money/sequence/transitions. No new dependency is proposed.

**Analogs.** Existing InvoiceManager.create_document, sales/purchase factories, JournalItemManager.reconcile locks, shared GraphQL write backend, and PaymentsPage. Do not calculate residuals on the frontend or introduce parallel numbering.

**Acceptance.** Invoice 100 → payment 40 → default payment 60; both partner-type refunds; rejection of empty/incompatible groups; a missing bank account does not fall back to receivable; repeated/concurrent requests do not create unintended overpayment. Verify entries and residuals, not just status.

## 003 — Environment inspection

**Completed.** Read arpee README, manage.py, settings.yaml, source models/tests, backend guidelines, and Angee's local angee-workspace skill. Arpee is clean; the Angee worktree contains the previously created report.

**Finding.** No angee.yaml exists in arpee/ancestor directories or the target worktree's ancestor chain. angee/uv are absent from PATH; both Angee checkouts lack .venv/bin/python. README's dev stack is not prepared here. Build/tests have not run.

**Open question.** Asked the user for the running stack location or instructions to prepare a new test stack. `.agents/skills/angee-workspace/SKILL.md`, Resolve The Controlling Stack Root, requires clarification about initialization when no ancestor stack exists. No stack was initialized; independent changes and test scenarios are being prepared while awaiting a reply.

**Implementation state.** No business code changed yet. The journal was created in the target worktree and is published separately as a link-accessible gist. Further decisions, changes, and checks will be appended.

## 004 — First-package regression scenarios

**Changed.** Added four `PaymentRegistrationTests` methods in `/workspace/arpee-angee/addons/arp/accounting/tests.py`:

- After paying 40 of 100, a second payment with no explicit amount is 60; neither payment leaves an unmatched residual.
- All four invoice/refund kinds separately verify money direction, bank-item sign, receivable/payable account, and settlement.
- An empty group raises ValidationError without creating Payment.
- A missing bank account blocks posting, retaining draft, an empty number, and no entry.

**Checks.** Python 3 `ast.parse` parsed the changed file and found four new methods; `git diff --check` passed. Django tests have not run: anticipated failures on the old implementation are not presented as an executed red run. Tests use existing fixtures/business calls without mocking Django/ORM. Models, schema, and UI remain unchanged.

**Publication.** Created and verified secret, link-accessible gist https://gist.github.com/litnimax/44d67e5f0e656dbce5366693082b88dc . Updates use this same gist; the original analysis remains separate.

**Next.** Resolve stack location/setup, run baseline/regressions, implement the first package. The stack question remains open; silence does not authorize initialization.

## 005 — Own stack selected and prepared

The user authorized `/home/paseo/.paseo/worktrees/2f3fqf9s/modest-toad`, branch `modest-toad`, an arpee-angee worktree. Angee stays in `exotic-pony` on `astra/invoice-form-contract`. The user's colorful-bumblebee was not found in the accessible filesystem; its processes/files were untouched.

Moved regressions from `/workspace/arpee-angee` into modest-toad; verified and removed only that patch from the former checkout. Created project pyproject/uv.lock, `.angee/framework` symlink, framework addon/package roots, and process-only `angee.yaml`. Installed Python 3.14.7, uv 0.12.10, Angee CLI 0.12.1, process-compose 1.122.0, pnpm 11.1.3; Debian libmagic is local in `.angee/tools/sysroot`. The dedicated SQLite database is `.angee/data/db.sqlite3`. Verified free backend 8601, web 5174, process-compose 8091 ports. Startup uses `angee dev`; service scripts are in `.angee/`.

`angee build` passed. Initial test attempts found an incorrect import label (`accounting.tests` instead of `arp.accounting.tests`) and missing initial migrations; native provision created migrations. pnpm was installed through Corepack; attempts through the Python package manager/an assumed GitHub asset are not part of the final environment.

## 006 — Original defects confirmed; first payment package implemented

Baseline: 21 accounting tests, four failures and one error in new regressions, one PostgreSQL-only skip. Confirmed 100 instead of residual 60, both refund directions, IndexError on an empty group, and no rejection of an empty bank account. Existing scenarios passed.

Changes in `arp.accounting`:

- Invoice determines partner type and settlement direction; Payment stores independent customer/vendor `partner_type`, selecting receivable/payable separately from money direction.
- PaymentManager.register locks debt items by PK, then reloads/locks documents. Item→invoice order matches reconciliation status updates. Amount derives from current residuals, without recalculating amount_total.
- Validates nonempty, duplicate-free groups; persisted/posted documents with partners; one company/currency/partner/document kind; correct debt items; nonzero residual per invoice; positive finite amount at currency precision; and bank/cash journal configuration.
- Invoice registration is capped by debt through validation, not silent clipping. Standalone Payment remains available for advances. Mixed invoice/refund groups are explicitly rejected rather than automatically netted.
- Removed receivable fallback for missing bank accounts and old `_reconcile_invoices`, which repeated direction-based account inference. Validation belongs to Payment; the resolver stays thin.
- Added partner_type to GraphQL and the shared Payment form. Prepared addon-owned Payment/HistoricalPayment migrations: historical outbound maps to vendor. Historical amounts/entries remain unchanged; migrations do not automatically repair old incorrect refunds.

Intermediate migration checks: **83 accounting/sales/purchase tests passed, 6 PostgreSQL-only skipped**. Additional negative/concurrent scenarios are in progress. Reconciliation graphs and comprehensive posted-record protection remain next.

## 007 — Fixes needed for a cold demo start

Initial provision exposed None.currency when sales lines loaded before company post-load hooks. Owner fix: `CompanyAccounting.round_amount` accepts explicit document currency; sales/purchase pass order currency while retaining company rounding mode. This also fixes documents whose currency has different precision; missing GL currency now raises a domain error.

Next, CRM Team validated direct membership before grants materialized. Fixed lost dependencies when separating rows/grants in `angee.resources` in exotic-pony. The existing EntryGraph governs order: independent grants still follow rows, explicit row→grant dependencies take precedence. Operations are atomic and post-load hooks see grants. CRM's manifest declares Team's dependency on arp.base membership grants. Membership validation/resources were not disabled.

Added framework regressions: grants are available during dependent-row clean and post-load hooks; failed import/dry run roll back grants/rows; repeated load is idempotent. The initial test incorrectly used an anonymous wildcard instead of auth/user wildcard; the test subject declaration was corrected. Resource tests also exposed an old deletion-test failure: a knowledge signal expects RecordBinding in a bare test app. Its origin/baseline is still under review.

After ordering fixes, **full provision --demo passed: 437 created, 2 updated; schema: ok**. Frontend codegen passed: 22 addons, 2 schemas. Service startup/final checks are underway.

## 008 — Payment, concurrency, and migration checks

Added negative scenarios for zero/negative/nonfinite amounts, overpayment, excess currency precision; mixed companies/partners/document kinds; draft, duplicate, and paid documents; sales journals instead of bank journals and foreign-company journals. Added document-currency rounding when company currency is unset.

Started dedicated PostgreSQL 17.5 at `127.0.0.1:55441` in `.angee/pg-test`. With no Docker socket, used Maven Central's PostgreSQL binary package (`io.zonky.test`, embedded-postgres-binaries-linux-amd64 17.5.0). This is temporary testing infrastructure; the main stack stays SQLite. Two threads simultaneously registering full payment yield exactly one payment, a ValidationError on the second request, and zero residual. Together with existing concurrent numbering and sales/purchase: **89 tests, all passed, no skips**.

Then added a migration integration test running actual AddField/RunPython on isolated legacy Payment/HistoricalPayment tables: inbound becomes customer, outbound vendor, amounts 40.25/60.75 survive, and repeat applicability is disabled. The factory restores the original actor after elevated bookkeeping per Angee's contract. Final PostgreSQL accounting rerun: **28 tests, all passed**. Logs contain dev-only change-publisher errors with DEBUG=False; dispatch.send_robust does not abort tests. Production event delivery was not verified.

Accounting frontend: **2 files, 5 tests, all passed**. Ruff E/F/I under Angee configuration passes for changed business Python and the resource owner; `git diff --check` and shell syntax pass.

## 009 — Full Angee suite and environment diagnosis

Full `pytest -q`: **1816 passed, 8 failed, 5 skipped**, 959.95 seconds. All eight failures were in `tests/test_settings.py`: inherited `ANGEE_PROJECT_DIR` pointed to ARPEE and interfered with temporary test settings.yaml. This was an error in the session's initial test invocation. Removing project-specific environment variables allowed the whole module to pass: **62 passed**. The full suite was not rerun; a full run plus targeted rerun is not claimed as one completely green run.

The isolated resource suite earlier found LookupError `knowledge.RecordBinding` in `pre_delete`. On a clean detached checkout at original Angee `64f1d175`, `test_stale_ledger_pointer_to_wrong_live_row_is_repaired` reproduces the same failure: 1 failed. It passes in the full suite, indicating a preexisting registry state/order dependency. No production signal was changed and no test disabled. The new row→grant regression passes, including rollback, dry run, hook, and repeated import.

## 010 — Live UI and reproducible startup

`angee status --json` confirms django/web running. Stack: ARPEE modest-toad, Angee exotic-pony on astra/invoice-form-contract. UI `http://127.0.0.1:5174`; backend `http://127.0.0.1:8601/graphql/console/`; process-compose 8091. Verified current demo login `admin` / `admin` in this stack's own database, not the other agent's credentials.

Real Playwright testing found a blank screen: `arp.base/web/tsconfig.json` referenced host web one level too high. Corrected the relative path. Aligned host tsconfig's `allowImportingTsExtensions` with Angee's compiler contract. Vite-origin CSRF uses native `ANGEE_PUBLIC_ORIGIN` in the stack script.

Services now use tracked `scripts/accounting-dev.sh`, referenced by `angee.yaml`, without requiring handwritten ignored `.angee/run-*.sh`. Added `docs/accounting-dev.md`. Generated process-compose.yaml/run are excluded from Git. Python/pnpm locks cover the selected checkouts. Framework JS uses its own lockfile; ARPEE links source packages as workspace dependencies. Much of the pnpm-lock diff removes former external importer paths; infrastructure review should account for this.

Browser: successful login, demo sales list loaded, `/accounting/invoices`, `/accounting/payments`, and `/accounting/payments/new` opened. No page errors or HTTP>=400 on these three accounting pages; Partner Type appears in list/form. Login still has a separate external-worktree background-image 403 and rejected console requests before authentication; accounting works after login. Screenshots/logs remain only in ignored `.angee/browser*`.

**Limitations/next.** Full frontend typecheck fails on outdated `sidebar`, `recordPath`, `MutationDialog`, resource-route/model-slot contracts, and separate React type instances across two node_modules; recursive framework-fragment checks also expect generated gql under another topology. Passing accounting alone does not resolve this. Frontend compatibility needs a separate package before a green overall build. Complete reconciliation graph/unreconcile and stronger posted immutability remain unimplemented. This package fixes payment registration; it does not establish production readiness or rewrite historical incorrect refunds.

Final checks: `makemigrations --check --dry-run`: No changes detected; both `git diff --check` and Ruff on changed owners pass. Temporary PostgreSQL stopped; baseline worktree removed. Main django/web remain running. No commits/merge: changes remain in the two agreed worktrees for review.

## 011 — Network access

At the user's request, changed backend binding from `127.0.0.1:8601` to `0.0.0.0:8601`; Vite explicitly uses `--host 0.0.0.0` on 5174. Updated tracked `scripts/accounting-dev.sh` and documentation; restarted both services through their process-compose 8091. Internal Vite→Django proxy remains loopback. Verified listening sockets and HTTP access through the environment's network IP.

## 012 — Updating from litnimax/angee-django

At the user's request, fetched origin and fast-forwarded astra/invoice-form-contract from `64f1d175` to `1f2b33c8` (origin/main). The update changes 296 files, including Django-native composition and new published dependency versions. Main checkout /workspace/angee-django was not switched.

Preserved the local resource patch in stash `accounting resource ordering before upstream 1f2b33c8`, then reapplied it. Resolved two conflicts, retaining upstream Dataset/read_groups, router-based single-database validation, and error-to-source-row mapping, plus local row/grant dependency order and hooks after grants. Updated the local regression to the new upstream fixture API. Kept stash as backup. Ruff/diffcheck pass; no unresolved conflicts. Framework uv sync completed.

**Startup incompatibility.** ARPEE build on the new framework raises ImproperlyConfigured: accounting.Invoice redeclares parent field 'created_at' from accounting.JournalEntry; use a narrow abstract child/donor with only its contributed fields. The new composer rejects the former inherited timestamp child/donor shape. Backend is unavailable after autoreload; Git update is complete, but working-stack compatibility is NOT verified. Native-composition adaptation is needed separately; broad business-model changes/database migrations were not performed as part of pulling upstream.

Targeted resource suite: 23 passed, 23 setup errors (Related model 'parties.Handle' cannot be resolved in upstream test registry), not green verification of the combined patch. Full suite not run after update. Earlier results do not automatically apply to 1f2b33c8.

## 013 — Adapting ARPEE to native composition

The user authorized adaptation. Materialized Invoice and all same-row donors now use narrow abstract Django models instead of AngeeModel; Invoice retains RebacModelBase for permission Meta. Removed obsolete child_overrides_parent. Business fields retain their owners; extensions no longer contribute generic timestamps/managers.

Resource participants use native ResourceLoadMixin and exactly one super().after_resource_load after their work. Demo-only contributors delegate even when skipped; early seed exits moved into owned helpers. Added install-tier integration coverage: accounting journals, sales/purchase sequences, CRM stages/reasons still appear after skipped demo work; repeated invocation does not duplicate rows.

Updated Hasura/aggregates/REBAC dependencies and recomposed the addon dependency group from manifests. Runtime build/schema pass. Migration diff contains only AlterModelOptions for VcsBridge, Directory, Organization, and Person; ARPEE columns are unchanged. Backed up SQLite to .angee/backups/before-native-adaptation.sqlite3 before applying migrations. Full provision --demo on empty native-cold.sqlite3: 437 created, 2 updated. Main data preserved.

First full PostgreSQL ARPEE run: 277 tests, 4 Discuss errors for missing MessageKind.USER_NOTIFICATION. Removed two obsolete filters; the new enum has no such member, and NOTIFICATION has a different purpose and was not substituted. Discuss rerun: 21 passed. Native hook regression: 1 passed. Full framework pytest is running without ANGEE_PROJECT_DIR.

Frontend now uses current route href owners, model-slot targets, typed MutationDialog.parseValues, and TanStack query isFetching; removed obsolete menu sidebar. Host tsconfig establishes one React type identity across checkouts. Host typecheck/production build pass; accounting browser smoke passes after restart. Discuss component tests still expose two React runtimes in Vitest; diagnosis/configuration continues. Final results follow.

## 014 — Adaptation final checks

**ARPEE:** full PostgreSQL run: 278 tests, OK, 64.689 seconds, including the hook regression and concurrent accounting/sales/purchase scenarios. All consumer frontend suites: 81 tests in 23 files passed. Host typecheck/build pass. Migration check: No changes detected. Ruff and both diffchecks pass.

**Angee:** full Python run: 1915 passed, 1 failed, 5 skipped, 1056.73 seconds. The sole failure was a new upstream expectation that hooks precede grants in test_native_import_pipeline_rolls_back_all_groups_grants_and_hooks, conflicting with the agreed hook-after-grants contract. Updated the expectation; also injected a post-grant hook failure and checked rollback of rows/M2M/ledger/grants/on_commit. Entire resource section with full registry collection rerun: 48 passed, 1873 deselected. The whole Python suite was not rerun after this test-only change; do not describe it as a new wholly green run. Collecting only resource directories lacks parties.Handle; used `pytest tests addons/angee/resources/tests -k 'test_resources or test_import_pipeline'`, without excluding resource tests.

**Frontend test infrastructure:** discarded attempts to inline every dependency or optimize unresolved direct transitive names. Final shared Vitest config deduplicates React/React DOM/router and processes logo/Base UI/Floating UI/Lucide through Vite. Discuss enables the client optimizer with nested @angee/ui dependency specifiers, including use-sync-external-store shims, so CommonJS peers use host React. No workaround dependencies added. All 17 Discuss frontend tests pass; full Angee App suite also passed: 214 tests, 24 files. The command with config-vitest actually ran the whole App suite; its actual result is recorded.

**Data/browser:** repeating resources load --include-demo on the separate cold database: 0 created, 0 updated, 439 unchanged. Restarted main stack retains demo data; invoices/payments/sales/purchase/CRM/calendar/discuss open. Verified real CRM records, calendar events, and general conversation history with no page/GraphQL errors. Fresh alice/alice login and new-invoice form verified. Anonymous login still makes rejected console queries before authentication, without blocking login. Login background now returns 200: Vite fs.allow contains exactly project root and the linked framework worktree.

Both services run on 0.0.0.0:8601 and 0.0.0.0:5174. Files remain in agreed ARPEE modest-toad and framework exotic-pony / astra/invoice-form-contract worktrees. No merge/commit/push. Reconciliation-graph and posted-immutability packages are outside this adaptation.

## 015 — Intermediate commits and reconciliation work

The user requested intermediate commits and the next package. Committed verified adaptation: ARPEE `4e75e5a` (`feat: validate accounting payments and adapt ARPEE to native Angee`), Angee `006ad59d` (`fix: preserve resource dependency order and linked frontend test runtime`). With no Git identity configured, used Codex <codex@openai.com> explicitly for these commits without changing global settings. Subsequent completed steps receive separate commits. No push.

`arp.accounting.JournalItemManager` remains reconciliation owner: PartialReconcile stores links/amounts; FullReconcile marks a fully settled connected component; `JournalItem.reconciled` means zero item residual. Odoo 19 references: `_reconcile_plan_with_sync`, `_all_reconciled_lines`, `_compute_amount_residual` in `account_move_line.py`; rules are independently implemented in Django. Sales/inventory already use atomic transactions and ordered locks; accounting owns this graph, with no generic graph framework/dependency needed.

Lock order for reconcile/unreconcile/Payment.register: Account → all connected JournalItem → Invoice. Account locks stabilize the traversal scope; PostgreSQL NO KEY UPDATE allows foreign keys during independent posting. Cost: reconciliations on one ledger account serialize. SQLite does not prove concurrency safety. Component calculation replaces stamping selected zero rows; unreconcile removes only selected matches, then recomputes the affected area. Include old full stamps to avoid leaving false markers on omitted items. Preserve valid existing stamps on repeated calls.

Planned checks: 100→40+60; removal via payment item; one payment across invoices; credit note plus payment; independent components; incompatible links rejected; registration/removal rollback; concurrent PostgreSQL register/unreconcile. No automatic historical rewrite or bulk reconciliation migration; only the explicitly operated area gets updated statuses/markers.

## 016 — Reconciliation components implemented

ARPEE `2959b40` (`fix(accounting): reconcile complete payment graphs and refresh all affected debt`) adds graph traversal, full reconciliation, recomputation after removal, unified Payment.register/reconcile/unreconcile lock order, and 14 regressions. Removed `_stamp_full_reconciles`. Validation checks account, entry/account company, item/document currency, posted state, and one receivable/payable partner; legacy GL/reversal items with missing partners on both sides remain supported. Unsaved/missing selections raise ValidationError. Unreconcile does not mark a zero draft item settled.

PostgreSQL: first targeted run 40 passed. After forced intersecting reconcile/unreconcile and currency scenarios, full ARPEE backend **291 passed**, 66.119 seconds. After final draft/non-reconcilable clarification, full accounting rerun **42 passed**, 6.890 seconds; entire ARPEE was not rerun after that clarification. A concurrent test pauses between match creation and total refresh, starts removal through a historical endpoint, verifies waiting, then residual 40 and all three document statuses. Concurrent Payment.register and register/removal races also pass. Existing authlib and dev-only InMemoryChannelLayer on_commit messages remain; reported results have actual exit 0.

Composed runtime builds; schema --check: ok; migration check: No changes detected. Ruff E/F/I uses framework configuration, line length 120; diffcheck passes. Initial lint without this configuration reported existing long lines; these were not hidden through new settings. No frontend/API changes; earlier frontend suites were not repeated for this package.

Browser after autoreload: invoices/payments/new payment open with the saved authenticated session, without page errors or HTTP>=400. The first smoke overlapped autoreload and saw temporary HTTP 502 responses; it is not counted as successful. The rerun log is clean. Backend /auth/csrf/ and frontend / return 200. Main SQLite/demo data were not overwritten; temporary PostgreSQL stopped.

Next: close posted-document update/delete/bulk/nested paths and validate entry aggregates before posting. This is outside `2959b40`; no bulk repair of historical invalid entries/reconciliation components. Account serialization remains an explicit throughput limitation.

The new module also ran separately on SQLite: **12 passed, 2 skipped** (PostgreSQL locking tests only), 0.701 seconds. This tests the dev stack's no-row-lock branch, not concurrency safety. Journal/analysis saved in Git; gist updates accompany completed iterations.

## 017 — Posted-ledger protection and atomic posting

Continued at the user's instruction. Accounting owns financial rules; shared Angee is unchanged. Inventory: Entry/Invoice/Payment lacked complete write/delete protection; bulk update/delete bypassed JournalItem.save, nested removal used `_base_manager`, and M2M had its own through table. Messaging/knowledge use Django lifecycle signals for cascading side effects, but signals do not cover bulk update/create of through rows. Models therefore provide domain errors; database triggers in a native addon-owned runtime migration enforce final immutability. No new dependency or custom shared framework. Odoo references: account_move `_check_balanced`, `write`, `unlink`, `_post`; account_move_line `write/unlink`. No partial imitation of unsupported Odoo lock-date/reopen protocols.

`LedgerDocumentMixin` and queryset read persisted state and reject closed-document editing/deletion, bulk status changes, and direct posted creation. Invoice exempts only derived payment_status; JournalItem reconciliation markers remain writable. Deleting users may null created_by/updated_by without changing financial facts. API delete_guard delegates to the model. Former configurable reopen now explicitly rejects even with allow overlay: there is no full unposting protocol; use reversal.

Entry/Payment `post()` own atomic scope around the complete transition, including final save_state, and lock persisted drafts before materialization/numbering. Native Invoice locks child and parent tables. Child totals persist before parent status changes in the same transaction, avoiding post-posting child edits. Validates at least two nonzero items, exact balance, company accounts, document/item/company currency, precision, journal ownership, invoice/bill journal compatibility, and company payment terms/taxes/distribution accounts. Forced-state persistence also validates aggregate/number. Nullable counterparties on old plain GL/invoice models are unchanged; full localization, tax-distribution rules, and zero-document policy need later stages.

Self-contained `posted_ledger_guards` adds INSERT/UPDATE/DELETE triggers to JournalEntry, Invoice, Payment, JournalItem, and tax through table: 15 total. They prohibit financial changes to nondrafts, new/reparented items, deletion, and M2M changes. PostgreSQL child writes take NO KEY UPDATE on the parent entry and recheck status after waiting; SQLite serializes writes. Triggers enforce immutability, not arbitrary administrator-SQL entry construction. Reverse migration removes triggers without rewriting data. Tested on both backends before registering/materializing as `accounting.0006_posted_ledger_guards`; source digest unchanged after materialization.

Initial checks: 28 previous accounting tests pass, then 14 new PostgreSQL domain/DB tests. A second concurrently started PostgreSQL run hit occupied test_postgres and did not execute; reruns are sequential. The new GraphQL test initially lacked triggers in its separate TestCase, confirming a nested-delete bypass; migration setup moved to a shared base for both classes and now passes. Real company accountant/reader API tests allow accountant draft edits, deny reader writes, and reject posted header update/delete/nested removal without data loss. Before the final race test: 57 PostgreSQL accounting/reconciliation/ledger tests and 15 SQLite ledger tests passed.

An existing reconciliation test deliberately seeds historically corrupted posted rows. Its fixture now reverses the migration within the test transaction, seeds corruption, and restores protection BEFORE reconcile. Reconcile assertions remain; product bypasses are not enabled. Added PostgreSQL posting-versus-bulk-insert test: posting pauses after entry creation, the insert waits on the parent and raises IntegrityError after commit. First full ARPEE backend: 308 passed, 70.012 seconds. Final full run follows native-parent lock refinement.

Backed up main SQLite to `.angee/backups/before-ledger-guards.sqlite3`; migration applied. Schema: ok; migration check: No changes detected; Ruff E/F/I and diffcheck pass. Migration does not repair/repost old entries. Frontend/SDL unchanged.

## 018 — Protection package completed and committed

ARPEE **`bcf604f`** (`fix(accounting): guard posted ledger writes and make posting atomic`). Final full PostgreSQL backend after all changes: **308 passed, 69.016 seconds**. Includes 16 new ledger tests, existing payments/reconciliation, accountant/reader API checks, and posting-versus-bulk-insert race. Last SQLite ledger run: **15 passed, 1.953 seconds**, before PostgreSQL-only race and `of=()` refinement; SQLite's no-lock branch was unchanged. No product tests disabled. Legacy-corruption fixture restores protection before the business operation.

`angee build --check`: ok; migration history/source digest consistent. Bidirectional EXCEPT against backup confirms unchanged JournalEntry, Invoice, Payment, JournalItem, tax through, PartialReconcile, and FullReconcile data. All 15 triggers installed. PRAGMA integrity_check through Django returns ok. The first bare sqlite3 attempt could not evaluate the existing generated MD5 column without Django functions; using the native connection fixed the check, without data repair.

Authenticated browser smoke passes invoices/payments/new payment without page errors, HTTP>=400, or login redirects. Backend /auth/csrf/ and frontend / return 200; both running. Temporary PostgreSQL stopped. New financial fields or rebuilt protected tables require a new protection migration; never edit published/materialized origins. Added this guidance to ARPEE `docs/accounting-dev.md`. No push; local intermediate commits retained and journal published to the existing gist.

## 019 — Taxes: first of two sequential steps

The user requested taxes and payment schedules, then specified “one by one.” No package changes had occurred after interruption before “working?”; this was stated explicitly. This iteration covers taxes only.

Inventory found the same sequential net_of_included error in Invoice, SalesOrderLine, and PurchaseOrderLine. Odoo 19 `account_tax.py` `_eval_tax_amount_price_included` uses summed percentages within a batch; `_eval_tax_amount_fixed_amount` computes quantity-based fixed charges independently of discounts. The independent Django implementation belongs to TaxQuerySet: price×quantity×(1−discount) = base×(1+sum(included rates)) + included fixed charges. TaxCompute strategies expose base coefficients/fixed terms through included_terms; Invoice/orders do not classify strategies by strings. Single-tax net_of_included remains compatible API but is not used for tax sets. Nonlinear/cascading strategies must extend the contract explicitly; no hidden sequential fallback.

TaxLine holds results and rounds documents by company policy. In per_document mode, round total tax first, then allocate currency units across rows using stable order for equal remainders. Preserve included gross: rounded base = rounded entered amount minus included taxes. This also fixes 0.05 with two included 10% taxes, where independent rounding lost a cent. TaxAmounts now uses actual largest-remainder allocation; removed putting the entire correction into the highest-percentage row.

Sales/Purchase share this calculation. Recomputing orders persists consistent header/line amounts, including per_document, instead of summing independently rounded previews. The saved line instance receives allocated amount fields so GraphQL/callers do not see stale previews. Regression: included 10%, lines 0.03/0.04 → tax 0.01, base 0.06, total 0.07; the second line returns base 0.03/total 0.04 immediately after save.

Tax.posting_distributions requires positive factors totaling 100% and explicit document-company accounts for the selected invoice/refund side. Missing distributions, 90/110%, negative factors, or missing accounts are not concealed by rounding/journal defaults. Only the active side is checked: invalid unused refund setup does not block invoices but does block refunds. Negative rates/withholding/factors were unsupported by the previous nonnegative GL; unsupported rates now explicitly raise ValidationError. No claim of full Odoo tax/localization parity.

Initial targeted PostgreSQL checks: 102 passed. With 14 new tax tests, full ARPEE backend: 322 passed, 71.903 seconds; SQLite tax module: 14 passed, 0.586 seconds. Covers 120→100+10+10 for four document kinds, debt signs, fixed+percent in both orders, quantity/discount, included/excluded, per_line/per_document, three-decimal currency, account allocation rounding, invalid-setup rollback, and shared accounting/sales/purchase totals. Final targeted run follows saved-instance amount refinement.

No new fields/migrations; migration check: No changes detected; schema: ok. Authenticated invoices/payments/new payment smoke passes without page errors/HTTP>=400. Framework/frontend unchanged; posted history is not recalculated, old draft/order totals update on normal save/recompute/post. Calculation/limits documented in ARPEE docs/accounting-dev.md.

## 020 — Tax step completed

ARPEE **`a8d9b13`** (`fix(accounting): compute included taxes jointly and preserve rounded totals`). Final targeted accounting/sales/purchase/tax after saved-return refinement: **104 passed, 18.675 seconds**. Previous full ARPEE: 322 passed; not repeated after this amount-return-only change. SQLite tax: 14 passed. Ruff E/F/I, diffcheck, and angee build --check pass; no migrations/SDL changes. Backend/frontend return 200; temporary PostgreSQL stopped.

Taxes committed separately per “one by one.” PaymentTerm/debt schedules remain unchanged and next. ARPEE clean after commit; same gist receives the journal, saved separately as an Angee docs commit. No push.

## 021 — Partner in invoice lists (2026-09-06)

At the user's request, added a partner Column immediately after document number in shared InvoiceWorkbench, using existing relation rendering and col.partner translation. Available in both Customer Invoices and Vendor Bills. Backend/schema/migrations unchanged.

ARPEE **`6b1be0f`** (`feat(accounting): show partner in invoice lists`). Authenticated smoke confirms Partner heading/populated names; invoices/payments/new payment open without page errors or HTTP>=400. Diffcheck passed. No new test for this one-line declaration.

Initial publication was rejected by automatic permission review. The user then explicitly authorized publishing this entry/checks to gist 44d67e5f0e656dbce5366693082b88dc with “go.”

## 022 — Compact analytic editor (2026-09-06)

The user reported a tall analytic_distribution JSON editor in invoice lines. Local Odoo 19 account_move_views.xml uses a specialized analytic_distribution widget, analytics group, and optional column; its template has compact tags and an account/percentage popover. The user authorized implementation with “go.”

**Owners/decisions.** arp.analytic owns the domain editor; accounting requests company through native returning for form context. Angee passes child row/parentRow without interpreting company fields. Found a contract gap: frontend registered addon widgets, backend allowed only built-in names. Extended the shared contract with namespace.addon.widget; unknown bare names/invalid segments still fail. Framework contains no analytic-specific concepts.

**Implementation.** arp.analytic.distribution displays account names/percentages compactly and uses native Popover/Table/RelationField/Input/Button. Apply moves valid distribution into the form; Save persists; Cancel leaves the form unchanged. Supports add/remove/clear/read-only, positive percentages up to four decimals, 100% per plan, no duplicate/unknown accounts. Server rules remain authoritative. Authorized typed GraphQL shares cache across cells; saved documents restrict choices to company. Archived accounts keep labels in saved distributions but are not new choices; inaccessible accounts are not silently removed. Loading errors offer Retry; no active accounts gives configuration guidance. New documents without company use the authorized catalog, with server company validation. No global analytics switch, column hiding, or Odoo mandatory/unavailable rules.

**Data.** analytic_distribution remains the same JSONField/public-ID→percentage map. Only inert angee_widget metadata added. Migration check: No changes detected. No distribution/posted-history rewrite; materialized origins unchanged.

**Checks.** Analytic frontend: 16 passed; accounting: 5 passed. Angee UI: 108 files, 726 passed; targeted context tests after fixture typing refinement: 5 passed. ARPEE backend: 42 tests OK, 2 PostgreSQL-only skips on SQLite. Framework metadata: 11 passed, 32 deselected. Architecture guardrails: 16 passed. Host/UI TypeScript, Vite build, Ruff E/F/I, diffcheck, angee build --check, and schema --check pass. Full ARPEE/PostgreSQL not rerun for this UI package.

**Browser.** Existing invoice has no CodeMirror; compact row/popover works without page/GraphQL errors. Separate temporary draft: Engineering 60% / Sales 40% → Apply → Save → reload; verified values in SQLite, then deleted the draft. No user invoice was used for writes. Frontend http://192.168.0.90:5174 returns 200.

**Intermediate errors.** Codegen rejected ASC because Hasura requires asc; query corrected. Added missing Python import after NameError. Real UI tests found duplicate React in linked checkout; reused Discuss optimizer configuration without component mocks. Framework pytest initially lacked libmagic; reran with .angee/env.sh. Final TypeScript error concerned optional fixture metadata, corrected using satisfies. No checks disabled.

**Commits.** Angee **daae5503**: qualified widgets/document context; ARPEE **eb04c24**: analytic editor/query/tests/docs. No push. PaymentTerm/debt schedule next.

Automatic review rejected the first attempt to publish entry 022. In response to the request to publish this entry to gist 44d67e5f0e656dbce5366693082b88dc, the user clarified: “I continuously authorize gist updates.” This is standing authorization to update the existing journal with decisions, implementation, checks, and commits; ordinary entries need no repeated permission.

## 023 — Aligned lines and compact tax selection (2026-09-06)

During PaymentTerm analysis, the user reported overlapping invoice-line fields. Before switching to this fix, schedules were only researched; business code/migrations were unchanged.

Causes belonged to Angee UI: EditableLines used auto tracks for empty header edges but button-filled row edges, misaligning headings/cells. Main columns used minmax(0,1fr), while widthless NumberField overflowed. Many2ManyEdit stacked tags and Select vertically.

Shared EditableLines now uses equal edge widths, minimum main-column widths, and extra M2M space. Narrow forms scroll only the line area; controls do not overlap. Float/Integer widgets fill their cells. Many2ManyEdit uses existing multiple SelectPrimitive: one row with first label/remaining count and a checked popup for selection/removal. Saved IDs outside loaded options stay visible/removable. Read-only has no editor. Tax formulas/API/data unchanged; all M2M fields using this widget benefit, including invoice selection for payments.

Checks: 7 targeted tests passed; after adapting two existing ActionFormDialog scenarios, full Angee UI: 108 files, 728 passed. Prefill/user-removal checks remain. UI/host TypeScript, Vite build, and diffcheck pass. No backend rerun for presentation-only changes.

Browser on a real invoice at 1280/1920 widths: aligned headers/cells, controls contained, no page-wide horizontal overflow. Row height fell from 78 to 50 px. Tax popup works without page errors/HTTP>=400. First check saw stale Vite prebundle; restarted through process-compose and reran successfully. User invoices were not saved. Frontend/backend proxy at 192.168.0.90:5174 return 200.

Angee **0b2287f3** — fix(ui): align editable line columns and compact multi-relation inputs. ARPEE unchanged. PaymentTerm/debt schedule next. Gist updates use standing authorization.

## 024 — Debt installments and payment schedule (2026-09-06)

The user authorized autonomous progress with a decision journal and intermediate commits. Completed the agreed PaymentTerm package. ARPEE **a815316** — feat(accounting): materialize installment debt and settle by maturity.

**Model/Odoo.** Local Odoo 19 account_payment_term._compute_terms allocates/rounds installments with final remainder; account_move_line stores date_maturity and orders payment items by maturity. ARPEE had compute_due but materialized one counterpart. Each nonzero maturity now creates a separate receivable/payable item. This independently implements the domain contract in Django, not Odoo runtime.

**Decisions.** Base date is invoice_date or entry date; without terms, use explicit due_date or document date. Empty terms mean immediate payment. Percent/fixed rules are positive; one final balance rule with amount=0 is allowed. Without balance, explicit portions must cover total before rounding; invalid configuration raises ValidationError and rolls back posting rather than silently correcting an arbitrary final portion. Round early installments using company policy, cap to remaining total, give the last the remainder, merge equal maturities, omit zeros. Preserve tax total across all four kinds. Header due_date is latest actual maturity. Early discounts, end-of-month terms, and FX remain unimplemented.

**Settlement.** Registration already selects all counterparts of selected invoices. Allocation now sorts them after locking by maturity, entry date, PK; lock acquisition retains PK order. Historical unknown maturity uses entry date only for ordering and stays NULL. Payment debt items receive payment date. Partial payments/top-ups/unreconcile preserve residuals/statuses. Editing terms after posting does not recalculate debt. Automatic invoice reversal retains the former no-payment_term contract; plain GL reversal copies maturity.

**Migration.** Self-contained installment_maturity materialized as accounting.0007: nullable indexed date_maturity plus all 15 updated guards protecting it. Frozen code intentionally copied into a new origin; former origins unchanged. Forward/reverse tested with historical posted items on SQLite/PostgreSQL. Backed up live SQLite to .angee/data/before-installment-maturity.sqlite3; bidirectional comparison of old columns in 15 accounting tables found no changes. Historical maturity NULL, 15 guards, integrity_check=ok. No reset/fake/backfill.

**UI/API.** Invoice/Bill Due date opens native Popover/Table with maturity, amount, residual, currency. Typed payment_schedule loads on open and invalidates with Invoice/JournalItem/Payment. Draft explains posting; legacy unknown dates are labeled; errors hide stale data and offer Retry. Real company-member GraphQL checked, including credit supplier debt; outsiders cannot see invoices. No framework business changes.

**Checks.** Full PostgreSQL backend: 333 passed, 73.701 seconds. After adding API authorization: 12 targeted passed, 3.737 seconds. Initial 11 scenarios also pass SQLite. Accounting UI: 3 files, 9 passed. Host TypeScript, Vite build, configured Ruff, diffcheck, migration/build/schema checks pass. Large-JS-chunk warning predates changes. Browser inspected a user draft's compact control/popover without writes, overflow, page errors, or HTTP>=400. Live demo had no posted documents; installment/payment scenarios ran in test databases. Services remain 0.0.0.0, frontend :5174.

**Diagnostics.** Replaced unavailable python with python3. Go angee build builds containers; manage.py angee build composes runtime. Negative-rule test needed a StateField savepoint; reverse test used an in-place-mutated ProjectState; fixtures corrected. API isolation initially inherited elevated setup, so moved reads to a separate nonelevated class. Raw sqlite integrity check lacked Django MD5; verified through Django. Backend process is django; web restarted and autoreload picked up changes. Checks were not weakened to hide these errors.

Next: period lock date, backdated-posting rejection, controlled settings, then numbers/audit/reports. No push. Publication continues under the user's standing gist authorization.

## 025 — Period closing and dated corrections (2026-09-06)

Continued under standing autonomous-progress authorization. ARPEE **37b9108** — feat(accounting): enforce company period locks and dated reversals. Previous schedule package **a815316**; entry 024 saved as Angee docs **2a52eff8** and published to gist.

**Ontology/scope.** Odoo 19 company.py distinguishes global/tax/sales/purchase/hard lock dates; account_move checks fiscal locks. This stage implements a reversible general posting prohibition on/before the closing date. Irreversible hard locks, tax boundaries, parent-company inheritance, personal exceptions, and automatic date shifts need separate rules and are not added. PeriodLock belongs to arp.accounting and references company; arp.base gains no accounting API. One policy/company; NULL/absence means open.

**Settings/audit.** Accounting → Configuration → Period Locks shows company, Closed through, reason, and change information. Reason required; AuditMixin/HistoryMixin version ordinary model/API writes. Reopen by clearing the date with a reason. Deletion/company transfer are prohibited, including direct ORM bypasses. company_admin/accounting_admin configure; accountant reads/posts but cannot reopen. Company admin does not acquire reversal permission in place of accountant. Arbitrary SQL-maintenance history is not claimed as full DB audit.

**Posting/concurrency.** Invoice/JournalEntry/Payment read current policy before materialization/numbering. Five new triggers guard posted transitions and policy writes. PostgreSQL posting takes FOR SHARE on company; policy changes take FOR NO KEY UPDATE. A separate policy query after waiting observes committed closing, including a first-INSERT race. A passing race test proves direct ORM status update waits for uncommitted policy and then fails. Policy changes need no individual entry locks. SQLite remains sequential development infrastructure.

**Corrections/debt.** Found an old UI gap: editable Invoice date but not Accounting date; reverse always used source date. Draft Invoice/Bill now exposes Accounting date. Native ActionFormDialog requires Reversal date and creates a draft on the chosen open date. API date remains optional; without it, source date is checked. Posting rechecks locks if policy changed after draft creation. Source unchanged. Closed-period debt may be paid in an open period; reconcile/unreconcile change only derived residual/status and are not blocked by source invoice date.

**Migrations/live data.** Native makemigrations created PeriodLock/HistoricalPeriodLock as accounting.0008; subsequent angee build materialized self-contained period_lock_guards as 0009. Prior origins untouched. Backed up .angee/data/before-period-lock.sqlite3, applied migrations/rebac sync to modest-toad, restarted Django/Vite through process-compose. Bidirectional comparison of old columns in 16 tables (15 accounting + arp_company): unchanged; five new guards present; integrity_check=ok. No live policy created; no company period automatically closed.

**Checks.** Final full PostgreSQL backend: **344 passed, 77.165 seconds**. Targeted period/installment: 22 passed PostgreSQL; SQLite: 22 tests OK, 1 PostgreSQL-only skipped. Accounting UI: 3 files, 9 passed. Host TypeScript/build, configured Ruff, diffcheck, migration/build/schema checks pass. Browser inspected Period Locks list/create and existing invoice Accounting date without saves, HTTP>=400, or page errors; form visually checked without overlap. Frontend http://192.168.0.90:5174 works; backend verified by real browser GraphQL reads.

**Intermediate failures.** First reversal-date edit missed the exact source line; reapplied to the typed fields declaration. First full run: 343 passed, one reversal permission failure because fixture user had company_admin without accountant. Corrected fixture role, not product permissions; targeted/full reruns green. Closed through browser locator matched label and date button; corrected to the button's accessible name. Scenario error, not form failure.

**Next.** Debt schedule/general period control complete. Separate next packages: number uniqueness/policy and correction audit; GL/Trial Balance; historical aging; BS/P&L; then bank intermediate accounts/statements/matching and FX. Localization/regulatory forms remain separate. No push. Gist publication uses standing authorization.

## 026 — Posted-number uniqueness (2026-09-06)

Completed after the next Go. ARPEE **766e64b** — fix(accounting): enforce posted number uniqueness and payment identity.

**Policy/Odoo.** Odoo 19 account_move.py uses a posted name/journal_id partial unique index excluding `/`. ARPEE JournalEntry is unique by company/journal/number; Payment by company/number. Company explicitly participates. Drafts reserve nothing; no slash placeholder. Posted numbers are nonempty, trimmed, at most 64 characters. Payment and entry share a number. Clear model validation complements independent DB constraints.

**Transactions.** Manual conflicts, constant sequence templates, or duplicate Payment numbers roll back posting, new items, and counter advancement. No automatic conflict skipping or silent renumbering. Year format/templates remain sequence configuration. PostgreSQL manual-number race has exactly one successful posting.

**Migration/data.** Frozen posted_number_uniqueness, accounting.0010, first checks historical duplicates/format/payment-entry consistency, then creates two partial unique indexes and two UPDATE guards. Existing triggers remain; ledger guards already reject posted INSERTs. No SQLite table rebuild. Forward/reverse checked on isolated schemas on both databases. Backed up .angee/data/before-number-guards.sqlite3; 18 old tables unchanged, integrity_check=ok, both guards present. Periods remain open.

**Checks.** Targeted PostgreSQL numbers/period/ledger/accounting: 62 passed, 13.127 seconds. SQLite numbers/period: 18 tests OK, 2 PostgreSQL-only skips. Ruff/diffcheck/migration check pass. Full regression will accompany Trial Balance. Raw period-lock update test now supplies a valid number to reach the intended guard. Retry test reloads Django instance after rollback, which does not restore in-memory fields. Isolated migration test uses independent index names; production origin unchanged after materialization.

**Boundary.** Chronological continuity, administrative sequence-change audit, and country-specific numbering are not implemented. Next: authorized posted-fact Trial Balance, then GL/aging. No push; gist publication remains authorized.

## 027 — Trial Balance and exact CSV (2026-09-06)

ARPEE **785e9d7** — feat(accounting): add authorized trial balance and exact CSV export. Previous number controls **766e64b** recorded in Angee docs **370b1947**; entry 026 published. Packages proceed sequentially under autonomous authorization.

**Ontology/calculation.** Odoo 19 addons/account/models/account_report.py:601 distinguishes from_beginning, to_beginning_of_period, strict_range, and fiscal-year scopes. This implements a specific cumulative posted-ledger Trial Balance, not all of account.report. Company/inclusive accounting-date range required. Opening includes all pre-start dates, debit/credit movements include both boundaries, closing equals opening plus debit minus credit. Split account balances into debit/credit. Include archived accounts with balances/movements and zero-net activity; omit empty accounts. Exclude draft/cancelled/future. Payments/refunds contribute via entries. Accumulation crosses year boundaries; no implicit retained-earnings transfer/P&L closing.

**Access/integrity.** reports.trial_balance permits company member/accountant. GraphQL requires session/visible company, then owner checks full-report access. A bounded system_context reads only that company after authorization; partial ledger visibility cannot masquerade as complete reporting. One SQL aggregate supplies rows/totals; three debit/credit pairs are checked. Foreign/missing accounts and entry/current-company currency mismatch fail, preventing historical amounts from being silently relabeled. No FX conversion yet.

**Contract/UI.** Pydantic owns amounts/row/report once; Strawberry pydantic_node publishes a typed parameterized snapshot; codegen supplies React types. Nonpersistent reporting uses existing authored query + RowsListView, as activity agenda does, not a fake CRUD resource or Hasura filter parameter channel. Business logic stays ARPEE. Accounting → Trial Balance, /accounting/trial-balance. ActionFormDialog collects company/From/To; MetricStrip shows six totals; RowsListView handles local search/pagination. Parameter changes/errors hide mismatched/stale snapshots. Refresh and Export full CSV available; UI labels totals/export as full-report values.

**Money/export.** Backend rounds Decimal to company-currency precision; frontend formats the integer part with BigInt, never converting money to Number. Monetary sorting disabled until shared exact Decimal comparison exists; code/name sorting remains native. CSV preserves Decimal strings, all rows/TOTAL, parameters/currency/generated_at, UTF-8 BOM/CRLF, quote escaping, and text-formula protection. No migrations.

**Checks.** Full PostgreSQL regression after both packages: **358 passed, 82.695 seconds**. 6 report scenarios pass PostgreSQL; numbers/reports SQLite: 14 tests OK, 1 PostgreSQL-only skip. Covers opening/boundaries/single day/prior year/payment/refund/archived/draft/cancelled/future/empty ledger/3-decimal KWD/currency changes/isolation. Real GraphQL actors: member/accountant allowed; partial-access viewer/outsider denied. Accounting frontend: 4 files, **12 passed**, including beyond-Number precision, locale/scale, escaped full CSV. TypeScript/build/Ruff/diffcheck/migration/build/schema checks pass; old Vite chunk warning remains.

**Stack/browser.** Restarted through modest-toad process-compose. Verified real reports for Angee Trading NV/Beta Subsidiary Ltd, reopened parameters, company change without stale snapshot, Refresh, CSV download. Live database has no posted documents, so both reports are zero; nonempty calculations are tested only in test databases. User drafts not posted. Viewed .angee/browser/trial-balance.png: no overlap/overflow/page errors/HTTP>=400. .angee/browser/trial-balance.csv contains selected company, EUR, dates, zero TOTAL. Temporary PostgreSQL stopped; SQLite/main web remain 0.0.0.0:8601/5174.

**Diagnostics.** Incorrect manage.py angee schema corrected to passing manage.py schema --check. Browser initially sought combobox/Select; native relation is button with aria-label Company, then Company: <name>. Corrected scenario accessible names, not product selector. Rerun passes.

**Next.** GL drilldown, historical aging rather than current residual, BS/P&L, explicit year closing; then bank intermediate accounts/statements/matching, FX/localization. No chronological gap/admin sequence audit yet. No push; gist updates remain authorized.

## 028 — Trial Balance drilldown to General Ledger (2026-09-06)

Continued after “Let's move on” under standing authorization. ARPEE **818b63c** — feat(accounting): drill trial balance into chronological general ledger. GL package complete; aging next.

**Architecture/Odoo.** arp.accounting.reports owns calculations/full access; Pydantic row/report, Strawberry publishing, typed authored query for UI. TanStack Router/useRouteHref owns URLs; useResourceRecordHref owns record links; RowsListView/MetricStrip owns table/metrics. Compared messaging ActivityAgendaList and CRM PipelinePage for calculated-list/native-resource navigation. No new consumer table/form or framework business API. Odoo account_move_line._compute_cumulated_balance uses balance/explicit order; chosen order: accounting date → entry PK → position → item PK. Positive debit, negative credit.

**Snapshot/access.** general_ledger takes company/account/inclusive period. Shared Trial Balance gate checks member/accountant, period, currency; GL checks company account ownership. Archived allowed; foreign/missing rejected. Pre-start history aggregates by currency in SQL, period movements remain complete; one UNION ALL statement reads both. Opening/movements share one snapshot without loading all history or collapsing duplicate rows. Mixed opening currency is detected. Running balance/totals use this result; unchanged-ledger totals match Trial Balance. Navigation from an earlier Trial Balance performs a fresh read, not a frozen old snapshot.

**Navigation/presentation.** Trial Balance account codes open GL with company/account/dates. Trial Balance parameters moved from local React state to URL, preserving reload/Back/return. GL shows YYYY-MM-DD date, number, journal, item partner, label, debit/credit/running balance; numbers open native read-only JournalEntry. Opening/closing/movements, Refresh, return link provided. Sorting disabled to preserve running-balance order. Local filters do not recalculate balances/totals; caption explains this. No movements does not erase opening.

**Export/money.** CSV includes OPENING, chronological items, TOTAL / CLOSING, parameters/time. Negative Decimal columns remain numeric; text is formula-safe. Shared report-format owns both reports' formatting/download; removed Trial Balance copy. Fixed small credit -0.12 losing its sign when the BigInt integer part became zero. No Number conversion, data-schema/migration/financial changes.

**Checks.** Reports: **12 passed SQLite, 2.902 seconds**, **12 passed PostgreSQL, 4.394 seconds**. Six new scenarios cover Trial Balance agreement, boundaries/payment/refund, duplicates/order, opening-only/archived/empty, invalid periods/accounts/historical currency, three decimals/requery, and GraphQL member/accountant versus viewer/outsider/foreign account. Snapshot test verifies one UNION ALL. Full PostgreSQL: **364 passed, 85.210 seconds**. Accounting frontend: **5 files, 16 passed**, including -0.12/large negatives/CSV repeated rows/opening/closing/URL parsing. TypeScript/build/Ruff/diffcheck/build/schema/migration checks pass; existing large-chunk warning remains.

**Browser/data.** Restarted services. Real existing-account API verifies empty GL/zero balances/URL reload/CSV. No posted live documents; no user drafts posted. A separate UI fixture intercepting report queries verifies negative balances/two rows, Trial Balance→GL, existing entry ID→real record, Back, return with dates, export. Nonzero backend calculations are proven in test databases, not by the UI fixture. Screenshot viewed: no overlap/overflow/page errors/HTTP>=400. Test PostgreSQL stopped; main SQLite stack running.

**Diagnostics.** First browser run before Vite readiness hit ERR_CONNECTION_REFUSED; rerun after readiness passed. Ruff import order/three long test lines fixed. Screenshot exposed relative “7 months ago”; GL now explicitly renders accounting dates and browser asserts two exact dates. Repeated typecheck/build/browser pass; no weakened checks.

**Journal publication.** Automatic review rejected the first write/publication of 028 over external-journal purpose/content concerns; command did not execute. Read-only GitHub verification confirmed existing litnimax gist 44d67e5f0e656dbce5366693082b88dc, public=false, sole file accounting-implementation-log.ru.md. Content includes agreed entries through 027; 022 records standing authorization for this journal. The new entry contains no credentials, financial-document contents, network addresses, or operational paths, only requested decisions/implementation/checks. It is committed locally first, then publication is retried with this evidence.

**Next.** Historical aging must reconstruct settlement/removal effects instead of substituting current residual. Then BS/P&L, explicit year closing, bank intermediate accounts/statements/matching, FX/localization. No push.

**028 publication status.** Review rejected sending again even after owner/content verification: it requires direct trusted confirmation of this external address and considers local records of prior authorization insufficient. No bypass attempted. Entry 028 remains local; gist remains at 027. The user is told the exact destination and asked to approve the prepared entry. GL implementation/tests/live stack are complete independently.

**028 published.** The user answered “go” to the explicit gist confirmation. Update succeeded; the blocked status above describes earlier attempts only.

## 029 — Clarifying Odoo aging semantics (2026-09-06)

Before implementation, inspected local account_partial_reconcile: max_date is the maximum debit_move_id/credit_move_id date, explicitly documented for aged receivable/payable reports. Both ARPEE/Odoo unreconcile delete current partial matches. Chosen contract: accounting cutoff using current links; a partial reduces debt only when both entries' accounting dates are on/before the cutoff. Future payments are restored to historical residual even if current residual is zero.

Clarification of the earlier “settlement/removal events” wording: ordinary Odoo-style aging does not need an invented unreconciliation date. Rerunning after unreconcile uses changed links, as restated reporting. Auditing “what the system knew then” is a separate temporal contract; the existing model cannot restore deleted matches, and this is not claimed implemented. This keeps Odoo as business ontology and avoids replacing accounting-event date with button-click time.

Owner: accounting.reports with existing full-company checks. Django Subquery/Sum computes dated matches in the same SQL statement as debt items; GraphQL/Pydantic owns the typed snapshot and Angee RowsListView/ActionFormDialog presentation. Include receivable/payable, credit balances/advances, historical NULL as Unknown maturity, Not due and 1–30/31–60/61–90/>90 buckets. Planned tests: future/partial payments, bucket boundaries, unreconcile, currency, access, GL reconciliation. Financial data/posting rules unchanged.

## 030 — Receivable/payable aging at a selected date (2026-09-06)

ARPEE **f76d963** — feat(accounting): add dated receivable and payable aging. Entry 028 published after user “go”; semantic clarification 029 committed as Angee docs **566327df** and published before completion.

**Calculation.** reports.aged_balance reads posted JournalItem on asset_receivable/liability_payable with accounting date <= As of. It does not use current amount_residual/payment_status for historical cutoffs. Correlated Subquery/Sum includes partials only if both posted endpoints are on/before As of, matching Odoo max_date. All rows/matches share one statement. Fully paid current invoices recover pre-payment debt; future invoices do not erase earlier advances. Ordinary payables are positive, their advances/refunds negative; receivables are debit-positive. Archived accounts, no-partner items, and credit balances included.

**Maturities/totals.** Each outstanding installment retains its maturity. Today/future is Not due; overdue buckets 1–30, 31–60, 61–90, >90. NULL is separate, never replaced by invoice/today's date. Settled-at-cutoff items omitted; opposite unmatched residuals remain even with zero total debt. Totals use the same rows and reconcile to GL, with reversed payable sign.

**Permissions/boundaries.** Full company member/accountant required; partial viewer/outsider denied; invalid kind rejected. Incompatible account/company/currency, nonpositive matches, or settlement exceeding an endpoint fail. Historical foreign amounts are not relabeled. Current links/catalogs define the report; unreconcile changes a rerun. No reconstruction of past system knowledge is claimed. Deleted matches require separate event history; entry 029 and technical docs explain this distinction.

**Contract/UI.** Pydantic AgingAmounts/Row/Report, Strawberry aged_balance, generated types. Accounting → Aged Balances has Aged Receivables/Payables. ActionFormDialog collects company/As of/kind in URL. RowsListView shows account/partner/number/exact date/maturity/bucket/residual; number opens JournalEntry. MetricStrip has six buckets/total. Errors/parameter mismatch hide old snapshots. Existing owners provide Refresh, local filter/pagination, full CSV; no new shared components/dependencies.

**CSV.** Retains company/currency/kind/As of/generated time. ITEM, BUCKET_TOTAL, TOTAL are explicit. Unknown maturity stays empty; credits/advances retain numeric negative signs. Shared formatter avoids Number; text is formula-safe. UI explains local filters do not narrow totals/export.

**Checks.** Aging: **8 passed SQLite, 2.157 seconds**; all reports: **20 passed PostgreSQL, 6.393 seconds**. Covers future/partial payment, currently paid invoice, future invoice/earlier advance, unreconcile/opposite unmatched balances, every bucket boundary/NULL, bill/refund/payment/draft/cancelled, installments, 3-decimal KWD/archived/foreign company, invalid kind/currency, excess partial, real GraphQL permissions. SQL test proves one selection with correlated sums. Full PostgreSQL: **372 passed, 86.531 seconds**. Accounting frontend: **6 files, 19 passed**, exact large/negative amounts, unknown maturity, CSV types/URL. TypeScript/build/Ruff/diffcheck/build/schema/migration checks pass; existing chunk warning remains.

**Browser/data.** Restarted via process-compose. Live browser verifies company form, receivable/payable switch, URL/reload, zero report, CSV. Separate report-query fixture checks negative amount, NULL maturity, absent partner, exact dates, real existing entry record/Back, and both rows/totals in CSV. Nonzero calculations are proven in test databases, not this UI fixture. Viewed 1280 screenshot; 1280/1440 checks show no overflow/page errors/HTTP>=400. User drafts not posted; no migration/financial changes/push. Test PostgreSQL stopped; SQLite stack running.

**Diagnostics.** Installment fixture initially supplied nonexistent PaymentTermLine.position; corrected to the existing owner's native ordering without model changes. Ruff fixed import order/two long lines. Targeted/full reruns pass; initial failures were not presented as readiness.

**Next.** Trial Balance→GL/historical aging complete. Next BS/P&L with explicit classification/result rules, then year closing. Bank intermediate accounts/statements/matching, FX, sequence-administration audit, localization remain later. Same authorized gist continues.

## 031 — Balance Sheet/P&L contract (2026-09-06)

Started financial statements under autonomous authorization. Local account_account derives internal_group from account_type and excludes income/expense from include_initial_balance; ARPEE already has five required AccountKind families. AccountKind.internal_group owns classification, not account code/UI/a mapping table. No new account kinds or statutory chart needed.

financial_statements uses existing trial_balance extended with account kind, sharing one authorized SQL snapshot/currency/generated time. Balance Sheet is cumulative at date_to; P&L uses inclusive date_from..date_to income/expense movements. Remaining income/expense balances enter equity as calculated result split before/within period. This is an arbitrary reporting period, not automatically a fiscal year. Posted transfers to equity reduce income/expense and increase booked equity without double counting.

Account rows drill into GL from inception for Balance Sheet or selected period for P&L; calculated results open corresponding P&L ranges. Existing Angee forms/tables/metrics/URL owners follow Trial Balance/GL/aging and ActivityAgendaList. Year-close posting remains separate; reports write no ledger facts and do not hide arbitrary manual closing entries from P&L.

## 032 — Balance Sheet and Profit & Loss implementation (2026-09-06)

ARPEE **940d772** — feat(accounting): add balance sheet and period profit loss statements. Contract 031 committed as Angee docs **4b421e84** and published during work. Year closing remains separate as announced.

**Owner/data.** Added nonpersistent Odoo-style AccountKind.internal_group. TrialBalanceRow adds kind selected in the same aggregate. financial_statements derives both reports from authorized Trial Balance, inheriting company/member/accountant, date/currency/account-company checks. No duplicate ledger SQL engine. Invalid kind/unsupported group is not silently equity. No catalog/financial changes or migrations.

**Formulas.** Cumulative Balance Sheet through date_to: assets debit-positive, liabilities/booked equity credit-positive. P&L income minus expense yields period_result within inclusive boundaries. Refunds reduce categories; loss stays negative. Accounts with actual activity but zero net remain. Unallocated income/expense enters equity split before/within period. Posted equity transfers are not double counted. Changing start changes profit split, not Balance Sheet at fixed end. Check assets = liabilities + equity plus Trial Balance checks.

**Period semantics.** Explicit user-selected range, not an inferred fiscal year. No closing entries created; arbitrary manual transfers remain visible in P&L. Formal year closing/separate statement treatment unimplemented. Current catalogs define restated reports, not saved historical classification versions.

**UI/drilldown.** Accounting → Balance Sheet/Profit & Loss share FinancialStatementsPage, two routes, ActionFormDialog/RowsListView/MetricStrip, one typed query. URL parameters survive switching/reload/Back. Balance Sheet account→GL from inception; P&L account→selected period; prior/current result→corresponding P&L. Metrics show assets/liabilities/equity/difference or income/expense/result. Errors/mismatched snapshots hide old values. Shared initialReportDates replaces duplicated suggested-calendar logic; financial rules do not depend on that suggestion.

**Export.** ACCOUNT, RESULT, TOTAL with company/currency/range/generated_at/row drilldown range. Balance Sheet also exports booked equity, prior/period/unallocated result, controls; P&L only its rows/totals. Local filters do not narrow export/totals. Large/negative Decimal avoids Number; names are formula-safe.

**Checks.** New statements: **9 passed SQLite, 1.705 seconds**; statements/prior reports: **21 passed PostgreSQL, 6.558 seconds**. Covers assets/liabilities/equity on invoices/payments, one SQL aggregate, before/after periods, no double equity transfer, losses/refunds, draft/cancelled/future, single-day/date.min, zero-net activity, archived/code-independent classification, corrupted kind, KWD/foreign company/currency changes, real permissions. Each row reconciles to GL or drilldown P&L. Full PostgreSQL: **381 passed, 88.482 seconds**. Accounting frontend: **7 files, 22 passed**, large exact CSV/negative result/drilldown boundaries/empty reports. TypeScript/build/Ruff/diffcheck/build/schema/migration checks pass; existing Vite warning remains.

**Browser/stack.** Restarted Django/web. Live API verifies company form, zero Balance Sheet/equality, URL/reload, P&L switch, CSV. Separate report-query fixture supplies asset/liability/two equity-result rows and income/expense; checks Balance Sheet→GL date.min, P&L→GL period start, both results→P&L, Back/CSV. GL reads real accounts; live documents not posted. Both screenshots viewed, no 1280 overflow/overlap/page errors/HTTP>=400. Test databases prove nonzero formulas; fixture is not claimed as live accounting. Test PostgreSQL stopped; SQLite stack running.

**Diagnostics.** Ordinary save correctly rejected unsupported kind through StateField before reporting; legacy-corruption test now uses explicit test SQL, without weakening writes. PostgreSQL fixture initially failed on account code >16 characters; shortened fixture only. Targeted/full reruns pass. Ruff fixed imports/two long lines; setup errors were not bypassed by disabling checks.

**Next.** Trial Balance, GL, aging, BS/P&L complete. Explicit year closing with permissions/date/repeat-transfer prevention/P&L semantics next; then bank intermediate accounts/statements/matching, FX, sequence audit, localization. No push. Authorized gist continues.

## 033 — Odoo report inventory and next package (2026-09-06)

User request: inspect Odoo Accounting reports and implement necessary ones. Sources: local Odoo 19 addons/account/views/account_menuitem.xml, data/account_reports_data.xml, report/account_invoice_report.py/XML; official catalog https://www.odoo.com/documentation/19.0/applications/finance/accounting/reporting.html . No local addons/account_reports: account.report definitions/tax localizations exist, but Enterprise handlers were neither examined nor claimed available.

| Odoo family | ARPEE before package | Decision |
| --- | --- | --- |
| Balance Sheet, Profit & Loss, Trial Balance, General Ledger | Implemented; GL drills from Trial Balance | Retain contracts |
| Aged Receivable / Payable | Historical maturity-based debt snapshot exists | Retain |
| Partner Ledger | No partner movements/balances | Implement with entry drilldown |
| Invoice Analysis | No management report | Analyze posted documents by partner/month/kind |
| Cash Flow Statement | Missing | Needs operating/investing/financing classification; bank movements alone are not this report |
| Tax Report/localized declarations | Missing | First retain tax/repartition provenance: current tax items have labels/amounts but no tax FK; do not recompute history using current rates |
| Analytic Report / budgets | Plans/accounts/posted analytic lines exist; no aggregates/budgets | Separate next arp.analytic package |
| Audit / review log | Record history/ledger protection exist; no summary audit report | Separate package with sequence audit |
| Invoice PDF / payment receipt | Document print forms | Separate from financial/management snapshots |

Owner map: posted entries/Invoice amount snapshots belong to accounting models; reports.py owns calculation/full-company access; Pydantic shapes, Strawberry thin resolvers. Existing RowsListView/ActionFormDialog/MetricStrip, TanStack URL, generated authored GraphQL own UI. Compared accounting reports, messaging ActivityAgendaList, CRM PipelinePage; reviewed stack dependencies. No new dependencies or financial writes needed.

Partner Ledger separates receivable/payable without netting. Opening includes all earlier posted movements; retain paid documents, advances, NULL partner, archived accounts. Debit/credit/signed balance remain debit-positive, including payables. Reconciliation does not alter movements. Summary/detail share one UNION ALL snapshot with SQL-aggregated history and complete period rows. Partner drilldown is URL state; browser does not calculate money.

Invoice Analysis has document granularity, unlike Odoo's product-line account.invoice.report, so saved amount_untaxed/tax/total are reliable without invented product tax allocation. Separate sales/purchases; refunds reduce their mode. Posted only, one company/currency, invoice date falling back to accounting date or explicit accounting basis. Native RowsListView groups documents by partner/month/kind; details open Invoice. Cost/margin/product pivots are not claimed. Dates/currencies/permissions/negative amounts/CSV/navigation are verified before commits.

## 034 — Partner Ledger / Invoice Analysis calculation (2026-09-06)

ARPEE **55dce0f**: authorized report snapshots, schemas, backend acceptance. PostgreSQL: **27 passed, 8.085 seconds** (15 new + 12 Trial Balance/GL). First 12 scenarios also passed SQLite, 2.463 seconds. Real GraphQL permissions compare member/accountant with viewer/outsider/foreign company. Covers opening/movements/closing, payments/refunds, reconciliation independence, archives, NULL partner, identical partner names, KWD, invoice/accounting date, NULL fallback, later tax-rate changes, draft/cancelled/future exclusion, one snapshot/report. Partner results reconcile with Trial Balance.

Invoice Analysis adds month/partner amount and document-count summaries, computed with backend Decimal from the same snapshot, not JavaScript Number. Same-name partners remain distinct IDs. UI provides Documents / By partner / By month; CSV includes documents, both summary dimensions, and total with explicit row types.

Inventory 033 clarification: official catalog also includes **Executive Summary**; ARPEE has no KPI contract yet. FX/loan/asset-specific reports depend on missing subsystems. Technical docs record these gaps; no complete Enterprise parity claimed.

Diagnostics: PostgreSQL guards correctly blocked post-posting SQL corruption. Two fixtures now explicitly simulate import before guards within rolled-back test transactions and restore guards before reporting. Production guards/posting unchanged. Report rejects foreign accounts/inconsistent saved totals. Another fixture expected partner-creation rather than document-date order; corrected independent-summary comparison to sorted amounts. Ruff/typecheck green; full regression/UI checks underway.

## 035 — Report UI, CSV, and completion (2026-09-06)

ARPEE **db0e614**: Partner Ledger/Invoice Analysis UI; calculation previously **55dce0f**. Angee docs **3271f453**, **20f90345** record inventory/intermediate decisions. Routes join Accounting near Trial Balance/aging. Framework business code unchanged: arp.accounting owns calculations/results; UI uses RowsListView/ActionFormDialog/MetricStrip/TextLink, typed queries, TanStack URL.

Partner Ledger: receivable/payable, partner opening/debit/credit/closing summary and chronological drilldown. NULL partner explicit; opening-only balance retained. Detail debit-positive, payable credits negative. JournalEntry owns record navigation; Back restores partner/period. Summary retains separate partners' debit/credit balances; their net reconciles with account Trial Balance. Invoice Analysis: sales/purchases, invoice/accounting basis, Documents / By partner / By month, same-name partners retain IDs. Numbers open Invoice; CSV preserves original accounting/invoice/report dates. Errors/parameter changes hide stale snapshots.

CSV metadata: company/currency/mode/dates/generated time. Partner Ledger: PARTNER_TOTAL / OPENING / ITEM / TOTAL; selected-partner export includes complete detail/opening. Invoice Analysis: INVOICE / PARTNER_TOTAL / MONTH_TOTAL / TOTAL plus document counts. Row types prevent summing detail with totals. Local pagination/search does not narrow export. Decimal strings preserve negatives and values beyond Number.MAX_SAFE_INTEGER; text formulas escaped. Native table toolbar owns report controls.

Checks: final new scenarios **15 passed SQLite, 2.621 seconds**; new plus Trial Balance/GL **27 passed PostgreSQL, 8.085 seconds**. Full PostgreSQL **396 passed, 92.197 seconds**. Accounting UI **8 files / 27 passed**. TypeScript/build/Ruff/diffcheck/build/schema/migration checks pass; no migrations. Existing Vite warning remains; limits were not raised to hide bundle size.

Browser: live company form, receivable/payable, sales/purchases, invoice/accounting basis, URL/reload, summaries/CSV. Live SQLite only has drafts, so reports are empty. Nonempty fixtures intercept only the two report queries: partner/opening-only/NULL, running balances, negative refund, month/partner totals, correct IDs, real records/Back/full export. Test databases prove nonzero calculations. Viewed 1280 screenshots: no overlap/overflow/page/HTTP errors. Initial helper relative fetch for Invoice ID returned frontend HTML; corrected read-only ID lookup through project host, not product routes/API.

Restarted through process-compose; confirmed **0.0.0.0:5174**, **0.0.0.0:8601**. Test PostgreSQL stopped. User documents not posted/changed; no push. Authorized gist continues. Two reports complete; Cash Flow, Tax Report, Analytic Report, Executive Summary, summary Audit remain separate with dependencies in 033–034. Document analysis does not claim Odoo product/margin pivots or its Enterprise engine.

## 036 — Cash Flow contract and owners (2026-09-07)

User explicitly requested Cash Flow. Odoo 19 catalog defines operating/investing/financing: https://www.odoo.com/documentation/19.0/applications/finance/accounting/reporting.html . Local Enterprise account_reports handler absent; implement a transparent independent direct-method ARPEE ledger snapshot.

Owner map: Account stores cash_flow_activity (operating/investing/financing/unclassified); asset_cash defines cash perimeter. Old/new arbitrary accounts default unclassified, not a policy inferred from code. Install chart explicitly classifies known categories; existing accounts use the native form. Classification/reconciliation changes restate past reports; no archived version implied. Permissions inherit account configuration/full-company report gate.

One SQL UNION ALL should include aggregated cash opening, all period cash-entry items, reconciled source-document items, and applicable partials. Both endpoints must be posted by date_to. Noncash documents alone are not flows. Pure cash↔cash transfers excluded; transfer fees remain expense. Ambiguous mixed entries explicitly unclassified rather than assigned invented categories. Matched AR/AP amounts allocate through saved source-document accounts; advances use AR/AP category. Complex netting/cash-endpoint chains without clear attribution remain unclassified without losing amounts.

reports.py/schema expose snapshots/thin resolvers; cash_flow.py owns selection/attribution. Analogs: FinancialStatements/PartnerLedger and ActivityAgendaList. Existing UI/query/URL owners retained. Move tax.py's allocator without duplication into accounting.amounts: one largest-remainder rule for tax/ledger attribution. No generic framework changes. Tests: opening+flows=closing, cash accounts=GL, partial/refund/date/currency/permissions/rounding/mixed/transfers, migrations on both databases, browser/CSV. New SQL writes limited to configuration/schema; no user posting.

## 037 — Cash Flow calculation, migration, rounding (2026-09-07)

ARPEE **84a3a71**. Added Account.cash_flow_activity and source runtime_migrations migration 0011; updated live SQLite without document changes or automatic classification of existing accounts. Install chart has explicit categories. Native accounting/account permissions govern configuration; company member/accountant gate reports, rejecting viewer/outsider/foreign company.

cash_flow.py owns one UNION ALL for opening/cash entries/partial-linked documents. Partial attribution also reads earlier matches on the same documents, consuming category balances before the period; otherwise three one-cent payments could all allocate to the first category. Order: max endpoint accounting date, partial PK; allocate against remaining categories with AccountingAmounts.allocate. Moved TaxAmounts to accounting.amounts as shared owner, without duplicating largest remainder; taxes use it too.

Direct counterparts use their own category; AR/AP matches use original document accounts, advances debt-account category. Future endpoints do not change earlier cutoff. Unreconcile changes attribution, not cash balances. Pure transfers create no FLOW; fees remain expense. Mixed entries, including cash net=0, and complex cash settlements stay unclassified. complete checks row presence independently of category net. Opening/closing/cash movements reconcile separately with GL.

Targeted: **15 passed SQLite, 2.375 seconds**; CF+tax **29 passed PostgreSQL, 4.772 seconds**. Covers three categories, opening/GL, transfers/fees, equipment payment/refund, mixed categories, prior allocations/rounding, future document/advance, unreconcile, noncash/draft/cancelled/future, mixed zero-net, complex settlement, unclassified offsets, archived cash, KWD, foreign company/historical currency change, excess partial, real permissions. Initial PostgreSQL UNION inferred NULL placeholders as text despite ORM output_field; added native Cast(NULL AS type) at SQL projection owner. Both backends pass. Full regression started separately.

Browser already checks live form/zero report/reload/views/CSV, then a report-only fixture for three activities/unclassified, source/payment/account configuration/GL/Back. Viewed 1280 screenshots without overlap. Fixture tests UI; test databases prove actual sums. Main drafts not posted. UI commit/full results follow.

## 038 — Cash Flow UI and completion (2026-09-07)

ARPEE **84a3a71** (calculation/classification/migration/allocator/tests), **f3fbd0e** (UI/CSV). Framework docs **535296c3**, **70e06930**. Accounting → Cash Flow: `/accounting/cash-flow`, modest-toad, http://192.168.0.90:5174/accounting/cash-flow.

Summary shows operating/investing/financing/unclassified; Flows filters activity; Cash accounts show opening/debit/credit/closing. Native RowsListView toolbar, ActionFormDialog, MetricStrip, resource links. Number opens cash entry; Settled document opens source; account opens cash_flow_activity settings; cash account→GL retains period. URL/reload/Back preserve parameters/view. Metrics opening/net/closing/difference; incomplete classification remains flagged even when balanced/category net zero. Errors/mismatch hide stale snapshot.

CSV: FLOW / CASH_ACCOUNT / TOTAL, company/currency/period/generated metadata, source entry, exact date/account/category/basis. Full export unaffected by view/filter/pagination. Negative/beyond-Number.MAX_SAFE_INTEGER Decimal remain strings; formula-safe text. Chart of Accounts list/form exposes category. Existing accounts stay Unclassified pending explicit policy; company resources were not reloaded.

Final checks: **411 passed PostgreSQL, 96.317 seconds**, full ARPEE; CF **15 passed SQLite, 2.375 seconds**; CF+tax **29 passed PostgreSQL, 4.772 seconds**. Accounting UI **9 files / 29 passed**. Ruff/TypeScript/build/diffcheck/build/schema/migration checks pass; existing chunk warning remains. Classification migration applied live SQLite and tested with other PostgreSQL migrations; amounts/entries unchanged.

Browser: actual empty posted ledger, company/period/equation/reload/three views/CSV. Nonempty fixture intercepts only CashFlow; other APIs real. Checks three activities/unclassified, negatives, URL activity selection, source/config/GL/Back, actual account Cash Flow Activity field, full CSV. Summary/Flows/config screenshots viewed at 1280 without overlap/overflow/page/HTTP errors. Fixture IDs test native navigation, not live accounting data. Separate databases prove nonzero calculations/cash-account=GL.

Restarted through process-compose, **0.0.0.0:5174 / 0.0.0.0:8601**. Test PostgreSQL stopped; no push/user posting. Cash Flow complete. Explicit limitations: single-company currency, restated classification/current reconciliation at accounting cutoff, ambiguous mixed/complex settlements remain detailed unclassified. Localization/FX/other reports remain separate.

## 039 — Tax Report sources and saved-data contract (2026-09-07)

User approved saved tax facts → Tax Report. Odoo 19 account_move_line.py stores tax_line_id, tax_repartition_line_id, tax_base_amount; account_reports_data.xml declares generic Net/Tax. ARPEE tax items only had label/account/debit/credit; current rates cannot reconstruct history.

Owner map: Invoice.tax_snapshot, typed Pydantic/JSON, stores posting assessment: version/currency, original tax ID/name/use/compute/rate/price-included, base/amount, distribution ID/factor/account/base-share/amount/item ID. Protected JournalItem tax_origin/tax_distribution FKs and tax_base_amount are filled by Invoice._materialize_tax_group/_create_tax_item. FK PROTECT retains references; catalog edits do not change snapshots. None means historical/unknown; version 1 with empty groups means proven no tax. Zero-rate base persists without artificial zero GL item. AccountingAmounts allocates distribution base-share exactly, avoiding duplicated base across accounts.

arp.accounting.tax_report owns one company/accounting-date-period snapshot with sales/purchases groups/distribution rows reconciled to actual tax items and Invoice.amount_tax. Refunds reduce their section. Document kind sets direction; tax.use is historical configuration. Existing rules permit either tax use on either document side; this package does not silently change that. Different historical parameters for one tax ID remain separate groups. Overlapping tax bases are not summed as company turnover.

Legacy invoices/manual tax entries without complete assessment are separate, with known amount/debit/credit but unknown base. Verified totals do not present incomplete coverage as a declaration. Country/statutory form/cash basis unset: generic accrual tax report only. No backfill from current names/rates. Migration updates Invoice/JournalItem guards while preserving append-only history.

Analogs: CashFlow/InvoiceAnalysis and ActivityAgendaList; existing Pydantic/Strawberry/authored-query/codegen/UI/URL/link owners retained. No new primitives/dependencies. Tests cover split/zero/included/fixed/refund/rounding/catalog changes/double-count prevention/legacy coverage/rollback/immutability/permissions/both databases/CSV/browser.

## 040 — 2026-09-07 — Tax facts and backend Tax Report

Implemented first package from 039 in `arp.accounting`: `tax_facts.py` defines versioned exact-Decimal saved assessment; `Invoice.post()` persists it with totals. Each nonzero tax entry gets protected tax/distribution references and allocated base. Base and amount use largest remainder. Zero rates retain assessment base without artificial zero GL entries.

Self-contained `0012_tax_provenance` adds nullable fields and recreates PostgreSQL/SQLite guards for expanded historical models. No historical recalculation. Posted assessments/provenance protected by DB; editing current names/rates/accounts does not rewrite old reports.

`tax_report.py` reads assessments and all period tax GL items in one `UNION ALL`, validates currency/document-tax total/complete related-entry set/signs/allocated bases/references. Corrupted assessments fail rather than return plausible totals. NULL assessments/manual unassessed entries are separate, make coverage incomplete, and are excluded from verified totals. Document kinds select sales/purchases; refunds negative; historical parameter differences form separate groups. Generic accrual only, no localized declaration/cash-basis recognition.

First-commit checks: 25 targeted PostgreSQL tests passed (11 new report/fact + 14 existing tax); existing 14 also pass SQLite. Covers sales/purchases/refunds/date boundaries/zero/fixed/included/distributions/remainders/3-decimal currency/later setup changes/legacy/manual/corruption/guards/isolation/GraphQL. Live SQLite migration applied without user-document changes. Ruff/diffcheck clean. Full regression/browser UI follow.

## 041 — 2026-09-07 — Tax Report UI, CSV, release, final checks

ARPEE `2fe9850`: facts/migration/report/backend tests; `073709b`: UI/query/navigation/CSV/frontend tests. Framework contains journal only; Tax Report remains consumer-owned. Entries 039–040 saved as framework `cd682607`, `91ffb195`.

Added Accounting → Tax Report (`/accounting/tax-report`). Native ActionFormDialog company/accounting-date parameters live in URL. RowsListView shows historical-tax summary, document/account distributions, Missing tax data. Group drilldown preserves period/filter; real Journal Entry/Account/Tax links. MetricStrip shows verified sales/purchase tax/difference. Missing assessments explicitly mark incomplete totals. Unknown amount is a dash; known zero is 0.00. Table filters do not recompute financial totals.

CSV retains complete snapshot: period/company/currency/generated time, COMPLETE/INCOMPLETE, historical tax parameters, distributions, missing facts, VERIFIED_TOTAL. Exact Decimal tests include beyond Number.MAX_SAFE_INTEGER and negative thousandths. Cross-tax bases are deliberately not summed as company turnover. Local declarations/fiscal boxes/cash basis remain future.

Final: **422 PostgreSQL tests OK, 100.134 s**, prior accounting/product/sales/purchase/analytic/related suites plus 11 new; **11 new SQLite tests OK, 1.861 s**, plus existing 14 tax tests. Frontend **10 files / 31 tests OK**, typecheck/build pass. Schema/migration/diff checks clean. Composer final check/frozen-migration formatting caveat corrected in 042. Existing large-chunk warning, no build errors.

Browser: live company/period, empty zero report, reload/all views/CSV. Report-query-only fixtures cover sales/purchases/refund/zero rate, URL drilldown/reload, real document/account/tax/Back, legacy zero versus manual unknown, full CSV. At 1280×1000 no overflow/page errors/HTTP 4xx/5xx/GraphQL errors. Artifacts: ignored `.angee/browser/tax-report-*`. No user drafts posted.

Restarted process-compose owners: Django 8601/Vite 5174 on 0.0.0.0. User URL http://192.168.0.90:5174/accounting/tax-report. Historical NULL remains unknown; new documents receive assessment at posting.

## 042 — 2026-09-07 — Final migration immutability verification

Final log review found initial `angee build --check` failed with source digest changed after materialization: Ruff reordered two tax_provenance.py imports after migration materialization/application. Operations were unchanged; test databases used the original materialized version. This was not a tax-calculation error, but violated reproducible-build requirements. This corrects 041's premature composer-success statement.

ARPEE `cca4f85` restores original import order. Source SHA-256 again exactly matches composer `a7c8d4aea202dc3e3032a74b1c0082976afef2ad833e8ca7aa318fb79e77ddd1`. Generated runtime/applied migration/database history untouched. Frozen source retains the import order Ruff I001 would change; no rule disabled. Application/test Ruff passes. Complete formatting before first materialization for future migrations.

After restoration, `angee build`, `angee build --check`, `schema --check`, `makemigrations --check --dry-run` all pass; last reports No changes detected. Financial logic unchanged from passing 422 PostgreSQL / 11 SQLite / 31 frontend and browser checks. Test PostgreSQL stopped; 5174/8601 confirmed LISTEN 0.0.0.0. Both branches clean after commits.

## 043 — 2026-09-07 — Updating Angee from origin/main and adapting host

User requested upstream update/work verification. Fetch confirmed origin/main `ceb77bf5`, 78 commits since common base; `astra/invoice-form-contract` had 32 own commits. Both trees clean. Stack topology uses local app/framework sources without managed slots. Merged origin/main in the selected worktree without switching /workspace/angee-django. Merge `e4f43358`; resolved resource_fields/field_classification import conflicts retaining upstream final-schema owner and local qualified-widget registry.

Upstream substantially changes resource queries, UI grouping, VCS ownership. Updated host through `python -m angee.compose.bootstrap`/`uv sync`: aggregates 0.12.0, Hasura 0.10.0, constraints from manifests. Removed old CRM/Inventory attach/make_data_resource_metadata; final executable schema includes native-extension fields itself. Removed Facet labelField: option labels/identity belong to resource query.

Found two shared upstream defects: ResourceQueryProjection must not inspect `_meta` on GenericForeignKey.related_model=None (Rating.target); resourceReadSelectionPaths must not select object-valued lists as scalar leaves (Invoice.payment_schedule in invoices_save generation). Added projection/selection regressions. Tax picker/compact analytics/EditableLines widths retained; no new abstractions/dependencies.

Backed up `.angee/backups/before-upstream-ceb77bf5.sqlite3`. Tested migration → reconcile_permissions → rebac sync → check on `.angee/upstream-migrate-test.sqlite3`, then live. Temporarily deferred premigration system checks per native provision contract because persisted REBAC has old VCS names that identity migrations must first move; full check passes after sync. Accounting schema/entries unchanged. Applied VCS state/identity/package migrations and backend-class choice updates. Did not reload resources/demo.

Preliminary: 422 PostgreSQL ARPEE pass, 116.600 s; consumer frontend 121 passed; typecheck/build pass. Metadata 88, UI 767, App 621 passed. Targeted resource-query 14 passed. Full Python framework still running, no result claimed. Initial App run overlapped pnpm prepare rebuilding metadata/dist; rerun after preparation: 621 passed. Corepack pnpm shim in ignored `.angee/tools` lets upstream prepare find pnpm; package scripts unchanged.

Preliminary browser: Tax Report live/fixture passes; invoices/payments/new/sales/purchase/CRM/calendar/discuss open. Invoice geometry/tax picker at 1280/1920 has no overflow, row height 50px. Restarted via process-compose on 5174/8601. Final audit follows.

## 044 — 2026-09-07 — Upstream update completed and verified

Integrated origin/main **ceb77bf5**, verified ancestor of current framework branch. Commits: Angee merge **e4f43358**, query projection/selection **341f069d**; ARPEE dependency/schema-extension/Facet adaptation **dc45d34**; journal 043 **7983a86d**. Agreed worktrees retained, main checkout not switched, no push.

Backend final: **422 ARPEE PostgreSQL tests OK, 116.600 s**, then **2 native composition tests OK**, including sales lead/delivery_status, Rating generic reference, Invoice payment_schedule/analytic widget. **Full Angee Python: 2017 passed, 9 skipped, 1171.28 s**. Eight skips need PostgreSQL (hierarchy, connection locks, sequence, system queryset, task advisory locks, workflow); one grouping-contract needs absent framework/runtime SDL; host SDL checked separately. Targeted query **14 passed**, including generic reference. Full run began during adaptation; final query/metadata changes also received targeted Python/TypeScript checks. An interim report of one failure misread FEED_SQL_COST diagnostic prefix; final pytest has no failures/errors.

Frontend: **consumer 121 passed**; framework **metadata 88, refine 80, UI 767, App 621** passed. Host/all four package typechecks and production build pass. Backend build/schema/migration/system checks pass. Changed Python Ruff/diffchecks clean. Frozen migrations untouched. Upstream chunk/static-dynamic-import warnings persist without build errors; Python warnings concern pytest plugin rewrite/mailparser_reply deprecation.

Cold SQLite `upstream-cold.sqlite3` provision --demo passed: 437 created / 2 updated; reload **0 created, 0 updated, 439 unchanged**. Fixture/live data separate. All **17 accounting tables** compared row-value-for-row-value to premigration backup: unchanged. No user posting/resaving. Backup `.angee/backups/before-upstream-ceb77bf5.sqlite3` retained.

Browser: fresh admin login; invoices/payment, sales/purchase, CRM pipeline/leads, calendar/discuss/companies, products/pricelists/suppliers, analytic accounts/lines, ratings/inventory transfers. Real server group/facet labels checked; Proposal filters CRM correctly and survives URL/reload. Invoice geometry/tax picker pass 1280/1920. Tax Report, Cash Flow, Partner Ledger/Invoice Analysis, BS/P&L, aging pass live-empty/nonempty-fixture scenarios, CSV/real links/Back. Initial P&L→GL timed out waiting for empty state; unchanged-code diagnostic rerun passes without GraphQL/page/HTTP errors; first timeout cause unknown. Facet-script ellipsis/accessibility/duplicate-heading selectors corrected only in ignored script; final filter confirmed. Artifacts `.angee/browser/upstream-*`.

Confirmed **LISTEN 0.0.0.0:5174 / 0.0.0.0:8601**, user URL **http://192.168.0.90:5174**. Test PostgreSQL stopped. Both branches clean before publication, no unfinished merge. Existing authorized gist updated and compared against local content.

## 045 — 2026-09-07 — Agreed sequence and Analytic Report

User requested autonomous **Analytic Report → bank cycle → multicurrency → Audit Report → fiscal-year closing**, with commits/journal. Budgets/localized declarations excluded. Continue modest-toad / astra/invoice-form-contract, 5174/8601.

Architecture: arp.analytic owns analytic facts/calculation; arp.base owns company/full-report access and exact CSV/Decimal display. Accounting stays a downstream analytic producer; analytics imports neither its models nor frontend. Analogs Invoice Analysis/Tax Report: Pydantic → pydantic_node → authored GraphQL → generated types; shared UI/links/URL. Reviewed docs/stack.md/AGENTS.md; no libraries needed. Moved report_company from accounting to base with existing member/accountant gate and compatible accounting import. Moved report-format to base with re-export.

Local Odoo 19 analytic_account.py:_compute_debit_credit_balance and account_move_line.py:_prepare_analytic_distribution_line: analytic amount = credit − debit, negatives debit, positives credit. These are signed movements, not income/expense GL classification. Do not sum analytic axes as turnover. ARPEE stores one line per axis; require **exactly one plan**, company, inclusive period. Child plans not automatically aggregated because distributions balance by plan_id. Include archived accounts; use saved line plan, not current account.plan, so reclassification does not rewrite old axes. Account names remain current.

One statement reads period rows and derives details/account sums/total, retaining saved MoneyField precision (6 decimal places) rather than rounding allocations to cents. Initially planned rejection of other currencies pending FX; inconsistent analytic-account company rejected. /analytic/report has parameters, accounts/lines, URL account drilldown, account links, full CSV independent of local filters, stale-data hiding. Tests target signs/refunds/bills/boundaries/draft/cancelled/archives/independent axes/reclassification/fractions/malformed data/access/exact CSV. Checks/browser in progress; no final readiness claim yet.

## 046 — 2026-09-07 — Analytic Report implemented and verified

ARPEE **b0959b9**. Final architecture review corrects 045: company.currency belongs to accounting extension; standalone analytic cannot require it. **Currency is an explicit required report parameter**; filter saved lines by plan/company/currency/date, with no implicit conversion/mixed totals. Shared arp.base report_company handles authorization/period/refresh only; accounting wrapper separately requires GL currency. UI states currency/no conversion. This replaces 045's preliminary rejection of all other currencies.

Checks: **32 SQLite tests OK**, 6 new analytic plus GL/TB/analytic; consumer frontend **123 passed** (analytic 18/accounting 31/others). Typecheck/build/codegen/composer/schema/migration checks pass; no migrations. Corrected GraphQLSchemas import and permission fixture scope: exit setup system_context before real actors. Final checks deny outsider/company viewer, allow member; not weakened.

Browser live company/plan/currency/period, empty report/reload. Report-query-only fixture checks exact fractions, accounts/lines, URL drilldown/reload, whole-report CSV from account detail, real analytic-account link/Back; no overflow/GraphQL/HTTP/page errors. Initial run hit backend restart readiness gap; rerun after readiness passed. Artifacts ignored .angee/browser/analytic-report-*. No user posting. URL **http://192.168.0.90:5174/analytic/report**. Next bank cycle.

## 047 — 2026-09-07 — Bank-cycle contract and implementation

Odoo references: account_bank_statement.py (balances/continuity), account_bank_statement_line.py (cash/suspense), account_journal.py (suspense/outstanding), account_payment.py (outstanding payments). arp.accounting owns Journal account selection, BankStatementManager import, BankStatementLine matching/categorization; existing JournalEntry.post owns entries/period locks, JournalItemManager.reconcile the graph. Analogs PaymentManager.register/InvoiceWorkbench. stdlib csv, Pydantic input, ResourceList/RowsListView/ActionFormDialog; no new dependencies/framework components.

Journal adds optional suspense_account/outstanding_receipts_account/outstanding_payments_account. Outstanding must be distinct, reconcilable, noncash/nontrade, same company; configured payments use it instead of cash. Unconfigured journals retain direct cash; history unchanged. Enabling statements for an existing journal requires agreed opening/date to avoid reimporting manually recorded cash. New immutable BankStatement/BankStatementLine evidence; each import line creates cash↔suspense. Matching does not edit saved documents: separate BNM closes suspense/open debt/outstanding, linked by existing reconciliation. BNK/BNM use created public IDs, not invoice/payment sequences.

CSV exactly transaction_id,date,label,amount; ISO dates/signed Decimal and bank-provided IDs required, so legitimate identical amount/date payments are not deduplicated. Same reference/canonical content returns existing statement. Changed same-reference content, duplicate IDs within/across statements, overlapping periods, inconsistent adjacent balances, invalid precision/range/dates, or opening+movements≠closing fail atomically. Imports serialize by journal; DB uniqueness backs identity. First opening is bank evidence, not an automatic opening entry; UI shows closing minus actual cash GL balance.

Matching selects open items of one account/currency/partner/company, settling bank amount plus explicit positive fee, including partials. -103 outflow with fee 3 settles -100; 97 inflow with fee 3 settles 100. Fee posts to selected expense account. Categorize handles standalone expense/interest directly without fictitious invoices. Match date cannot precede bank/source dates. Account-before-item locks and refreshed residual prevent repeated/concurrent matching.

Typed import/match/categorize APIs and bank_match_view use correlated subqueries, avoiding multiplied partial joins. Bank Statements / Bank Transactions / Bank Match expose CSV import, read-only source evidence, balances, open-document selection, fees, direct expense/income categorization. Native hideCreate hides New; authored importer owns creation. Member reads, accountant imports/matches, outsider denied. REBAC revision 4.

Frozen bank_statements/bank_evidence_guards migrations; second declaration guarantees SQLite/PostgreSQL immutable UPDATE/DELETE guards on fresh initial schemas where composer already created models. Formatted before materialization. Backup .angee/backups/before-bank-cycle.sqlite3; migration/permission sync tested on .angee/bank-migration-test.sqlite3, then live. No live posting. Preliminary 12 SQLite tests OK, one PostgreSQL concurrency skip; typecheck passes. Full PostgreSQL/final browser in progress.

## 048 — 2026-09-07 — Bank cycle verified and committed

Full **441 PostgreSQL tests OK, 108.873 s**, bank/analytic plus prior accounting/sales/purchase/product/CRM/inventory. After historical cash-account balance_difference fix, **12 targeted PostgreSQL bank tests OK, 2.906 s**. Initial targeted test found values_list/filter added a JOIN including both entry legs; fixed filter→values_list at calculation owner. Concurrent matching yields one success, one domain rejection, one BNM.

Consumer frontend **123 passed**, typecheck/build pass. Manifest test adds two resources, preserving unique route-owner assertion. Composer/schema/migration checks pass; frozen sources unchanged. Browser real empty lists/import dialog; BankMatchView/MatchBankTransaction-only fixture checks open amounts, selection, typed mutation, invalidation/matched state/reload/no reselection/overflow/errors. Actual bank GL/CSV proven by API/model tests, not live browser import. Autoreload-overlapping run saw 502; readiness /auth/csrf/200 rerun passed. Artifacts .angee/browser/banking-*.

Existing Cash Flow still explicitly shows unclassified suspense where no category is configured. Automatic attribution through multiple clearing accounts is not added or claimed as an Enterprise-handler port. Invoice.payment_status retains trade-debt settlement semantics; bank confirmation is separately visible as matched. This stage imports in company currency; FX next.

Bank-cycle ARPEE commit: **f331e07**.

## 049 — 2026-09-07 — Multicurrency contract

angee.money.Currency/CurrencyRate owns rates; accounting snapshots the effective posting-date rate. JournalEntry.currency is document currency; ledger_currency is historical GL currency. JournalItem.debit/credit always use company currency; transaction_currency/amount_currency retain signed original units. GL/TB/BS/P&L continue summing homogeneous ledger amounts. Invoice retains original tax_snapshot and separate company_tax_snapshot built from actual posted tax legs; rate-catalog changes do not rewrite history.

Reconciliation stores base amount plus each endpoint's original amount. Settling foreign residual creates a realized gain/loss entry using explicitly configured accounts/company general journal. Unreconcile reverses these with reversal_of retained. Bank journals gain optional fixed currency; statements stay in bank units and convert movements at transaction date. Matching uses the bank fact's original rate so manual reconciliation date cannot alter cash movement.

Accounting models/managers own rules/locks; typed APIs delegate; native ResourceList/Form/ActionFormDialog owns UI. Company uses accounting-owned extension/configuration command, without accounting vocabulary in arp.base. React formats Decimal strings, including schedules. Automatic unrealized valuation is not claimed; it needs a separate dated policy operation.

## 050 — 2026-09-07 — Multicurrency implemented

ARPEE **c15c7e0**. Foreign posting retains original/company amounts and rate. Taxes/Invoice Analysis use company facts; schedules use original units. Journal.currency sets bank units; import/matching preserve bank amounts/historical rate. Realized differences use configured gain/loss accounts; unreconcile creates reversal, rematching a new difference. Migrations backfill old identity-currency entries without recalculating documents. Changing currency on an existing statement chain is rejected. API/Exchange Settings exposed in UI.

Checks: 36 SQLite tests OK, 3 PG-only skips. A 148-test PostgreSQL regression exposed one invalid foreign draft incorrectly normalized by conversion; added draft item/document-unit equality check. Targeted rerun **26 PostgreSQL tests OK**, 10 new FX + 16 ledger. **123 frontend tests OK**; typecheck/build/schema/codegen/migration check pass. Browser real four-relation configuration form, companies, Customer Invoices without errors; .angee/browser/fx.log, fx-settings.png. Migrations tested on copy, then live SQLite; backup before-fx.sqlite3. Full PostgreSQL regression planned after final audit/closing.

## 051 — 2026-09-07 — Audit Report and year-closing contract

Odoo sources: account/models/company.py global fiscalyear_lock_date, separate irreversible hard_lock_date/restricted audit trail; account_move.py period/posted protections; report/account_hash_integrity_templates.py hash-check presentation. Implement verifiable GL facts and closing-control snapshots. Snapshot SHA-256 is not an electronic signature, external notarization, or full Odoo hash chain.

Audit Report shows period documents/findings: balance/leg count, company/currency consistency, numbers, FX provenance, tax evidence, drafts, pending bank movements. Year close checks the entire ledger through closing date, separately computes the chosen full fiscal year's result, saves append-only snapshot/digest, and advances existing PeriodLock atomically under company lock. Both errors and warnings block closure. AR/AP need no fictitious settlement. No automatic opening/zeroing entries: Balance Sheet already carries balance accounts/prior unallocated earnings; P&L is period-bound. Administrative reopening stays with historical PeriodLock; review creates a new revision without deleting old ones.

## 052 — 2026-09-07 — Audit Report / Financial Year Closing complete; full regression

ARPEE **1b4fd68**. Read-only Audit Report uses shared company authorization, typed GraphQL, native RowsListView, findings/documents, URL sections/parameters, document links, full CSV. Posted totals are company-currency; drafts are not labeled as ledger units. Deterministic posted-header/item SHA-256 supports saved-closing comparison. Mutable catalog names/reconciliation state do not replace historical facts. Local control snapshot only, not Odoo hash chain/legal certification.

FiscalYearClosure saves company/currency/full-year range/posted count/debit/credit/year result/digest/reviewer reason/audit attributes. Append-only including bulk ORM and PostgreSQL/SQLite UPDATE/DELETE guards. Shared AccountingEvidenceMixin/QuerySet now serves bank/year evidence. company/accounting administrators close; accountant/reader denied, outsider cannot report. REBAC revision 5. Concurrent closes serialize company lock and return one snapshot; PeriodLock update is in the same transaction. Policy-write failure rolls back snapshot. Differently bounded overlapping years rejected; identical reviewed close idempotent; reopening/review adds a revision and retains prior evidence.

Late FX **7f7d934**: missing reference rates produce clear domain errors; validate each source reference-relative rate through CurrencyRate.rate_for so two negatives cannot yield an accepted positive cross-rate. Effective factor still saved on entry. Fixed foreign taxes retain original rate currency in Tax Report/group key/CSV, while base/amount are company units. Verified 12 USD fixed tax → 10 EUR ledger tax, rate explicitly USD.

Validation:

- Audit/Closing: 9 SQLite tests OK; PostgreSQL concurrency in full suite. fiscal_year_closure/fiscal_year_guards first tested on .angee/closing-migration-test.sqlite3, then live; backup .angee/backups/before-year-close.sqlite3. Formatted before materialization, never rewritten.
- Full **463 PostgreSQL tests OK, 116.317 s**, accounting/reports/FX/banking/analytic/locks/concurrency/prior suites. Previous 462-test run found missing concurrency-test import; fixed, full rerun passed. Final negative-rate addition: **13 FX PostgreSQL tests OK, 1.201 s**.
- **123 frontend tests OK**, typecheck/build pass. Final audit-label changes rechecked by typecheck/build/browser. Composer/schema/migration/Ruff/diff checks pass.
- Browser real findings, Entries/reload/URL/full CSV, read-only closures/close form. Viewed screenshots: generic debit/credit labels corrected from Tax Debit/Credit, explicit dates, readable draft links, four total cards without a lone fifth. Artifacts .angee/browser/audit-closing-final.log, audit-findings.png, audit-entries.png, year-closing-form.png, audit-report.csv. Early runs overlapped autoreload, expected the wrong draft count (Customer Invoices excludes vendor bills), or abbreviated CSV button; ready-service rerun verifies real 4 drafts and exact Export full CSV.
- No live years closed or documents posted. Real Audit: 0 errors, 4 draft findings, 0 posted entries. HTTP 200 through http://192.168.0.90:5174; backend/frontend 0.0.0.0:8601/5174.

Five agreed stages implemented at current baseline scope: Analytic **b0959b9**, bank cycle **f331e07**, multicurrency/realized FX **c15c7e0 + 7f7d934**, Audit/year close **1b4fd68**. Git branches not published; local intermediate commits and gist retained.

Limits: no automatic unrealized valuation; pre-close valuation follows company policy. Bank import is normalized CSV, no feeds; Cash Flow does not claim arbitrary clearing-chain attribution. Closing uses reversible administrative PeriodLock, not Odoo irreversible hard lock. Local declarations/legal certification/hash chain/automatic selected-equity profit allocation remain separate; reports carry balances/unallocated result without duplicate opening entries.

## 053 — 2026-09-07 — Next: unrealized valuation and hard lock

User “go” continues the two explicitly remaining tasks. Owners: CurrencyRate dated rates; JournalItem/account/currency grouping dated exposure; new FxRevaluation manager preview fingerprint/atomic adjustment/reversal; PeriodLock soft/hard boundaries; PostgreSQL/SQLite triggers irreversibility/posting serialization. Native UI/typed GraphQL, no new table/form engine. Analogs BankPages, AuditReportPage, FiscalYearClosure, immutable evidence migrations. Financial values Decimal/exact React strings.

Odoo company.py _validate_locks prohibits reducing/removing hard_lock_date and checks pending entries; https://www.odoo.com/documentation/19.0/applications/finance/accounting/bank/foreign_currency.html describes unrealized gains/losses and adjustment entries. Enterprise handler absent locally; implement business contract, not a claimed literal port.

Valuation: monetary balance-sheet AR/AP/cash and explicitly selected reconcilable current assets/liabilities, grouped by original currency; no income/expense/equity valuation. Dated ledger facts, not today's residual. Adjustment changes company amounts on original account; next-day reversal created atomically. Realized settlement still uses original debt. Cash Flow separately exposes exchange effect. Repreview includes earlier adjustments, stale previews fail, rate edits never rewrite posted facts.

Hard lock: explicit confirmation by company/accounting admin, not editable through generic PeriodLock. Code/DB reject reducing/clearing dates, including raw SQL. Live demo is not automatically locked; capability tested on test companies.

## 054 — 2026-09-07 — Revaluation implemented and verified

FxRevaluation is append-only preview/entry/reversal evidence. No mutable JournalEntry flag; protected one-to-one evidence links establish membership. Group dated account/currency facts; automatic AR/AP/cash scope, others explicit. Rate/booked/adjusted/valued/difference enter fingerprint. Posting locks account-before-company; repeated fingerprint idempotent, stale preview denied. Both entries posted atomically; next-day reversal and pair reconciliation do not touch original debt. Manual re-reversal/removal of automatic pair matching denied; new valuation posts only remaining difference. Cash Flow adds exchange: closing = opening + net cash flows + exchange.

61 PostgreSQL tests OK, 11.660 s, including 9 new valuation cases plus FX/reconciliation/closing/Cash Flow. SQLite 37-test run found only the expected need to add exchange to old full-totals assertions; updated contract verified PostgreSQL. 123 frontend tests, typecheck/build/composer/migration checks pass; CSV assertions add exchange control. Browser real empty report/history; typed-query/mutation fixture checks USD120/EUR100/adjustment20 review, fingerprint/reason submission, invalidation, adjusted20/difference0, reload, disabled repeat. .angee/browser/revaluation2.log, revaluation-review.png, revaluation-adjusted.png. Ruff/autoreload-overlapping run repeated after HTTP200. Migrations 0020/0021 tested on copy/applied SQLite; backup before-revaluation.sqlite3. No user posting.

## 055 — 2026-09-07 — Hard lock, bank currency, final verification

Consumer **cee2101**: unrealized valuation; **3b471fb**: permanent locks/correct bank-balance currency. Saved in modest-toad; framework astra/invoice-form-contract.

PeriodLock has independent soft lock_date/hard_lock_date; later boundary applies. Hard date cannot be deleted/reduced/bypassed by policy deletion or company transfer. hard_lock_period requires company/accounting admin, reason, explicit confirmed=true; runs Audit from inception through selected date before setting/extending. Errors/warnings block it. Same boundary idempotent. Ordinary CRUD excludes hard_lock_date. Configuration → Period Locks → Set permanent lock uses native ActionFormDialog, confirmation initially off, date read-only.

Models/PostgreSQL/SQLite triggers reject closed-period JournalEntry/Payment posting INSERT/UPDATE and enforce monotonic policy. Company locks serialize posting/closing. Rechecking drafts/payments in DB catches drafts created after review; closure rolls back. Corrections use reversal in a later open period. Frozen 0022–0024 tested on .angee/hard-lock-migration-test.sqlite3 then applied live; backup .angee/backups/before-hard-lock.sqlite3.

Additional FX correction: invoice currency does not determine bank cash currency. EUR bank/cash paying USD records cash amount_currency in EUR, retains USD debt; fixed-USD bank keeps USD. Inconsistent third bank currency rejected. Prevents false USD exposure/revaluation of converted funds. No historical rewrite. Valuation uses existing gain/loss settings; other monetary balance-sheet scope explicit.

Checks:

- **485 PostgreSQL tests OK, 116.012 s**, full consumer/report/FX/bank/reconciliation/locks/valuation/concurrency. .angee/valuation-hard-lock-full-pg.log. Two concurrent identical previews yield one evidence record/entry pair.
- **29 SQLite tests OK**, 2 PostgreSQL-only skips, hard/soft locks/audit closing. Preliminary PostgreSQL assertion expected too-specific raw INSERT text; existing posted-INSERT guard precedes hard-lock trigger. Corrected expectation; prohibition retained and full rerun confirms it.
- **123 frontend tests OK**; typecheck/build/Ruff/composer/schema/migration/diff checks pass.
- Browser real Period Locks, permanent-lock form/confirmation, Saved valuations navigation; no JS/HTTP/GraphQL errors. .angee/browser/hard-lock.log, hard-lock-form.png. Viewed hard-lock/revaluation-review/revaluation-adjusted screenshots without overlap. Typed valuation fixtures documented in 054.

No real company documents posted; no live hard lock set. Stack modest-toad, 0.0.0.0:5174/8601. These two previously deferred tasks are complete; 052's no-unrealized-valuation/no-hard-lock limits no longer apply. External feeds/local declarations/automatic equity allocation remain outside scope.

## 056 — 2026-09-08 — Analytic Report and agreed Sale Order rules

User explicitly requested parallel Analytic Report/Sales fixes. Independent report, sales ORM, CRM tasks; root handled sales API/UI/integration/browser/journal. Owners: SalesOrderLine.product_defaults description/UOM/price; SalesOrder payment terms/accepted-term immutability; pricelist.price_for pricing; Django/triggers persistence guarantees; RHF/Form/EditableLines/registry form/row updates; JournalItem.source_sale_line invoice list. UI analogs PurchaseOrdersPage, InvoiceWorkbench, AnalyticDistribution, ActionFormDialog/RowsListView. No libraries added.

**Analytic Report, 1dc038f.** Existing report's account drilldown improved: totals/CSV now reflect selected account with scope label; All lines restores plan. Unknown account does not fall back to global totals, export disabled. URL retains scope on reload. Backend/API unchanged. Checks: 20 SQLite, 18 analytic frontend, host typecheck; browser live-empty/parameter form plus typed scope/CSV/reload fixtures. .angee/browser/analytic-report-scoped.log/png/csv.

**Sale Order, 082ba90.** Product selection requests server preview and atomically replaces product/label/UOM/price. Description uses template.description or template.name, preserving label256 limit. UOM read-only; new/replaced product uses template.uom, independent model UOM changes rejected. New line quantity1/discount0; replacement preserves existing quantity/discount but updates label/price. Price uses selected pricelist, otherwise effective product.list_price. Model distinguishes omitted price from explicit0: imports/programmatic creation retain explicit quantity/price/label, including free lines; UI selection gets defaults.

Payment Term required on creation/commercial-field saves/confirmation and must belong to order company. Storage remains nullable for legacy; migration invents no term. Both existing confirmed live orders already had terms. After confirm/cancel, models/triggers protect company/customer/date/expires/currency/payment_term/pricelist/salesperson/number, commercial line fields, line add/delete/reparent, taxes. Operational invoiced/delivered quantities remain writable. Invoice/delivery bridges lock order before lines, avoiding reversed concurrent lock order. Explicit legacy fixtures preserve alternate-UOM history tests.

**Opening invoices.** Sales → Orders → order → Invoices lists actor-visible invoices through source_sale_line, no duplicate M2M. Number/Draft invoice opens document; dates explicit. Create Invoice returns id for one created invoice; standard ActionResult opens it automatically. Batch/exhausted repeat only reports result. SalesOrderType.company now projects CompanyType node (id/name/display) for native read-only relation rendering; clients select company { id ... }, writes still take public ID. Schema/codegen updated.

**CRM, e5edc11.** Convert to Quotation asks Payment Term in native ActionFormDialog and delegates to model. Existing quotation returned idempotently; new requires explicit accessible company term. UI paymentTerm follows normalized ActionResult validation keys. No invented defaults.

**Framework, b1ded91f; extra regressions 56aef787.** Form.readOnlyWhen evaluates persisted state and blocks fields/lines/save/applyPatch while retaining lifecycle actions. EditableLines passes live parentRow/optional onRowChange; RHF key protects late responses after reorder/delete/unmount/lock. Metadata/registry accept namespaced relation widgets while preserving ID/filter semantics. Browser found semantic no-op: different label shape for the same relation ID left RHF dirty after save. Baseline now accepts those rows while retaining later user edits.

sales002/003 tested on .angee/sales-contract-migration-test.sqlite3, applied to main database; backup .angee/backups/before-sales-contract.sqlite3. Drift found simple-history expects blankTrue for historical payment_term; added separate frozen004 order_history_contract, without rewriting applied sources. After004: No changes detected.

Final checks:

- **500 PostgreSQL consumer tests OK, 120.580s**, accounting/sales/CRM/inventory/others. After final schema/history: **121 PostgreSQL tests OK, 29.268s**, including crossbridge concurrency; 5 SQLite API/composition OK.
- **123 consumer frontend OK**, host typecheck/build; **773 framework UI OK**, UI typecheck, **51 metadata backend OK**, Ruff/diffcheck.
- Live browser: replacement→label/price/UOM→Save/reload; new quantity1/discount0/price149→Save/reload; confirmed read-only; Invoices→real invoice; CRM required term/disabled empty submit. .angee/browser/sales-new-contract.log, sales-links-final.log, sales-product-change.png, sales-confirmed.png, sales-invoices.png, crm-payment-term.png. Screenshots viewed.
- Separate semantic no-op Save: .angee/browser/sales-dirty-fixed-final.log/png. Vite retained old linked prebundle after source edits; cleared generated optimizer cache/restarted web via process-compose. Acceptance scripts corrected LAMP-01/capitalized Payment Term/Playwright API expectations; mismatches were not treated as product defects.
- Two temporary browser drafts deleted; user confirmed orders/financial documents unchanged by acceptance. Stack modest-toad, frontend0.0.0.0:5174 / backend0.0.0.0:8601.

## 057 — 2026-09-08 — main-astra branch and PR

At explicit user instruction, created/published litnimax/arpee-angee main-astra from current origin/main, SHA fa5c444125595e82260d45e2e53d4c7994ed3ce5. modest-toad at 082ba908c4106de4c536be4502e64f9475fe56de already matched origin. No force push/current-branch switch.

Opened PR **#2**, modest-toad → main-astra: https://github.com/litnimax/arpee-angee/pull/2 . Includes all 31 accounting/sales iteration commits. English description records final scope, prior checks, migrations, limits, separate angee-django astra/invoice-form-contract dependency cd2bdf37. Framework branch not included. GitHub API verified base/head/isDraft=false. No code changes/additional tests for publication.

## 058 — 2026-09-08 — Sale Order lines before first save

**Problem.** New Sale Order could not add lines until saved. Cause: `!isCreate` in shared `useFormViewSave.linesActive`; backend already supported atomic nested inserts. Previous browser testing began with a saved draft, missing `/sales/new`.

**Owners/solution.** Form/EditableLines/RHF own draft; Refine Hasura provider native create; HasuraLines/AngeeHasuraWriteBackend envelope/transaction; SalesOrderLine defaults/calculation. Fixed framework UI, no separate sales editor or sequential parent/child saves. Create editor enabled with create root/custom submit. Native create gets `object.lines.data` from diffLines; returning selection includes lines/IDs. Remote-line conflict checks apply only to existing documents. Successful creation's dirty-state change no longer replays the empty initial draft over saved lines. Custom submit retains standard lines-diff context.

**Commits.** Framework `c2051e7d`: fix/3 UI regressions (Add line/first create, native nested insert IDs/baseline, draft retention after failure). Consumer `b19341b`: two GraphQL integrations, order+line success and complete rollback for invalid second-line discount. No models/ORM/migrations changed. Consumer published to modest-toad/PR #2; companion dependency updated in PR.

**Checks.** 776 UI, 88 metadata, 80 Refine, 3 e2e-package unit tests pass; framework UI/app typecheck/UI build pass. 123 consumer frontend, host typecheck, Ruff/diffcheck pass. Two SQLite GraphQL integrations verify success/VALIDATION/full rollback. Added actor_context/real company salesperson/direct_member grants: initial UNAUTHENTICATED/PERMISSION_DENIED were fixture errors, not passed validation tests.

Full framework `pnpm -r test` is not entirely green: 7 preexisting @angee/app ResourceList tests cannot find record fields; 45 others in that file pass. Same seven reproduced in isolated unchanged **bf5c68da**; temporary checkout removed. Logs `.angee/create-lines-app-targeted.log`, `create-lines-app-baseline.log`. Full `pnpm -r typecheck` also stopped on unchanged integrate_vcs `@angee/gql/console` and `/actions` imports missing in standalone framework; composed consumer passes. These are not described as successful full runs.

**Browser.** Live modest-toad `/sales/new`: Add line before any mutation → company/customer/currency/payment term/date → LAMP-01 → “Adjustable LED desk lamp.”, quantity 1, price 24.900000, discount 0, read-only UOM → Create. Exactly one `insert_sales_orders_one` with nested lines; after navigation/reload, line/description/price persist. `.angee/browser/sales-create-lines.log`, `sales-create-lines-result.json`; screenshots `sales-create-lines-before-save.png`, `sales-create-lines-saved.png`, first viewed. Existing confirmed read-only/invoice navigation/CRM term rechecked. Only test draft `sor_OIJLhNcS` deleted, `.angee/browser/create-lines-cleanup.log`.

Moved generated Vite cache into local scratch and restarted web through process-compose to load linked changes. Rechecked create surface after final restart. Frontend :5174/backend :8601 return HTTP 200; stack remains modest-toad.


## 059 — 2026-09-08 — English repository documentation; Russian gist retained

The user requested translation of all Russian repository text, then explicitly clarified that the external gist must remain in Russian and continue in Russian. Scanned tracked text in arpee-angee/modest-toad and the linked angee-django/astra/invoice-form-contract. Found three Russian documents: local development instructions, the original Odoo analysis, and the implementation journal. Translated them into English and renamed them to accounting-dev.md, accounting-odoo19-analysis.md, and accounting-implementation-log.md. Updated local document references and the PR's development-guide reference. The original analysis gist remains Russian as well.

All 58 preceding journal entries, their dates, commit hashes, evidence links, decisions, checks, failures, and historical limitations are retained. The original analysis remains a dated historical analysis, not a new implementation-status assessment. The only remaining Cyrillic in tracked sources is five native currency-symbol values in the ISO currency catalog; these are identifiers/display symbols, not Russian prose, and remain unchanged. Concurrent invoice/product/action-form edits are outside these documentation commits.

Verification is documentation-specific: complete numbered-entry inventory, commit-hash and URL preservation, Cyrillic scan, renamed-reference checks, balanced Markdown code fences, and git diff --check. No application tests were rerun for translated prose. The Russian gist is updated separately under its existing filename accounting-implementation-log.ru.md, preserving earlier Russian entries; it must not be synchronized from this English file.
