# Accounting arpee → Angee: analysis using the Odoo 19 ontology

Research date: 2026-09-05. Status: source analysis and implementation design; no functional changes have been made.

## 1. Conclusion

Arpee already implements an initial accounting system, beyond invoice CRUD: a common journal entry, its items, the Invoice specialization, taxes, payments, partial reconciliation, numbering, and analytic entries. Development should build on this system, preserving Odoo's domain relationships while using native Django/Angee mechanisms.

Balanced debits and credits alone do not establish accounting correctness. Current risks include an incorrect repeat-payment amount, reversed refund directions, incomplete reconciliation-graph processing, and incorrect extraction of multiple included taxes. These take priority over adding screens.

Odoo is the source of business concepts, invariants, and scenarios here. This does not propose using Odoo as the runtime, reproducing its ORM, or porting all its capabilities in one change.

## 2. Scope and evidence

| Source | Snapshot | Role |
|---|---|---|
| `/workspace/arpee-angee` | `fa5c444125595e82260d45e2e53d4c7994ed3ce5` | Current consumer addon `addons/arp/accounting` |
| `/home/paseo/.paseo/worktrees/1s29tjir/exotic-pony` | `64f1d1750f7a9f5afbefc3ce3196fa190ee44280` | Target angee-django: shared mechanisms and standard addons |
| `/workspace/odoo_19` | `1a13ceeaee12fe5cc50f287c31f217d4be2a2eaf` | Local Odoo 19 reference |

The working trees were clean when research began. Paths below are relative to their respective repositories. Line numbers refer to these snapshots.

The review covered accounting models, business methods, GraphQL, permissions, resources, tests, and main UI declarations; sales/purchase integration points; Angee's money, sequence, transitions, and GraphQL-write owners; and Odoo's account core and related models. This is static research, not a production-data audit or proof of full Odoo parity. Existing Django/PostgreSQL and browser tests were not run: a composed runtime with a verified connection between these two checkouts was not started during the analysis.

An isolated calculation using arpee's actual `PercentTaxCompute` was also performed; section 5 records the result. It does not substitute for a posting integration test.

This Odoo checkout contains `account.report` and its declarative models but no `addons/account_reports` directory. Report declarations therefore do not establish availability of the complete Enterprise dynamic reporting engine. Bank integrations and localizations likewise require checking specific addons, not relying on the general Accounting name.

## 3. Business ontology

| Concept and relationship | Odoo 19 | Current arpee | Development decision |
|---|---|---|---|
| A company owns a ledger and currency | `res.company` | `arp.Company` + `CompanyAccounting` | Preserve the owner; add accounting policy and period closing |
| A partner participates in an obligation | `res.partner` | `parties.Party` | Extend the existing Party, including company-specific account settings |
| An account classifies a movement | `account.account` | `Account`, 9 kinds, company/code uniqueness | Extend classification for reporting; reject invalid accounts at posting |
| A journal defines a book of transactions | `account.journal` | `Journal`, 5 kinds | Validate purpose, company, accounts, and sequences |
| An entry contains items | `account.move` → `account.move.line` | `JournalEntry` → `JournalItem` | Keep one ledger as the source of accounting amounts |
| An Invoice specializes an entry | `move_type` | Materialized child `Invoice` | Preserve the native Angee child; do not add an independent second accounting record |
| Debt has an amount and maturity | Receivable/payable items with `date_maturity` | One counterpart item; document `due_date` | Materialize payment schedules as separate debt items |
| Settlement links opposite debts | `account.partial.reconcile` | `PartialReconcile` | Settlement amount and residual are graph facts, not manual invoice status |
| Full reconciliation closes a graph component | `account.full.reconcile` | `FullReconcile`, current settled items only | Process all connected items and partials |
| A payment records money received/sent | `account.payment`, separate payment_type and partner_type | `Payment.direction`, bank/counterpart entry | Separate money direction from partner type |
| A statement confirms a bank movement | Statement / statement line | No models | Introduce a separate object and bank-reconciliation workflow |
| Tax transforms a base and creates accounting effects | Tax + repartition + tags + fiscal position | Percent/fixed, invoice/refund distributions | Share a base/tax/distribution calculation result, then materialize GL items |
| Analytics allocates economic results | `analytic` + account bridges | `arp.analytic`, distribution on item | Preserve the separate addon and source-item relationship |
| A report projects entries at a date | Report/line/expression/column | No accounting reports | Start with verifiable GL, movements, aging, BS/P&L |

Typical flow: document → validation → posting → income/expense, tax, and debt items → payment → partial reconciliation → residual → bank confirmation → report at a selected date. Refunds and corrections create linked reverse documents; period closing restricts changes.

Odoo payment terms create a separate journal item for each maturity date, which matters for aging and partial payment: [official payment-terms documentation](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/payment_terms.html).

An Odoo 19 detail: payments need not create entries. This depends on outstanding-account configuration; payment registration and bank confirmation are different events. Arpee's current always-direct-to-bank design cannot be described as full Odoo parity. See [Payments](https://www.odoo.com/documentation/19.0/applications/finance/accounting/payments.html) and [Journals](https://www.odoo.com/documentation/19.0/applications/finance/accounting/get_started/journals.html).

## 4. Existing foundations to preserve

- `JournalEntry.post()` centralizes materialization, balancing, analytics, and numbering; Invoice overrides domain hooks. Source: `addons/arp/accounting/models.py:695,958`.
- Money uses `MoneyField`, currency, and rounding from `angee.money`; numbering uses `angee.sequence`. The target Angee already has rates/conversion, but arpee posting deliberately rejects foreign currency (`models.py:760`).
- `StateTransitions` and `save_state` already exist. In the target Angee, `save_state` rechecks persisted state under a lock; saying there is no repeat-transition protection would be incorrect. Atomicity of the whole operation remains the calling business method/transaction's responsibility.
- Reconciliation locks selected items by PK and calculates residuals after locking (`models.py:1131`). Extend this foundation to correctly process connected components.
- Analytics is a separate addon. Sales/purchase create documents through `InvoiceManager.create_document` and add their relationships through extensions; accounting does not import sales/purchase.
- UI uses shared List/Form/Record primitives. Invoice, bill, payment, entry, and configuration pages exist. GraphQL GL resources are currently read-only; this API has no complete manual-entry workflow (`schema.py:432`).
- Tests already cover basic posting, ordinary posted-item edit rejection, foreign-currency rejection, reversal, refund distributions, rounding, read isolation, and concurrent numbering. This is a useful foundation, not full settlement-lifecycle coverage.

## 5. Defects and risks with concrete scenarios

P0 items must be fixed before this system is used as a reliable ledger. “Confirmed from code” means a directly observable rule or missing branch; whether a particular bypass is accessible through the composed API still requires runtime verification.

| Priority | Finding and consequence | Evidence / acceptance scenario |
|---|---|---|
| P0 | Default payment uses original totals rather than current residuals | `PaymentManager.register`, `models.py:1501–1503`. Invoice 100, paid 40: a second payment without amount must be 60; it currently calculates 100 |
| P0 | Customer refunds are treated as inbound; vendor refunds as outbound | `inbound = first.kind in _RECEIVABLE_KINDS`, `models.py:1502`; the set includes customer refunds. `_build_entry:1617` also infers counterpart from direction. customer/vendor and receive/send must be independent axes |
| P0 | Payment-group validation is incomplete | `schema.py:624`, `models.py:1481`. Empty input reaches `invoices[0]`; no explicit split/rejection handles different companies, currencies, partners, or document semantics. Access to two companies does not permit mixing their accounting |
| P0 | A missing bank account falls back to receivable | `models.py:1625`. A payment can produce D receivable / C receivable instead of cash movement. Missing valid configuration must block posting |
| P0 | Full reconciliation misses historically connected items | `_stamp_full_reconciles`, `models.py:1215`. For invoice 100 and payments 40+60, the final call sees the invoice and payment 60 but not payment 40. Close one complete connected component, not just stamp the current subset |
| P0 | Unreconcile recalculates only supplied items | `models.py:1173`. Deleting a partial through the payment item also changes invoice residual, but the invoice may retain `paid`; omitted items may retain stale `reconciled` after FullReconcile deletion. Lock and recompute affected endpoints/components |
| P0 | Posted-ledger protection does not cover all write paths | `JournalItem.save:1377` protects existing items on save. Models lack domain delete guards and posted header/Payment edit guards; Invoice/Payment write backends do not set `delete_guard` (`schema.py:481,507`). Item `entry` is CASCADE. The domain-guard gap is confirmed; test API delete/update, M2M, nested writes, and bulk operations with real permissions |
| P0 | Posting validation is not proven sufficient: balance permits an empty set | `assert_balanced:747` only compares sums. It does not require items, accounts, a partner, or journal/account/tax/company consistency. `account` is nullable; zero-zero is checked in `clean` only when the parent is already posted. Validate the whole aggregate before transition, including internal system writes |
| P1 | Multiple included taxes are extracted incorrectly | `Invoice._materialize_document_lines:983`, `tax.py`. Gross 120 with two independent included 10% taxes on one base produces net 99.17 and total 119.01 instead of 100 and 120. Reproduced in isolation with Python 3 using current `PercentTaxCompute` |
| P1 | Payment terms do not create a debt schedule | `PaymentTerm.compute_due:492`, `Invoice._materialize_counterpart:1075`. Only the latest schedule date is retained; items lack `date_maturity`. Invoice 1000 with 30/70 terms should create debts 300 and 700 on different dates |
| P1 | Tax distributions do not validate the expected structure | `_materialize_tax_group:1025` puts the remainder in the first distribution; missing distributions use the journal's default account. A remainder must not conceal invalid factor totals. Define base/tax lines, tax tags, and allowed factors explicitly |
| P1 | Sequences do not establish document-number integrity | `JournalEntry.number:634` has no uniqueness constraint; `post(number=...)` permits explicit numbers. Domain uniqueness needs an agreed scope and assigned-number immutability; Payment and its entry intentionally share a number |
| P1 | Reopen does not clean up dependent accounting facts | `reopen:724` is empty; `_generate_analytic_lines:780` recreates rows. Enabling the policy risks duplicate analytics, reconciliation problems, and a new number on repost. Reopen is disabled by default; enable only after implementing the full protocol |

Separately verify Invoice creation through generic GraphQL: required `JournalEntry.date` is absent from Invoice writable fields, while create_document and demo factories pass it explicitly. Confirm the actual runtime defaulting chain; the API declaration does not make it clear.

Reconciliation currently checks one account, one currency, and posted status. It does not establish complete payment-group semantics. The fix belongs in the model/manager so API, jobs, imports, and internal calls share behavior.

## 6. Missing capabilities relative to Odoo's domain model

| Area | Required capabilities |
|---|---|
| Ledger integrity | Complete posting/edit/delete guards; period closing; correct reversal/repost; immutable source-fact references |
| Receivables/payables | Document/item residual, installment maturities, advances, overpayment, refunds, write-offs, correct unreconcile |
| Banking | Partner bank accounts, payment methods, outstanding/suspense, statement lines, deduplicated import, matching, fees |
| Taxes | Shared/changing-base taxes, groups, fiscal position, tax/base repartition, reporting tags, cash basis and cash rounding where required |
| Currencies | Company-currency debit/credit plus signed transaction-currency amount_currency, rate/date snapshot; dual residuals; exchange differences at reconciliation |
| Reporting | GL, Trial Balance, historical aging, Balance Sheet, P&L; then tax reports and configurable expressions |
| Period control | Lock dates/exceptions, repeatable closing; sealing/hash integrity if required. HistoryMixin alone is not cryptographic ledger protection |
| Documents and exchange | PDF/sending, EDI and electronic invoices in separate addons; OCR as additional input subject to user review |
| Localization | Country-specific charts, tax policy, forms, and algorithms. Do not assume every localization reduces to YAML |

Local Odoo reference sources: `addons/account/models/account_move.py:2781,5501,5575,6275`; `account_move_line.py:115,245,2793,3138`; `account_partial_reconcile.py`; `account_full_reconcile.py`; `account_payment.py`; `account_payment_term.py`; `account_bank_statement_line.py`; `account_tax.py`; `partner.py` (FiscalPosition is here); `company.py:76`; `account_report.py`. Also use Odoo tests as a scenario catalog with independently formulated expectations.

## 7. Implementation architecture and change ownership

Owner map under the target checkout's current `AGENTS.md`:

| Owner | Responsibility |
|---|---|
| Django/PostgreSQL | Decimal storage, transactions, locks, FK/Check/Unique constraints, migrations |
| `angee.base.transitions` | Shared allowed-transition mechanics and concurrent state persistence |
| `angee.money` | Currencies, rates, basic rounding/conversion; fiscal policy is consumer-owned |
| `angee.sequence` | Transactional number allocation; accounting defines scope, sequence, and business uniqueness |
| `arp.base` / `arp.Company` | Company and membership; accounting extends accounting configuration |
| `arp.accounting` | Entries, posting, taxes, debt, payments, reconciliation, locks, accounting reports |
| `arp.analytic` | Analytic plans/accounts/distributions; accounting adds JournalItem provenance |
| GraphQL / React | Thin domain-operation calls and presentation through existing primitives |

Analog inventory: existing `parties.Person` and Invoice for specialization; sales/purchase extensions for cross-addon relationships; money/sequence for shared primitives; accounting ConfigPages/InvoiceWorkbench and shared List/Form for UI. A complex accounting concept does not belong in framework core merely because it is complex.

The specified angee-django checkout contains neither `arp.accounting` nor `arp.base`. All business changes therefore cannot correctly land there without changing repository composition. Recommended boundary: shared improvements here, domain fixes in their owner `arp.accounting`. Shipping accounting physically from angee-django would be a separate structural decision: move the agreed addon family together with dependencies, namespace, tests, and a plan to remove the old owner. Copying `models.py` alone creates two owners and broken dependencies.

Only this report was changed in the target checkout during this task. Moving the addon family or changing the runtime is outside the analysis.

Expected simplification: remove Payment's inference of partner type from direction; replace totals with one residual source; replace local reconciliation stamping with domain-graph traversal; remove fallback accounts; if moving implementation, remove the old one after consumers switch. Do not create parallel currencies, numbering, state machines, or partner tables.

Arpee's old `specs/domains/accounting.md` is a historical hypothesis, not the current architecture: it says `arp.account` rather than actual `arp.accounting`, describes money/sequence/state transitions as missing, and proposes moving ledger/tax into core. Current code and AGENTS take precedence. Align the specification with the owner map before implementation.

## 8. Sequence and acceptance criteria

1. **Establish location and baseline.** Choose addon delivery without duplicate owners. Compose a host connected to the exact sources under test; run existing accounting tests and frontend checks. Retain minimal scenarios with expected entries.
2. **Close P0 gaps.** Full-aggregate validation, draft-only editing/deletion, atomic posting; residual and Payment's two axes; payment-group validation; correct reconcile/unreconcile components. Acceptance: 100→40→60, 40→unreconcile, customer/vendor refunds, repeated requests, concurrent payments, rejection of mixed companies, posted-invoice deletion blocked.
3. **Complete debt and taxes.** Item maturities, installment rounding to the total, multiple included taxes, refund distributions, tax-account validation. Acceptance: 1000→300/700, gross 120→net 100 + 10 + 10; document, GL, and residual agree in every scenario.
4. **Add accounting controls and basic reports.** Manual balanced entries, lock dates, number constraints, audit/reversal policy, GL/Trial Balance/BS/P&L/aging. Acceptance: debits equal credits, account movements reconcile to GL, historical residual considers settlement dates, closed periods cannot change through supported channels.
5. **Add the bank cycle.** Payment methods, outstanding/suspense, statement import/matching, advances, fees. Acceptance: registration and bank confirmation are distinct; reimport does not duplicate movements.
6. **Add FX.** Company/transaction/settlement in different currencies, rate snapshots, exchange differences, correct reversal. Establish a complete dual-currency model before enabling foreign-currency posting.
7. **Extend for the selected business.** Localizations, tax forms, EDI, PDF, cash basis, advanced reports. Scope depends on countries, legal entities, and processes; full parity cannot be claimed without those boundaries.

This is dependency order, not a schedule estimate. Minimum parameters for the next phase: where accounting ships, country/accounting regime, company count, currencies, and need for bank reconciliation/electronic documents. These do not prevent accepting the analysis or preparing P0 now.

## 9. Verification of future implementation

- Unit/domain: signs of all four invoice/refund kinds, multiple taxes, distribution rounding, installments, residual, graph closure.
- PostgreSQL transaction tests: concurrent posting of one document; two payments settling one residual; intersecting reconcile/unreconcile; complete rollback leaves no numbers, partials, or analytic items.
- API/security: ordinary accountant, invoicer, and a two-company user; update/delete/M2M/nested writes cannot bypass posting rules; access and reference compatibility are checked separately.
- Reports: reconciliation to GL and historical cutoffs; document totals do not replace the posted ledger; draft/cancelled records are excluded according to policy.
- UI: create → lines/taxes → posting → partial payment → residual → refund/reversal; shared forms/tables and error presentation.
- Delivery: owner migrations, `angee build`, runtime migrations, permissions/resources/schema; required Python/frontend/browser checks under current AGENTS. Do not hand-edit generated runtime.

Do not automatically repost historical documents using a new tax formula. New fields and reconciliation semantics need a migration plan: inventory, opening-residual checks, identification of damaged components, filling only provable values, and a discrepancy report.
