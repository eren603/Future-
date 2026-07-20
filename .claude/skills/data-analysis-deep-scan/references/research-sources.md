# Research sources and design rationale

This skill was designed from primary/official documentation and active upstream projects. Recheck current versions before relying on version-specific APIs.

## OpenAI analysis and tool workflow

- [Analyze datasets and ship reports](https://developers.openai.com/codex/use-cases/datasets-and-reports): supports a workflow from messy files through cleanup, joins, hypotheses, models, visualizations, and reusable reviewable artifacts. This informed the artifact-first and reproducibility requirements.
- [Code Interpreter](https://developers.openai.com/api/docs/guides/tools-code-interpreter): documents iterative sandboxed code execution for data analysis, math, files, and graphs. This informed executable calculations rather than prose-only arithmetic.
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs): documents file input handling and format-specific processing. This informed source routing and preservation of the original file.
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): documents schema-constrained responses. This informed JSON job/contracts and machine-readable audit results.
- [Working with evals](https://developers.openai.com/api/docs/guides/evals) and [model optimization](https://developers.openai.com/api/docs/guides/model-optimization): recommend systematic evaluations on representative inputs. This informed the permanent synthetic self-test and fail-closed checks.
- [Deep research](https://developers.openai.com/api/docs/guides/deep-research): combines search/retrieval with code execution for analysis. This informed separating source acquisition from numerical verification.
- [Skills in the OpenAI API](https://developers.openai.com/cookbook/examples/skills_in_api): defines skills as reusable instruction/script/resource bundles. This informed packaging the protocol with deterministic scripts and references.

## Scientific Python and analytical engines

- [NumPy repository](https://github.com/numpy/numpy): foundational n-dimensional arrays, linear algebra, random-number and numerical primitives. Used for vectorized calculations, OLS algebra, deterministic random generators, and tolerance checks.
- [pandas repository](https://github.com/pandas-dev/pandas), [missing-data guide](https://pandas.pydata.org/docs/user_guide/missing_data.html), and [`DataFrame.merge`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html): cover labeled tables, group-by, IO, time series, missingness, and merge validation. These informed profiling, row-accounting, and join-cardinality rules.
- [SciPy repository](https://github.com/scipy/scipy) and [SciPy statistics documentation](https://docs.scipy.org/doc/scipy/reference/stats.html): provide maintained numerical and statistical routines. Used for tests, distributions, intervals, and diagnostic probabilities.
- [statsmodels repository](https://github.com/statsmodels/statsmodels), [regression diagnostics](https://www.statsmodels.org/stable/examples/notebooks/generated/regression_diagnostics.html), and [multiple-testing procedures](https://www.statsmodels.org/stable/stats.html): informed regression diagnostics, robust uncertainty, and multiplicity controls. The included OLS tool implements a dependency-light audited subset because statsmodels may not be installed.
- [scikit-learn repository](https://github.com/scikit-learn/scikit-learn), [common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html), [cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html), and [pipelines](https://scikit-learn.org/stable/modules/compose.html): explicitly cover preprocessing consistency, leakage, generalization, and pipeline isolation. These informed split-before-preprocess and group/time-aware evaluation rules.
- [DuckDB repository](https://github.com/duckdb/duckdb) and [Parquet guide](https://duckdb.org/docs/stable/data/parquet/overview): document in-process analytical SQL and efficient predicate/projection pushdown. These informed large-file routing without making DuckDB a mandatory dependency.
- [Polars repository](https://github.com/pola-rs/polars) and [Apache Arrow repository](https://github.com/apache/arrow): informed optional columnar/lazy processing and interoperable schemas for data too large for ordinary in-memory pandas work.
- [Pandera repository](https://github.com/unionai-oss/pandera) and [DataFrame schemas](https://pandera.readthedocs.io/en/stable/dataframe_schemas.html): document reusable type/property checks over dataframe-like objects. These informed the JSON validation contract while avoiding an optional runtime dependency.
- [Hypothesis repository](https://github.com/HypothesisWorks/hypothesis): property-based testing informed invariants and generated edge-case testing, although the packaged self-test uses only installed dependencies.
- [SymPy repository](https://github.com/sympy/sympy): symbolic/exact mathematics informed routing exact algebra beyond Decimal to a specialized engine when installed.

## Statistical interpretation standards

- [American Statistical Association statement on p-values](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf): p-values do not measure effect size, practical importance, or the probability a hypothesis is true; scientific conclusions should not hinge on a threshold alone. This informed effect-size, interval, assumptions, and graded-evidence reporting.
- [ASA task-force statement](https://magazine.amstat.org/blog/2021/08/01/task-force-statement-p-value/): emphasizes uncertainty, variability, multiplicity, and replicability. This informed sensitivity and multiple-testing requirements.
- [scikit-learn example on failure to infer causal effects](https://scikit-learn.org/stable/auto_examples/inspection/plot_causal_interpretation.html): supports the separation between predictive association and causal identification.

## Routing notes

The Documents router is an explicit artifact router: use it when the user intentionally selects `@document` and asks for a document output. Ordinary CSV/statistical analysis stays in this skill; workbook, PDF, DOCX, chart-image, and presentation artifacts invoke their dedicated skills so extraction/rendering rules are not weakened.
