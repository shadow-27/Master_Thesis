# Methodology comparison: our FAVAR/NS-VAR pipeline vs ECB WP 544 (Mönch, 2005)

**Goal of this document**

You asked for a detailed write-up comparing:

1) **What we implemented in this thesis repository** (data → processing → models → forecasts → evaluation → observed results)

versus

2) **What the ECB Working Paper No. 544 does** (“Forecasting the yield curve in a data-rich environment: A no-arbitrage factor-augmented VAR approach”, Emanuel Mönch, Nov 2005)

…and then **what we can change to improve our empirical results**.

**Primary sources used here**

- Our pipeline description + extracted executed results: `docs/favar_taylor_pipeline_professor_review.md`
- Our executed notebook (source of truth for what was run): `notebooks/favar_taylor_comparison_executed.ipynb`
- ECB paper PDF in repo root: `ecbwp544.pdf`
- ECB snippet extraction (verbatim-ish text windows to avoid “guessing”): `docs/ecbwp544_key_snippets.txt`

---

## 1) What we did (current repo pipeline)

This is a concise summary; see `docs/favar_taylor_pipeline_professor_review.md` for full step-by-step.

### 1.1 Data

**Yields**

- Source: FRED constant-maturity Treasury yields (`DGS*`).
- Daily → monthly: resampled to **month-end frequency** using the **monthly mean**, then forward/back filled.
- Tenors used: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y.
- Aligned monthly sample in executed run: **1980-01 to 2025-12** (552 obs).

**Macro**

- Source: FRED macro series.
- Transformations: a mix of annualized log-differences (growth/inflation-type series) and levels (rates/spreads/volatility).
- Monthly: resampled to monthly mean.

### 1.2 Factors

**Yield factors (Nelson–Siegel, cross-sectional per month)**

- Each month, fit Nelson–Siegel to the 11 yields across maturities → estimated: level, slope, curvature, plus a decay parameter $\lambda$.

**Macro factors (PCA)**

- Filter macro variables by coverage, standardize, then PCA.
- Executed run used **3 principal components**, explaining **71.42%** of variance.

### 1.3 Forecast models

**NS-VAR**

- VAR on (differenced) Nelson–Siegel factors.
- 1-step ahead forecast of factors, then reconstruct yields from forecasted factors.

**FAVAR**

- VAR on (differenced) [Nelson–Siegel factors + macro PCA factors].
- Expanding window, recursive refit for each test month.

**Baselines**

- “Taylor-yield” baseline: per-tenor expanding OLS using lagged yield and a broad lagged macro information set.
- Separate “Taylor rule” regression for Fed Funds is also reported (policy-rate-only diagnostic).

### 1.4 Evaluation and observed results (executed notebook)

Test window in executed run: **2015-12 to 2025-12**.

Headline averages across the 11 tenors:

- Avg RMSE:
  - Taylor-yield: **0.6027**
  - NS-VAR: **0.7310**
  - Best FAVAR (selected): **0.7252** (FAVAR_VAR1)

- Avg MAE:
  - Taylor-yield: **0.2738**
  - NS-VAR: **0.5916**
  - Best FAVAR: **0.5914**

Per-tenor “wins” (lowest RMSE among Taylor / NS-VAR / FAVAR):

- Taylor: **7 / 11** tenors
- FAVAR: **2 / 11** tenors (3M, 6M)
- NS-VAR: **2 / 11** tenors (20Y, 30Y)

So, **in our current design (1-step ahead, last-10-years test, strong Taylor-yield benchmark)**, Taylor-yield is best on average.

---

## 2) What the ECB paper does (WP 544) — methodology recap

This recap is grounded in the ECB paper text as extracted into `docs/ecbwp544_key_snippets.txt`.

### 2.1 Data and sample (ECB)

**Macro dataset (data-rich)**

- Factors are extracted from a panel of **about 160 monthly macro time series** for the **US**.
- The dataset includes industrial production-related series, many employment series, many price indices, monetary aggregates, surveys, stock indices, exchange rates, etc.

**Stationarity + standardization**

- The paper follows Stock & Watson principal-components methods, which require stationarity.
- It applies “preadjustments” to the large panel to achieve stationarity and **standardizes** series to mean 0 / variance 1.

**Yield data**

- Uses **zero-coupon** yields constructed from US Treasury bonds using the method in **Bliss (1997)**.
- Uses maturities including 1, 3, 6, 9 months and 1, 2, 3, 4, 5, 7, 10 years.
- Described as **continuously-compounded, smoothed zero-coupon yields**.

**Estimation/forecast sample**

- Model is estimated and forecast over **1983:01 to 2003:09** (post-Volcker disinflation).

### 2.2 Factor construction (ECB)

- Extracts common factors using **static principal components** (Stock & Watson).
- Notes: first 10 factors explain about 70% of panel variance; the **first four** account for most of that contribution.
- Chooses **four macro factors** (plus the short rate) for **parsimony**, because the number of risk-price parameters grows quickly with the number of factors.

### 2.3 Model structure (ECB): no-arbitrage affine term structure + FAVAR states

High-level structure:

- State vector includes:
  - the **short rate** (operationalized as the 1-month yield)
  - plus **four macro factors** extracted from the large macro panel.

- **State dynamics** are modeled via a **factor-augmented VAR**.

- **Yield pricing** is governed by an affine no-arbitrage term structure model:
  - yields are affine functions of the state,
  - and the factor loadings / intercepts are computed recursively in a way that enforces no arbitrage.

### 2.4 Estimation approach (ECB)

Two-step spirit:

1) Estimate the VAR state dynamics (e.g., VAR(1) for states in the forecast section).
2) Estimate risk-price parameters (e.g., $\lambda_0$, $\lambda_1$) by minimizing squared fitting errors of the term-structure model.

The paper also notes that estimated **prices of risk** can be sensitive to model specification choices.

### 2.5 Forecast design + benchmarks (ECB)

**Forecast window + recursion**

- Out-of-sample forecast period: **2000:01 to 2003:09**.
- Models are estimated recursively using data **from 1983:01 up to the forecast origin**, beginning in 2000:01.

**Forecast horizons**

- Reports performance at **multiple horizons** including:
  - 1-month ahead
  - 6-months ahead
  - 12-months ahead

**Benchmarks compared in the ECB paper**

The ECB paper compares the no-arbitrage FAVAR against:

- No-arbitrage VAR with a small macro set + short rate
- VAR(1) on yield levels
- Diebold–Li (2005) three-factor Nelson–Siegel (with fixed $\lambda$)
- “Essentially affine” latent-factor ATSM (A0(3))
- Random walk (no-change)

**Key qualitative forecast finding (important for interpreting our results)**

- At the **1-month horizon**, yield-based models (random walk / latent-factor ATSM) can be hard to beat.
- At **6- and 12-month horizons**, the no-arbitrage FAVAR is reported to outperform the considered benchmarks broadly.

**Significance testing**

- Uses a White (2000)-style superior predictive ability test with a **block bootstrap** (1000 resamples are explicitly mentioned).

---

## 3) Side-by-side: main methodological differences

### 3.1 Data construction differences

**Yield definition**

- **Ours:** FRED constant-maturity yields (par yields), monthly means.
- **ECB:** constructed **zero-coupon** yields (Bliss method), continuously-compounded smoothed yields.

This matters because no-arbitrage ATSMs typically want (or are easiest with) zero-coupon yields.

**Macro information set size**

- **Ours:** comparatively small, curated macro dataset (then PCA ends up using 3 factors from ~10 high-coverage variables in the executed run).
- **ECB:** ~160 monthly macro series (explicitly “data-rich”).

### 3.2 What plays the role of “yield curve factors”

- **Ours:** we explicitly estimate **latent yield factors** via Nelson–Siegel each month (level/slope/curvature) and then forecast those factors.
- **ECB:** the core “observable” drivers are **macro common components + the short rate**, with yields linked via **no-arbitrage restrictions**.

So philosophically:

- We are closer to **Diebold–Li style factor forecasting** (latent yield factors) plus macro augmentation.
- ECB WP 544 is closer to a **macro-driven ATSM** (affine pricing + FAVAR state equation) with a data-rich macro panel.

### 3.3 No-arbitrage restrictions

- **Ours:** Nelson–Siegel fits are cross-sectional least squares; forecasts are not constrained by no-arbitrage.
- **ECB:** yields are priced by an affine model with no-arbitrage restrictions.

No-arbitrage can improve:
- cross-sectional coherence of fitted yields,
- and (often) medium-horizon forecasts when the state dynamics are well specified.

### 3.4 Forecast horizon design

- **Ours:** currently **1-step (1-month) ahead only**.
- **ECB:** explicitly studies **1-, 6-, 12-month horizons** and finds the strongest gains beyond 1 month.

This difference alone can explain why our macro-factor models do not “win” on average: we are evaluating primarily where the ECB paper itself says macro-based models are least advantaged.

### 3.5 Benchmark set and “difficulty” of the baseline

- **Ours:** the headline benchmark “Taylor-yield” is a strong per-tenor expanding OLS using lagged yields and a broad lagged macro set.
- **ECB:** includes random walk, VAR-yields, Diebold–Li, and ATSM baselines.

A very strong baseline is fine academically (it’s honest), but it changes the question:

- If Taylor-yield is essentially “a flexible predictive regression per maturity”, it can soak up a lot of predictive signal.
- Then the contribution of a factor model has to be **incremental** relative to a high-performing predictor, which can be much harder.

---

## 4) What we can do to improve our results (concrete, prioritized)

Below are improvements, ordered from “most likely to matter / easiest to validate” to “bigger methodological shifts.”

### Priority 0 — Fix correctness risks in the existing pipeline

1) **Verify the Nelson–Siegel $\lambda$ parameterization is consistent** end-to-end.
   - Our pipeline report flags a potential mismatch: estimation uses $e^{-\tau/\lambda}$ but reconstruction uses $e^{-\lambda\tau}$.
   - If true, this is not a tuning issue; it is a **model mismatch** that can distort reconstructed yields and OOS evaluation.

2) **Sanity-check maturity units** (months vs years) wherever $\tau$ enters loadings.

3) **Re-check the month aggregation choice** (monthly mean vs end-of-month) to ensure it matches how the “month $t$ to month $t+1$” forecast is interpreted.

### Priority 1 — Evaluate the horizons where macro-FAVAR models are expected to help

ECB WP 544 is very explicit that gains show up most clearly beyond 1 month.

- Add **6- and 12-month ahead** yield forecasts to the existing notebook, and report RMSE/MAE by tenor and averaged across tenors.
- Keep 1-month ahead as a baseline.

If FAVAR improves materially at 6/12 months (even if it doesn’t at 1 month), that becomes a clean, thesis-friendly story.

### Priority 2 — Add the ECB-style benchmark suite (for interpretability)

Add these benchmarks alongside Taylor-yield (not necessarily replacing it):

- **Random walk** (no-change) per tenor.
- **VAR on yield levels** (small-dimensional, yield-only predictor).
- **Diebold–Li (2005)** three-factor Nelson–Siegel with fixed $\lambda$ (and VAR/AR factor dynamics).

This does two things:

- It makes your results comparable to the yield-curve forecasting literature.
- It helps diagnose whether your current underperformance is due to “macro-FAVAR is weak” vs “Taylor-yield baseline is unusually strong.”

### Priority 3 — Move toward a truly data-rich macro factor extraction

ECB uses ~160 series; our executed run effectively uses a much smaller set.

Practical path:

- Use a large panel dataset like **FRED-MD** (or build a similar panel from FRED).
- Apply stationarity transforms (as in Giannone/Stock–Watson style pipelines).
- Standardize and extract the first **4** principal components.

Then re-run the existing FAVAR forecast design with:

- 4 macro factors instead of 3
- a broader information set

This aligns the “FAVAR” part with the ECB paper, even before adding no-arbitrage pricing.

### Priority 4 — If the target is to replicate the ECB idea: add no-arbitrage pricing

If your goal is not just to “use VARs with factors” but to be methodologically closer to WP 544, the big gap is the no-arbitrage affine pricing layer.

High-level implementation steps:

1) Define a state vector $Z_t = [r_t, F_{1,t},\dots,F_{k,t}]$ where $r_t$ is the 1M yield and $F$ are macro factors.
2) Fit VAR dynamics for $Z_t$.
3) Specify market prices of risk (affine in states) and estimate risk-price parameters by minimizing yield fitting errors.
4) Compute affine loadings $(a_n, b_n)$ recursively and produce forecasts $\hat y_t^{(n)}$ from $\hat Z_{t+h|t}$.

This is more work, but it directly addresses a core methodological difference.

### Priority 5 — Add “paper-style” inference for forecast comparisons

To strengthen the thesis empirically:

- Report **relative RMSEs** vs random walk (the ECB paper emphasizes this).
- Add a **block bootstrap** (or DM tests with HAC) to assess whether improvements are statistically meaningful, not just numerically different.

---

## 5) A suggested narrative that matches both our evidence and the ECB paper

A clean thesis-compatible story (if supported after the above changes) is:

1) At the 1-month horizon, yield forecasts are hard to beat; flexible yield-based baselines can dominate.
2) At medium horizons (6–12 months), macro information (especially data-rich factors) and term-structure restrictions can add value.
3) Therefore, we evaluate multiple horizons and show where/why the macro-factor approach helps.

---

## 6) Deliverables checklist (what to implement next, if you want)

If you want to act on this, here is an “ordered implementation checklist”:

1) Fix/verify NS $\lambda$ consistency + maturity units.
2) Add 6- and 12-month horizons to the existing expanding-window pipeline.
3) Add random-walk, VAR-yields, and Diebold–Li benchmarks.
4) Expand macro panel (FRED-MD style) and re-run PCA with 4 factors.
5) (Optional, research-level) implement the no-arbitrage affine pricing layer.
6) Add statistical tests (block bootstrap / DM).

If you tell me whether you want steps 1–4 (quick wins) or also step 5 (no-arbitrage ATSM), I can implement the code changes and regenerate the executed notebook outputs.
