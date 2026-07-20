# Script operation specification

Use this reference when constructing JSON jobs for the bundled tools. Unknown operation types, missing columns, invalid settings, non-finite inputs, cardinality violations, and unsupported output sizes fail closed.

## Analysis job root

```json
{
  "input": "table.csv",
  "sheet": 0,
  "delimiter": ",",
  "numeric_mode": "float",
  "confidence": 0.95,
  "seed": 1729,
  "max_output_rows": 10000,
  "multiple_testing": {"method": "holm", "alpha": 0.05},
  "operations": []
}
```

`input` is resolved relative to the job file. `sheet` and `delimiter` are optional. `numeric_mode` is `float` or `decimal`; Decimal mode preserves CSV text before parsing. `multiple_testing` adjusts p-values emitted by correlations, group tests, contingency tables, and non-intercept regression coefficients. Methods are `bonferroni`, `holm`, `fdr_bh`, and `fdr_by`.

Run:

```bash
python scripts/analyze_data.py --job analysis.json --output analysis-result.json
```

## Aggregate

```json
{
  "id": "by_region",
  "type": "aggregate",
  "group_by": ["region"],
  "numeric_mode": "decimal",
  "metrics": [
    {"agg": "size", "name": "rows"},
    {"column": "order_id", "agg": "nunique", "name": "orders"},
    {"column": "revenue", "agg": "sum", "name": "revenue"},
    {"column": "margin", "agg": "weighted_mean", "weight": "revenue", "name": "weighted_margin"}
  ]
}
```

Aggregations: `size`, `count`, `nunique`, `sum`, `min`, `max`, `mean`, `median`, `std`, and `weighted_mean`. Negative weights fail unless the metric explicitly sets `allow_negative_weights=true`. Output includes usable/excluded rows per metric and reconciles grouped sums to the raw total.

## Correlation

```json
{"type": "correlation", "x": "spend", "y": "sales", "method": "spearman", "alternative": "two-sided"}
```

Methods: `pearson`, `spearman`, or `kendall`. The tool uses pairwise complete finite numeric observations and reports dropped rows. Pearson receives a Fisher-z confidence interval when defined.

## Independent two-sample comparison

```json
{
  "type": "two_sample",
  "value": "conversion_value",
  "group": "variant",
  "group_a": "treatment",
  "group_b": "control",
  "test": "welch_t",
  "alternative": "two-sided",
  "bootstrap_statistic": "mean",
  "bootstrap_repetitions": 5000
}
```

Tests: `welch_t`, `student_t`, or `mannwhitney`. Welch is the default. Output includes group summaries, mean/median difference, Hedges' g, Cohen's d, rank-biserial effect where applicable, p-value, and seeded percentile-bootstrap interval.

## Paired comparison

```json
{
  "type": "paired_sample",
  "left": "after",
  "right": "before",
  "test": "paired_t",
  "bootstrap_statistic": "mean",
  "bootstrap_repetitions": 5000
}
```

Tests: `paired_t` or `wilcoxon`. Rows are paired by their existing row alignment, so establish the entity/time key before this operation. Output includes complete-pair count, paired differences, Cohen's dz, p-value, and paired bootstrap interval.

## Contingency table

```json
{"type": "contingency", "row": "variant", "column": "converted", "yates_correction": true}
```

Output contains observed counts, chi-square statistic, degrees of freedom, p-value, Cramér's V, minimum expected count, and the number of expected cells below five. Sparse-table warnings require an exact or specialized method before a firm inference.

## OLS regression

```json
{
  "type": "regression",
  "y": "sales",
  "x": ["spend", "price"],
  "intercept": true,
  "covariance": "hc3",
  "confidence": 0.95
}
```

Covariance is `hc3` or `classical`. The tool rejects rank-deficient or underdetermined designs. Output includes coefficients and intervals, fit measures, rank, condition number, VIF, Durbin–Watson on current row order, residual normality, Breusch–Pagan auxiliary test, leverage, Cook's distance, and an association-only claim limit. Use a specialized library for clustered, generalized, mixed, survival, panel, causal, or nonlinear models.

## Bootstrap interval

```json
{"type": "bootstrap", "column": "revenue", "statistic": "median", "repetitions": 10000, "seed": 1729}
```

Statistics: `mean`, `median`, or `proportion`. Proportion also requires `"success": <category>`. Repetitions must be 200–100000. Output is a seeded percentile interval; use BCa or design-aware resampling when bias, clusters, strata, time dependence, or complex sampling requires it.

## Ordered time change

```json
{
  "type": "time_change",
  "time": "timestamp",
  "value": "value",
  "group_by": ["entity_id"],
  "periods": 1,
  "method": "pct_change",
  "duplicate_policy": "fail"
}
```

Methods: `difference`, `pct_change`, or `log_return`. Time is parsed as UTC and sorted stably within groups. Duplicate group/timestamp keys fail by default. Percent change is returned as a fraction; zero baselines become null and are counted. Log returns require positive values.

## Validation contract operations

Column rules support `required`, `nullable`, `unique`, `type`, `min`, `max`, `allowed_values`, and full-match `regex`. Types are `numeric`, `integer`, `datetime`, `string`, or `boolean`.

Check kinds:

| Kind | Required fields | Purpose |
|---|---|---|
| `row_count` | `operator`, `expected` | verify dataset size |
| `sum`, `mean`, `count`, `nunique` | `column`, `operator`, `expected` | scalar reconciliation |
| `unique_key` | `columns` | composite-key uniqueness and null policy |
| `relation` | `left`, `operator`, `right` | row-wise column/scalar relation |
| `linear_identity` | `target`, `terms` | target equals intercept plus weighted column sum |

Operators: `eq`, `ne`, `lt`, `le`, `gt`, `ge`, and `close`. Float closeness uses `rtol` and `atol`; Decimal identities can set both to zero. `required=false` records an optional failure without quarantining the entire contract.

Run:

```bash
python scripts/verify_data.py --contract contract.json --output verification.json
```

## Join specification

```json
{
  "left": "orders.csv",
  "right": "customers.csv",
  "left_on": ["customer_id"],
  "right_on": ["customer_id"],
  "how": "left",
  "validate": "many_to_one",
  "suffixes": ["_order", "_customer"],
  "max_output_rows": 1000000,
  "audit_only": false,
  "output": "joined.csv"
}
```

Cardinality must be `one_to_one`, `one_to_many`, `many_to_one`, or explicitly approved `many_to_many` with `allow_many_to_many=true`. Null keys and mismatched key types fail. `all_strings=true` is an explicit whole-table read choice for text-preserved keys. Existing outputs are not replaced unless `overwrite=true`.

Run:

```bash
python scripts/join_data.py --spec join.json --manifest join-manifest.json
```
