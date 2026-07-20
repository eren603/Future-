# Method selection and reporting

This is a decision aid, not a substitute for the study design. Begin with the observation unit, dependency structure, and target claim.

## Descriptive questions

| Goal | Primary output | Required checks |
|---|---|---|
| Typical numeric value | median and IQR; mean and SD when meaningful | missingness, skew, outliers, units |
| Category composition | counts and proportions with denominator | mutually exclusive/exhaustive categories, unknowns |
| Change over time | endpoints, absolute and relative change; distribution by period | timezone, frequency, gaps, revisions, baseline zero |
| Group comparison | group counts, distributions, effect size and interval | independence/paired status, imbalance, missingness |
| Relationship | scatter/distribution, Pearson or rank association | nonlinearity, outliers, range restriction, confounding |

Do not summarize a multimodal or highly skewed distribution with a mean alone. Keep raw group sizes next to normalized percentages.

## Two-sample inference

1. Determine paired versus independent observations. Never use an independent test for before/after measurements on the same units.
2. Use Welch's t-test for independent means unless pooled variance is substantively justified.
3. Use a paired t-test for paired mean differences when their distribution is defensible.
4. Use Mann–Whitney for a rank/distribution comparison when its estimand is appropriate; it is not automatically a median test.
5. For small samples, severe ties, sparse counts, or unusual sampling, prefer exact/permutation methods when available.
6. Report group summaries, difference direction, effect size, confidence interval, test statistic, p-value, and assumptions.

Treat a p-value as one graded measure under a specified model. It is not the probability that the null is true, not an effect size, and not a causal certificate. Avoid binary language based solely on a threshold.

## Contingency tables and proportions

- Show observed counts, not only percentages.
- State whether denominators differ across rows/columns.
- Inspect expected cell counts before relying on chi-square asymptotics; use an exact method for sparse small tables where appropriate.
- Report an association effect size such as Cramér's V and its practical context.
- For repeated binary outcomes or clustered samples, ordinary chi-square independence is generally inadequate.

## Correlation

- Pearson measures linear association and is sensitive to outliers.
- Spearman and Kendall measure monotone/rank association and handle nonlinear monotone structure better, but do not remove confounding.
- Report pairwise complete `n`, missing rows, coefficient, interval when supported, and the visible functional form.
- Do not correlate IDs, accumulated totals, or unrelated trending series without a design that handles their structure.

## Regression

Before interpretation, check:

- outcome scale and functional form;
- complete-case loss and selection;
- full rank, collinearity/VIF, and condition number;
- residual nonlinearity, heteroskedasticity, autocorrelation, and influential observations;
- whether standard errors match clustering/time dependence;
- whether interactions and nonlinear terms were pre-specified or exploratory;
- whether evaluation is out-of-sample when the goal is prediction.

Use HC3 heteroskedasticity-consistent uncertainty as a robust default for ordinary cross-sectional OLS when cluster/time dependence is absent. It does not fix nonlinearity, omitted variables, measurement error, selection, dependence, or causality.

Report coefficient units (“outcome units per one x-unit”), interval, p-value when relevant, sample size, fit, covariance method, diagnostics, and claim limit. Standardized coefficients are optional and never replace original-unit effects.

## Multiple testing and exploration

- Define the family of hypotheses before choosing a correction.
- Holm controls family-wise error without the independence requirement of simple Sidak-style reasoning.
- Benjamini–Hochberg controls false discovery rate under independent or suitable positive dependence; use a more conservative method such as Benjamini–Yekutieli for general dependence when warranted.
- Label analyses selected after seeing the data as exploratory. A correction does not erase selection bias, optional stopping, or researcher degrees of freedom.

## Prediction and cross-validation

- Establish a naive baseline first.
- Split data before fitting preprocessing, imputation, feature selection, dimensionality reduction, or target encoding.
- Keep the same entity/group on one side of a split.
- Use forward/rolling splits for temporal data and ensure every feature would have existed at prediction time.
- Tune inside training folds; evaluate once on an untouched test set or use nested cross-validation.
- Report a distribution of fold/period errors and subgroup errors, not a single best score.
- Control randomness with fixed seeds while checking stability across seeds.
- Predictions and feature importances are not causal effects.

## Forecasting

Define forecast origin, horizon, update cadence, frequency, timezone, known-future covariates, and interval type. Compare against seasonal-naive and last-value baselines. Backtest across multiple historical origins. Do not leak revised values, centered windows, or future-normalized features into earlier forecasts.

Distinguish:

- confidence interval for a parameter/mean;
- prediction interval for a future observation;
- scenario range based on chosen inputs;
- empirical backtest error distribution.

## Causal claims

Allow a `CAUSAL` label only when the analysis specifies treatment, outcome, target population, time ordering, identification strategy, assumptions, diagnostics, and sensitivity. Examples include randomized assignment or a defensible instrumental-variable, regression-discontinuity, difference-in-differences, or synthetic-control design. Each requires domain-specific checks.

If those conditions are absent, use “associated with,” “predicts,” or “differs between,” not “causes,” “impact,” or “effect.”

## Sensitivity matrix

For a material conclusion, vary at least the relevant rows:

| Dimension | Typical alternatives |
|---|---|
| Missing data | complete case; explicit unknown; justified imputation |
| Outliers | included; robust statistic; pre-defined exclusion |
| Weighting | unweighted; design/exposure weighted |
| Denominator | eligible population; observed population; exposure time |
| Time | alternate start/end; pre/post windows; seasonal alignment |
| Functional form | levels; log; nonlinear term; robust model |
| Uncertainty | classical; robust; clustered; bootstrap |
| Multiplicity | unadjusted exploratory; Holm; FDR |

If the substantive conclusion changes, report it as specification-sensitive.
