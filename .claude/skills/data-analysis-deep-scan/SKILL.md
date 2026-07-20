---
name: data-analysis-deep-scan
description: Profile, clean, validate, calculate, join, aggregate, compare, statistically analyze, model, forecast, audit, and explain data with reproducible numeric verification. Use for every request involving veri/data, hesaplama/calculation, analiz/analysis, statistics, percentages, ratios, KPIs, correlations, regressions, experiments or A/B tests, hypothesis tests, forecasts, time series, CSV/TSV/JSON/JSONL/Parquet/XLSX tables, database extracts, or quantitative evidence extracted from PDF/DOCX/images; also use whenever a numerical claim, denominator, formula, or model result must be checked. Coordinate with spreadsheet, PDF, document, chart, and stricter domain skills; never claim exactness or causality beyond the evidence.
---

# Data Analysis Deep Scan

Turn raw or reported data into an auditable result. Lock the question, inspect the source, profile the data, choose a defensible method, calculate with code, independently verify material results, and separate observation from inference.

## Non-negotiable contract

- Apply this workflow to every quantitative data-analysis request, including apparently simple totals or percentages when their source or denominator matters.
- Use executable calculations for arithmetic, statistics, transformations, joins, simulations, forecasts, and model evaluation. Do not rely on mental arithmetic as the only calculation path.
- Preserve source files and source columns. Put cleaning decisions and derived fields in reproducible code or a workbook formula; never overwrite evidence silently.
- Keep units, currency, nominal/real basis, timezone, population/sample, numerator, denominator, weighting, missing-value policy, and rounding explicit.
- Distinguish `OBSERVED`, `CALCULATED`, `INFERRED`, `SCENARIO`, and `CAUSAL`. Correlation, prediction, or temporal order alone is not causal evidence.
- Prefer primary or authoritative sources for current external data and cite them near the claim. Record retrieval date, coverage, and source version when available.
- Process private uploads locally with the available tools. Do not publish or send user data elsewhere merely to make analysis easier.
- Let stricter domain and safety protocols win. Never weaken medical, legal, financial, blind-chart/C0, privacy, or future-leakage rules.

## Deep-scan workflow

### 0. Lock the analysis contract

Before calculating, write down:

1. the decision or question;
2. the unit of analysis and target population;
3. the measure or estimand, including numerator and denominator;
4. comparison groups, baseline, time window, and timezone;
5. requested precision and whether the result is descriptive, predictive, inferential, or causal;
6. the minimum output needed: answer, table, chart, workbook, code, memo, or model artifact.

Ask only for a missing choice that would materially change the answer. If it is non-blocking, proceed with a clearly labeled assumption and calculate sensitivity to plausible alternatives.

### 1. Route the source correctly

| Source or output | Route |
|---|---|
| CSV, TSV, JSON, JSONL, ordinary in-memory table | Use the scripts in this skill with pandas/NumPy/SciPy. |
| XLSX/XLS/Google Sheets, workbook formulas, pivots, or workbook-native charts | Invoke the spreadsheet skill; use this skill for the analytical contract and independent checks. |
| PDF table or visually positioned evidence | Invoke the PDF skill to extract and render-check it, then analyze the extracted table. |
| DOCX/Google Docs evidence or report deliverable | Invoke the documents skill. Use the explicit document router only when the user selected `@document` and requested a document artifact. |
| Chart, plot, screenshot, axes, annotations, OHLCV, or visual measurement | Invoke `chart-calculation-workbench`; invoke stricter blind-chart/financial skills when their triggers apply. |
| Database or many large columnar files | Inspect schema and query with SQL; prefer DuckDB/Polars/PyArrow if present and materially more efficient. Do not install them only by preference. |
| Current public facts or datasets | Retrieve from an official/primary source, keep the raw response or file, record access time, and cite it. |
| Repository-hosted data or methodology | Use the GitHub connector when available and pin the repository, path, ref, and commit/version. |

Do not treat prose extracted from a document as a reliable table until row/column structure, units, footnotes, page boundaries, and totals have been checked against a render.

### 2. Establish provenance and a data contract

Record source path/URL, SHA-256 for local inputs, file size, sheet/table name, encoding or delimiter, row/column counts, collection window, schema, keys, units, and transformations. State whether the dataset is raw, filtered, sampled, aggregated, revised, seasonally adjusted, or synthetic.

Define field-level expectations for required columns, types, nullability, uniqueness, ranges, allowed values, and cross-field identities. Use `scripts/verify_data.py` for supported contracts. Read `references/analysis-contract.md` before handling joins, exact money, repeated measures, sampling weights, experiments, multiple tests, regression, forecasting, or causal claims.

For two-table joins, use `scripts/join_data.py` when possible. It requires declared cardinality, rejects null keys and implicit many-to-many merges, reports match/unmatched expansion, and can run in audit-only mode before writing output.

### 3. Profile before interpreting

Run `scripts/profile_data.py` on tabular input. Inspect at least:

- row count, column names and types;
- missing, non-finite, zero, negative, constant, and near-unique fields;
- duplicate rows and duplicate/nullable keys;
- category cardinality and rare categories;
- minima, maxima, quantiles, dispersion, and robust outlier flags;
- date parsing, timezone, ordering, duplicate timestamps, gaps, and frequency;
- impossible values, mixed units, sentinel codes, truncation, censoring, and selection bias;
- join cardinality and row-count changes before and after every merge.

Never silently drop, impute, winsorize, deduplicate, coerce, or rescale. Report how many observations each decision affects.

### 4. Choose the numeric representation

- Use integers or `Decimal` from original text for currency, balances, counts, identifiers, and legally exact arithmetic. Specify rounding rule and stage.
- Use floating point for scientific/statistical work, with explicit `rtol`/`atol` and finite-value checks.
- Preserve significant digits from measurement; do not add false precision.
- Normalize units only into new columns. Preserve the original value and unit.
- Parse datetimes with an explicit timezone. Resolve daylight-saving ambiguity and calendar/session rules before resampling.

### 5. Choose a method that matches the design

Start descriptive. Use distributions, robust summaries, and group counts before a test or model.

- Weight only when weights have a defined meaning; report weighted and unweighted sample sizes.
- For two groups, determine independent versus paired observations before choosing a test. Report effect size and interval, not only a p-value.
- Check distribution shape, outliers, variance behavior, sample size, and dependence. Use Welch rather than pooled-variance t-tests unless equal variance is justified; use robust/nonparametric alternatives when appropriate.
- For proportions and contingency tables, report cell counts and expected-count limitations.
- Correct or explicitly scope multiplicity when testing many hypotheses. Keep exploratory and confirmatory analyses separate.
- For regression, inspect rank, condition number, residual pattern, leverage/influence, heteroskedasticity, autocorrelation, nonlinearity, and out-of-sample validity. Coefficients are conditional associations unless the design supports causality.
- For prediction, split before preprocessing. Use pipelines and cross-validation that respect time, entity/group, geography, and repeated observations. Never let future or duplicate-entity information cross the split.
- For time series, preserve order; state frequency, gaps, seasonality, transformations, forecast origin, horizon, and interval type. Backtest with rolling/expanding origins, never random future leakage.
- For causal questions, require a credible treatment assignment or identification strategy, assumptions, diagnostics, and sensitivity analysis. Otherwise return association only.

Read `references/method-selection.md` for the decision table and reporting requirements.

### 6. Calculate reproducibly

Use `scripts/analyze_data.py` for supported aggregations, correlations, independent/paired comparisons, contingency tables, OLS with HC3 uncertainty, bootstrap intervals, p-value adjustments, and ordered time changes. Its JSON job is the calculation specification and its JSON output is the audit record.

Read `references/operation-spec.md` for complete JSON fields, supported operations, limits, and examples.

For unsupported methods, create a small reviewable script or notebook that records:

- input hashes and code/environment versions;
- exact filters, joins, transformations, formulas, seeds, and hyperparameters;
- row counts at every material stage;
- warnings, assumptions, and dropped observations;
- machine-readable outputs before narrative interpretation.

Use the simplest sufficient library already present. pandas/NumPy/SciPy are the default local stack. scikit-learn is for validated prediction workflows. Prefer specialized, well-maintained libraries over hand-written algorithms, but independently check critical identities.

### 7. Verify by a second path

Every material result needs at least one independent check; high-stakes results need more.

- Recompute totals or rates from raw counts, not from rounded display values.
- Reconcile parts to wholes and group totals to the ungrouped total.
- Check conservation identities, bounds, monotonicity, uniqueness, dimensional units, and expected signs.
- Compare vectorized and grouped calculations with a second formulation or a small hand-checkable subset.
- Re-run stochastic methods with a fixed seed and sensitivity across reasonable seeds/specifications.
- Check tolerance-aware equality for floats and exact equality for counts/Decimal values.
- For models, compare against a naive baseline and inspect out-of-sample errors, not only fit statistics.
- Use `scripts/verify_data.py`; any failed required check makes the result `QUARANTINE` until explained or corrected.

### 8. Stress-test the conclusion

Test whether the conclusion changes under plausible alternatives: missing-data treatment, inclusion/exclusion rules, outlier policy, weighting, time window, denominator, transformation, model specification, and multiple-testing correction. Report fragility rather than choosing the most favorable result.

### 9. Deliver the evidence chain

Lead with the strongest supported answer. Then provide:

1. result with unit and coverage;
2. evidence label (`OBSERVED`, `CALCULATED`, `INFERRED`, `SCENARIO`, or `CAUSAL`);
3. source/provenance and sample size;
4. exact method, denominator, interval/effect size, and relevant assumptions;
5. verification status and sensitivity result;
6. limitations and what additional evidence would change the conclusion;
7. reusable code, manifest, transformed data, workbook, or chart when useful.

Keep exploratory findings visibly separate from pre-specified claims. A polished chart or small p-value does not upgrade weak evidence.

## Fail-closed conditions

Return `QUARANTINE`, request the missing information, or limit the output to a qualified descriptive result when any material condition holds:

- source, population, unit, time basis, numerator, denominator, or weighting is unresolved;
- required fields are missing, types cannot be safely coerced, or non-finite values enter a calculation;
- duplicate keys or many-to-many joins multiply rows without an explicit design;
- missingness, exclusion, outliers, or imputation materially changes the result and is undisclosed;
- exact money/count work has already lost precision through floating conversion;
- train/test, time, group, target, or future leakage is possible;
- test assumptions or independence are materially violated without a robust alternative;
- sample size or event count cannot support the requested inference/model;
- multiple comparisons, optional stopping, or post-selection inference is ignored;
- a causal claim lacks an identification strategy;
- independent recomputation, invariants, or reconciliation fails;
- the narrative, table, chart, and calculation manifest disagree.

## Resources

- `scripts/profile_data.py`: deterministic schema, quality, distribution, outlier, correlation, and time-order profile.
- `scripts/join_data.py`: two-table join with type, null-key, cardinality, row-expansion, and match-state auditing.
- `scripts/analyze_data.py`: JSON-specified calculations and statistical analyses with dropped-row counts and audit metadata.
- `scripts/verify_data.py`: fail-closed schema, range, uniqueness, row-count, total, relation, and linear-identity checks.
- `scripts/self_test.py`: synthetic end-to-end calculations and edge-case checks for all four tools.
- `references/analysis-contract.md`: provenance, exactness, joins, missingness, reproducibility, and claim taxonomy.
- `references/method-selection.md`: statistical/predictive method selection, assumptions, effect sizes, intervals, and leakage controls.
- `references/operation-spec.md`: complete JSON job, join, and validation contract schemas with examples.
- `references/research-sources.md`: official OpenAI, GitHub, scientific-computing, and statistical-method sources used to design this skill.
