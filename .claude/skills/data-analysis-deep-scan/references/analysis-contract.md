# Analysis contract

Load this reference before joins, exact money, repeated measures, sampling weights, experiments, multiple tests, regression, forecasting, or causal claims.

## 1. Minimum provenance manifest

Record these fields when available:

- immutable source identifier: local path plus SHA-256, or URL/repository/path/ref/commit;
- retrieval timestamp for live sources and source publication/revision date;
- format, encoding/delimiter, workbook sheet or database table/query;
- row and column counts before and after each filter, join, reshape, or aggregation;
- population, sampling frame, observation unit, key fields, and collection window;
- field names, types, units, timezone/calendar, currency and nominal/real basis;
- missing-value codes, censoring/truncation, revisions, seasonal adjustment, and known exclusions;
- software/library versions, random seeds, method settings, and output hash.

Never substitute a display table or rounded chart label for the raw source when the raw source is available.

## 2. Exactness and rounding

Use the representation that matches the claim:

| Data | Representation | Verification |
|---|---|---|
| Counts, integer IDs | integer/string | exact equality; uniqueness and bounds |
| Currency or contractual decimals | `Decimal` parsed from source text | exact equality or an explicitly named currency tolerance |
| Binary floating workbook cells | float, unless source text preserves decimals | state that original binary precision is the limit |
| Physical measurements/statistics | float | finite checks plus explicit relative/absolute tolerance |
| Dates/times | timezone-aware timestamp | UTC normalization plus original timezone/calendar |

Round only for presentation unless the business rule says rounding is part of the calculation. State the rounding mode (`half_even`, `half_up`, floor, etc.), scale, and whether rounding occurs per row or after aggregation. These can produce different totals.

For ratios and percentages, keep the raw numerator and denominator. A percentage-point change is `p2 - p1`; a relative percent change is `(p2 - p1) / p1`. Never use them interchangeably.

## 3. Join protocol

Before a merge:

1. normalize key types without discarding original keys;
2. count null keys and duplicates on both sides;
3. declare expected cardinality: one-to-one, one-to-many, or many-to-one;
4. reject an unintended many-to-many merge;
5. add a merge indicator and inspect left-only/right-only rows;
6. compare pre/post row counts and reconcile totals that should be conserved;
7. retain examples of unmatched keys without exposing them unnecessarily.

In pandas, use `validate="one_to_one"`, `"one_to_many"`, or `"many_to_one"` when the design permits. Do not infer a correct join because the code ran successfully.

## 4. Missingness and exclusions

Separate:

- structurally not applicable;
- not collected;
- measurement failure;
- suppressed/redacted;
- zero as an actual measurement;
- sentinel codes such as `-99` or `9999`;
- non-finite computational results.

For each analysis, report starting rows, rows excluded by every rule, complete-case rows, and final rows. Compare included and excluded observations on available fields when selection could change the conclusion.

Do not automatically impute. If imputation is justified, fit it only on training data, preserve an imputation indicator when useful, state the model and assumptions, and include uncertainty from imputation in inferential work.

## 5. Weights, clusters, and repeated observations

- Identify whether weights are frequency, probability/survey, exposure, reliability, or business allocation weights. They are not interchangeable.
- Report unweighted row count, effective/weighted count where meaningful, and total weight.
- Treat observations from the same person, account, device, site, household, or time block as dependent unless independence is justified.
- Split and cross-validate by the dependency unit. Use clustered or repeated-measure methods when inference requires them.
- A large row count does not compensate for a small number of independent clusters or events.

## 6. Claim taxonomy

Use one label per material claim:

- `OBSERVED`: directly present in the verified source.
- `CALCULATED`: deterministic transformation of observed data.
- `INFERRED`: estimate/test/model whose validity depends on statistical assumptions.
- `SCENARIO`: conditional output under chosen assumptions, including forecasts and simulations.
- `CAUSAL`: effect supported by a randomized design or explicit quasi-experimental identification strategy with diagnostics.

If evidence does not meet the requested claim level, downgrade the claim rather than upgrading the evidence rhetorically.

## 7. Independent verification ladder

Apply increasingly strong checks as risk grows:

1. schema/type/finite/range checks;
2. counts, sums, parts-to-whole reconciliation, and formula identities;
3. second implementation or alternative algebraic formulation;
4. hand-checkable subset with known answer;
5. sensitivity across inclusion, missingness, weights, windows, and specifications;
6. out-of-sample/temporal backtest or external replication;
7. domain-expert review for high-stakes interpretation.

Any disagreement remains visible in the report and triggers `QUARANTINE` until resolved.

## 8. Script job examples

Profile:

```bash
python scripts/profile_data.py --input data.csv --output profile.json
```

Analysis job:

```json
{
  "input": "data.csv",
  "seed": 1729,
  "confidence": 0.95,
  "multiple_testing": {"method": "holm", "alpha": 0.05},
  "operations": [
    {
      "id": "region_totals",
      "type": "aggregate",
      "group_by": ["region"],
      "metrics": [
        {"column": "revenue", "agg": "sum", "name": "revenue_sum"},
        {"column": "margin", "agg": "weighted_mean", "weight": "revenue", "name": "revenue_weighted_margin"}
      ]
    },
    {"id": "relationship", "type": "correlation", "x": "spend", "y": "revenue", "method": "spearman"},
    {"id": "model", "type": "regression", "y": "revenue", "x": ["spend", "price"], "covariance": "hc3"}
  ]
}
```

Safe join specification:

```json
{
  "left": "orders.csv",
  "right": "customers.csv",
  "left_on": "customer_id",
  "right_on": "customer_id",
  "how": "left",
  "validate": "many_to_one",
  "audit_only": true
}
```

Run `python scripts/join_data.py --spec join.json`. The tool rejects null join keys because pandas can match null to null in ways that differ from ordinary SQL expectations. Filter, repair, or separately model null-key rows first. Use `all_strings=true` only as an explicit key-normalization decision.

Exact-decimal aggregation sets top-level `"numeric_mode": "decimal"`. For CSV/text, the tool reads fields as strings before Decimal parsing. Decimal mode rejects comma punctuation because `1,234` and `1,23` are locale-ambiguous; normalize it explicitly into a new field first.

Validation contract:

```json
{
  "input": "ledger.csv",
  "all_strings": true,
  "columns": {
    "transaction_id": {"nullable": false, "unique": true},
    "amount": {"nullable": false, "type": "numeric", "min": 0}
  },
  "checks": [
    {"kind": "row_count", "operator": "ge", "expected": 1},
    {"kind": "sum", "column": "amount", "numeric_mode": "decimal", "operator": "eq", "expected": "1250.40"},
    {
      "kind": "linear_identity",
      "target": "total",
      "numeric_mode": "decimal",
      "terms": [{"column": "subtotal"}, {"column": "tax"}],
      "rtol": 0,
      "atol": 0
    }
  ]
}
```
