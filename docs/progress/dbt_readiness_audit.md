# dbt readiness audit (historical summary)

## Status

This file previously contained a copy of the project roadmap rather than the
audit. It is restored here as a concise audit summary. The implementation and
live reconciliation are in
[`dbt_implementation_report.md`](./dbt_implementation_report.md).

**Original readiness classification:** READY WITH CONDITIONS for a dev-only
dbt shadow build in `dbt_dev`; NOT READY for production Gold replacement or
incremental dbt.

**Current state:** the shadow build has been implemented and validated. Gold
has not been replaced.

## Verified baseline

| Fact | Result |
|---|---|
| PostgreSQL | 16.15; database `ecommerce_dw` |
| Existing layers | Bronze, Silver, Gold; 31 tables + 9 views |
| Silver data tables | 9, plus `rejected_rows` |
| Bronze / Silver / Gold rows | 1,550,922 / 1,289,062 / 571,238 |
| Existing Gold analytical views | 9 |
| Existing Gold FKs | 0 |
| Existing Silver declared FKs | 7, all valid |
| Existing Python tests | 27 passed |
| dbt project before implementation | Skeleton only |
| Git baseline | Not present in this workspace |
| dbt installed before implementation | No |

## Key findings that shaped the dbt layer

1. **Shipping flag was semantically wrong.** Gold's
   `shipped_after_limit` compared `shipping_limit_date` with customer delivery.
   The corrected rule is `order_delivered_carrier_date > shipping_limit_date`:
   10,423 rows versus 23,000 old, with only 16 overlap.
2. **Seller metrics were item-weighted.** The corrected seller late rate counts
   one outcome per seller/order. This changes 366 sellers by more than 1pp, with
   a 37.40pp maximum difference.
3. **Category review scores were item-weighted.** The corrected mart scores one
   order/category once. This changes 69 of 74 categories, maximum 0.48 stars.
4. **Delivery population was inconsistent.** Gold's numerator included a
   canceled order with a delivery timestamp while its denominator used delivered
   status. The dbt mart uses orders with a delivery timestamp on both sides:
   7,827 late / 96,476 eligible = 8.11%. The 7.87% figure is
   `7,827 / 99,441`, an all-order denominator, not the current Gold view rate.
5. **Surrogate keys were unstable.** Gold used `ROW_NUMBER()` for
   `dim_category` and Silver's reset sequence for `fact_reviews`. dbt uses
   deterministic MD5 keys over natural identifiers; hashes were stable across
   repeated builds.
6. **Silver is not multi-batch safe.** Silver still truncates and rebuilds from
   all Bronze rows without a `_load_id` filter. dbt reads the current snapshot;
   it does not fix this pipeline behavior.
7. **No Git or CI baseline.** The workspace still has no Git repository, so
   checkpoint commits and CI provenance could not be verified.

## Conditions satisfied by the implementation

- [x] Restricted `dbt_dev_user` created; no superuser/createdb/createrole.
- [x] Isolated `dbt_dev_staging`, `dbt_dev_intermediate`, `dbt_dev_marts`.
- [x] dbt reads Silver only; no Bronze or Gold access.
- [x] `dbt debug`, `dbt compile`, `dbt build`, and `dbt test` pass.
- [x] Stable deterministic keys; repeated-build hash checks pass.
- [x] Corrected shipping, seller, category, and delivery metrics.
- [x] 9 analytical marts, including payment reconciliation and quality flags.
- [x] 27/27 existing Python tests still pass.

## Unresolved conditions

- [ ] Git repository and baseline commit.
- [ ] CI pipeline and automated dbt checks.
- [ ] Silver multi-batch/idempotency hardening.
- [ ] Business sign-off on corrected metrics.
- [ ] Any production Gold migration or incremental dbt rollout.

## Historical decision answers

1. **Where does dbt fit?** After Silver, before BI, building a parallel Gold
   candidate.
2. **Compatible with Python pipeline?** Yes, if dbt remains read-only on Silver
   and writes only to isolated dev schemas.
3. **Can existing Gold SQL be copied?** Only with corrections and tests; do not
   copy blindly.
4. **What is the safest first milestone?** Sources + staging + dimensions in
   `dbt_dev`.
5. **Can it operate only in dbt_dev?** Yes; verified.
6. **Can it harm Gold?** Not with the verified role/ACL separation.
7. **Safest Gold model to migrate first?** Stable dimensions and daily sales.
8. **What must not change?** Raw CSVs, Bronze, Silver, Gold, credentials, and the
   existing test suite.
9. **What remains before production?** Git/CI, Silver hardening, metric
   sign-off, backup/rollback, and a migration plan.
