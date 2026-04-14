# FAVAR vs Taylor(-yield) Interest-Rate Forecasting — End-to-end workflow (for thesis review)

**Purpose of this document**

This Markdown note is a **step-by-step, end-to-end** description of what the current codebase does: from **data acquisition** → **data processing** → **model construction** → **forecasting protocol** → **results** → **current conclusion + recommended next steps**.

It is written so you can send it to a thesis supervisor for review and advice on what to do next.

**Primary source of truth**

- Main executed analysis notebook: `notebooks/favar_taylor_comparison_executed.ipynb`
- Data-fetch notebook (creates the CSVs used by the main notebook): `notebooks/fetch_data.ipynb`
- Regression/VAR sanity test script (mirrors the core pipeline): `scripts/test_notebook.py`

---

## 1) How to reproduce the pipeline (what to run)

### 1.1 Environment setup

1. Create a Python environment (Windows example):
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
2. Install packages:
   - `pip install -r requirements.txt`

Key packages used in the modeling steps:
- `pandas`, `numpy`
- `pandas-datareader` (FRED download)
- `scipy` (optimization)
- `scikit-learn` (standardization + PCA)
- `statsmodels` (OLS + VAR)
- `matplotlib` (figures)

### 1.2 Data refresh (optional, when you want to pull from FRED again)

The repository is designed so the main notebook can run **offline** using cached CSVs.

1. Open and run `notebooks/fetch_data.ipynb`.
2. This downloads the raw series from FRED and saves:
   - `data/yields_raw.csv`
   - `data/macro_raw.csv`

### 1.3 Main analysis (models + forecasts + results)

Run `notebooks/favar_taylor_comparison_executed.ipynb`.

Outputs (figures) are saved as PNGs in the `notebooks/` folder (because the notebook is executed with working directory `notebooks/`). Examples:
- `notebooks/nelson_siegel_factors.png`
- `notebooks/macro_variables.png`
- `notebooks/rmse_ratio_vs_taylor_heatmap.png`
- `notebooks/yields_favar_vs_taylor_all_tenors.png`

(There are also some figures in `results/figures/`, likely from earlier runs.)

---

## 2) Data: what we use and where it comes from

### 2.1 Yield curve data

**Source**: FRED (Federal Reserve Economic Data)

**Raw file**: `data/yields_raw.csv`

**Series (daily, then converted to monthly):**

| FRED code | Tenor label used in the notebook |
|---|---|
| DGS1MO | 1M |
| DGS3MO | 3M |
| DGS6MO | 6M |
| DGS1 | 1Y |
| DGS2 | 2Y |
| DGS3 | 3Y |
| DGS5 | 5Y |
| DGS7 | 7Y |
| DGS10 | 10Y |
| DGS20 | 20Y |
| DGS30 | 30Y |

**Sample used in the executed notebook**
- Start date: 1980-01-01
- End date: 2025-12-31

**Economic meaning**
- These are constant-maturity Treasury yields (percent), representing the term structure across maturities.

### 2.2 Macroeconomic data

**Source**: FRED

**Raw file**: `data/macro_raw.csv`

**Important data-quality note**
- The stored CSV contains some **non-date header rows** (e.g., repeated ticker headers).
- The main notebook explicitly cleans this by:
  1. attempting `pd.to_datetime(index, errors='coerce')`
  2. dropping rows where the index cannot be parsed as a date
  3. converting all series to numeric with `errors='coerce'`

**Raw series included (examples)**
- CPI (`CPIAUCSL`) and Core CPI (`CPILFESL`)
- Industrial production (`INDPRO`)
- Federal funds rate (`FEDFUNDS`) and effective fed funds (`DFF`)
- Unemployment rate (`UNRATE`)
- Payrolls (`PAYEMS`), housing starts (`HOUST`)
- Money supply (`M2SL`), mortgage rate (`MORTGAGE30US`)
- Some financial indicators (e.g., equity index `SP500`, VIX `VIXCLS`, credit spreads)

---

## 3) Data processing: turning raw series into model-ready monthly panels

All processing steps are implemented inside the main notebook (`notebooks/favar_taylor_comparison_executed.ipynb`).

### 3.1 Yield processing (`process_yields`)

**Goal:** convert daily Treasury yields into a clean monthly panel.

Step-by-step:

1. Ensure the index is a `DatetimeIndex`.
2. Resample daily yields to month-end frequency using **monthly mean**:
   - `yields_df.resample('ME').mean()`
3. Fill missing values:
   - forward-fill, then backward-fill: `.ffill().bfill()`
4. Rename columns from FRED codes to human-readable tenors (1M, 3M, …, 30Y).

Result: `yields_monthly` — a monthly yield panel with 11 tenors.

### 3.2 Macro processing (`process_macro`)

**Goal:** create a monthly macro panel with consistent transformations.

Step-by-step:

1. Ensure a `DatetimeIndex`.
2. Resample to monthly mean:
   - `macro_df.resample('ME').mean()`
3. Construct the processed variables:

**Annualized log-difference growth rates (× 12 × 100):**
- Inflation (headline):
  - `inflation_t = 1200 * (log(CPI_t) - log(CPI_{t-1}))`
- Inflation (core):
  - `inflation_core_t = 1200 * (log(CoreCPI_t) - log(CoreCPI_{t-1}))`
- Output growth (industrial production):
  - `output_t = 1200 * (log(IP_t) - log(IP_{t-1}))`
- Payroll growth, retail sales growth, housing starts growth, equity return, money growth

**Level variables (no differencing):**
- Policy rate(s): `fedfunds`, `fedfunds_eff`
- Unemployment: `unrate`
- Volatility: `volatility` (VIX)
- Credit spreads: `hy_spread`, `credit_spread`
- Breakeven inflation: `breakeven_inflation`
- Mortgage rate: `mortgage_rate`

Result: `macro_processed` — a monthly macro panel with mixed transformations.

### 3.3 Alignment (common sample)

**Goal:** ensure yields and macro have the same monthly dates.

Step-by-step:

1. Compute the intersection of month-end indices.
2. Keep yields with no missing values (`dropna()` after fill).
3. Keep macro panel aligned to yield dates.
4. Macro missingness is allowed at this stage; PCA later filters variables by coverage.

**Aligned sample in the executed notebook**
- 552 monthly observations
- 1980-01 to 2025-12

---

## 4) Yield curve factor extraction: Nelson–Siegel

### 4.1 Model definition

For maturity $\tau$ (in years), the notebook uses the Nelson–Siegel curve:

$$
 y(\tau) = \beta_0 + \beta_1 \left(\frac{1 - e^{-\tau/\lambda}}{\tau/\lambda}\right)
          + \beta_2 \left(\frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} - e^{-\tau/\lambda}\right)
$$

Interpretation:
- $\beta_0$ (level): long-run yield level
- $\beta_1$ (slope): short-vs-long component
- $\beta_2$ (curvature): medium-term “hump”
- $\lambda$ (decay): location of the curvature loading peak

### 4.2 Estimation procedure (done separately each month)

**Inputs per month:** the 11 yields across tenors (1M … 30Y).

Step-by-step per date $t$:

1. Define the sum-of-squared-errors objective between observed yields and the Nelson–Siegel curve.
2. Choose initial guess based on the short/long yields:
   - $\beta_0$ initialized at the long yield
   - $\beta_1$ initialized at (short − long)
   - $\beta_2$ initialized at 0
   - $\lambda$ initialized at 1.5
3. Optimize using `scipy.optimize.minimize` with L-BFGS-B bounds:
   - $\beta_0 \in [-10, 20]$
   - $\beta_1 \in [-15, 15]$
   - $\beta_2 \in [-15, 15]$
   - $\lambda \in [0.1, 10]$
4. Store:
   - level, slope, curvature, lambda
   - per-date NS fit RMSE (cross-sectional)

Result: `ns_factors` — a time series of $(\beta_0, \beta_1, \beta_2, \lambda)$.

---

## 5) Macro factor extraction: PCA

### 5.1 Motivation

The macro dataset is a **panel** of many variables. The FAVAR uses a small number of latent macro factors extracted by PCA to reduce dimensionality while retaining common variation.

### 5.2 Variable selection rule (coverage filter)

Before PCA, the notebook selects only macro series with >90% non-missing coverage.

In the executed notebook, **10 variables** pass the filter:
- inflation
- inflation_core
- output
- fedfunds
- fedfunds_eff
- unrate
- payroll
- housing
- money_growth
- mortgage_rate

### 5.3 PCA procedure

Step-by-step:

1. Keep only the selected variables.
2. Drop any rows with missing values in those variables.
3. Standardize (zero mean, unit variance) using `StandardScaler`.
4. Fit PCA and keep the first 3 components.

Explained variance ratios in the executed notebook:
- F1: 0.3677 (36.77%)
- F2: 0.2260 (22.60%)
- F3: 0.1206 (12.06%)
- Total: 0.7142 (71.42%)

Result: `pca_factors` with columns F1, F2, F3.

---

## 6) Modeling and forecasting

The workflow compares yield-curve forecasting performance **tenor-by-tenor**.

### 6.1 Train/test split (pseudo out-of-sample)

The executed notebook uses a “paper-style” split: **last 10 years** are treated as test.

- `TEST_YEARS = 10`
- Test window: 2015-12 to 2025-12
- Split date: 2015-12 (test starts here)

### 6.2 State vectors

#### 6.2.1 NS-VAR baseline

- State vector: NS factors only
  - `[level, slope, curvature]`
- Stationarity treatment: difference the factors
  - $\Delta level_t$, $\Delta slope_t$, $\Delta curvature_t$

#### 6.2.2 FAVAR

- State vector: NS factors + PCA macro factors
  - `[level, slope, curvature, F1, F2, F3]`
- Stationarity treatment: difference all included series

### 6.3 VAR forecasting protocol (expanding window, refit each step)

For both NS-VAR and FAVAR, the notebook uses **recursive 1-step-ahead forecasts** with **expanding-window re-fitting**.

Step-by-step for each test month $t$:

1. Fit a VAR($p$) on all available history up to $t-1$.
2. Produce a 1-step-ahead forecast for $\Delta state_t$.
3. Append the realized $\Delta state_t$ to the history (expanding window).

Baseline setting in the notebook:
- `VAR_LAGS = 2`

**Multiple FAVAR variants are also tried**:
- `FAVAR_VAR1` (lags = 1)
- `FAVAR_VAR2` (lags = 2)
- `FAVAR_VAR4` (lags = 4)
- `FAVAR_PCA1_VAR2` (PCA components = 1, lags = 2)

A “best FAVAR” spec is selected by minimizing the **average RMSE ratio vs Taylor** across tenors.

### 6.4 Converting factor forecasts into yield forecasts

The models forecast factor **changes**. To evaluate in yield levels, the notebook converts back:

1. Convert diff forecasts to level forecasts:
   - $\widehat{factor}_t = factor_{t-1} + \widehat{\Delta factor}_t$
2. Convert forecasted NS factors to yields for each maturity.

**Lambda handling**

- The mapping from factors to yields requires $\lambda$.
- The notebook uses a persistence / random-walk rule:
  - $\widehat{\lambda}_t = \lambda_{t-1}$
- If $\lambda_{t-1}$ is missing, it falls back to the sample median.

**Implementation note to verify (important for supervisor review)**

- In the estimation function, the Nelson–Siegel curve is implemented using $e^{-\tau/\lambda}$.
- In the yield reconstruction helper, the code uses $e^{-\lambda\tau}$.

These are equivalent only if the reconstruction uses $\lambda^{-1}$ instead of $\lambda$. The current implementation stores “lambda” from the estimation step and then uses it directly in reconstruction, which may imply a **parameterization mismatch**. This is worth double-checking because it can affect the reconstructed yields and therefore the forecast scoring.

### 6.5 Taylor-rule and Taylor-yield baselines

The notebook implements two related (but distinct) OLS baselines:

#### 6.5.1 Taylor rule for Fed Funds (policy rate)

Regression (in-sample on train set):

$$
FEDFUNDS_t = \alpha + \beta_1\,inflation_t + \beta_2\,output_t + \beta_3\,FEDFUNDS_{t-1} + \varepsilon_t
$$

Then it forecasts Fed Funds on the test window and reports OOS RMSE.

Executed-notebook result:
- Taylor (Fed Funds) OOS RMSE: **0.4290** (2015-12 to 2025-12)

#### 6.5.2 “Taylor-yield” per-tenor yield forecasting (macro information set)

For each tenor $m$ (1M, 3M, …, 30Y), the notebook runs an expanding-window regression:

$$
 y^{(m)}_t = c_m + \rho_m y^{(m)}_{t-1} + b_m' x_{t-1} + e^{(m)}_t
$$

Key details:
- Regressors are lagged by one period ($t-1$) to avoid look-ahead.
- The implementation uses **the full processed macro panel** as $x_{t-1}$ (not just inflation/output/fed funds).
- A minimum history threshold is enforced: at least 36 training observations before forecasting.

This is the main baseline labeled “Taylor” in the yield-by-tenor tables.

---

## 7) Evaluation metrics

All yield-curve scoring is done on **yields in levels** (percentage points) over the common test window.

Metrics used:

1. **RMSE** per tenor:
   $$RMSE = \sqrt{\frac{1}{T}\sum_{t=1}^T (y_t - \hat y_t)^2}$$

2. **MAE** per tenor:
   $$MAE = \frac{1}{T}\sum_{t=1}^T |y_t - \hat y_t|$$

3. **Win-rate vs Taylor** (per tenor):
   $$P(|e_{model}| < |e_{Taylor}|)$$

Missing values are handled “pairwise” by aligning actual and predicted series and dropping rows where either is missing.

---

## 8) Results observed (from the executed notebook)

### 8.1 Sample + model configuration summary

From the final summary cell of the executed notebook:

- Data period (aligned): **1980-01 to 2025-12**
- Total monthly observations: **552**
- Test window: **2015-12 to 2025-12**
- VAR baseline lag order: **2**
- PCA components used in the headline FAVAR block: **3**
- Total PCA explained variance (F1–F3): **71.42%**
- Median NS lambda in sample: **1.2172**

### 8.2 Best FAVAR specification chosen

The notebook compares a set of FAVAR variants and selects the “headline” FAVAR by minimizing the average RMSE ratio vs Taylor across tenors.

Selected best FAVAR spec:
- **FAVAR_VAR1** (VAR lags = 1)

### 8.3 Headline conclusion: average forecast accuracy across tenors

Average errors across the 11 tenors (test window 2015-12…2025-12):

- Avg RMSE:
  - Taylor-yield: **0.6027**
  - NS-VAR: **0.7310**
  - Best FAVAR (FAVAR_VAR1): **0.7252**

- Avg MAE:
  - Taylor-yield: **0.2738**
  - NS-VAR: **0.5916**
  - Best FAVAR (FAVAR_VAR1): **0.5914**

Interpretation:
- On average across maturities, the **Taylor-yield** baseline is the best performer in this run.

### 8.4 RMSE by tenor (core comparison table)

Below is the tenor-by-tenor RMSE table reported by the notebook (yields in levels):

| Tenor | Taylor RMSE | NS-VAR RMSE | Best FAVAR RMSE (FAVAR_VAR1) | Best model (lowest RMSE among the three) |
|---|---:|---:|---:|---|
| 1M  | 0.3002 | 0.4094 | 0.3864 | Taylor |
| 3M  | 1.1530 | 0.6651 | 0.6461 | Best FAVAR (FAVAR_VAR1) |
| 6M  | 1.0366 | 0.8697 | 0.8534 | Best FAVAR (FAVAR_VAR1) |
| 1Y  | 0.7290 | 0.9756 | 0.9640 | Taylor |
| 2Y  | 0.6157 | 1.0011 | 0.9961 | Taylor |
| 3Y  | 0.6328 | 1.0005 | 0.9989 | Taylor |
| 5Y  | 0.3252 | 0.9163 | 0.9179 | Taylor |
| 7Y  | 0.3817 | 0.7871 | 0.7893 | Taylor |
| 10Y | 0.4149 | 0.6849 | 0.6879 | Taylor |
| 20Y | 0.4935 | 0.4283 | 0.4299 | NS-VAR |
| 30Y | 0.5474 | 0.3027 | 0.3079 | NS-VAR |

Count of “wins” (lowest RMSE among the 3):
- Taylor: **7** tenors
- Best FAVAR (FAVAR_VAR1): **2** tenors
- NS-VAR: **2** tenors

### 8.5 Additional diagnostics vs the Taylor-yield baseline

From the notebook’s “KEY COMPARISONS” block:

- Tenors where model beats Taylor-yield by RMSE:
  - Best FAVAR (FAVAR_VAR1): **4 / 11** tenors
  - NS-VAR: **4 / 11** tenors

- Average win-rate vs Taylor-yield across tenors:
  - Best FAVAR (FAVAR_VAR1): **0.261**
  - NS-VAR: **0.268**

Interpretation:
- Even when Taylor is best on average, both factor-based approaches still **beat Taylor on a minority of maturities**, especially at the long end (20Y/30Y).

### 8.6 Figures produced

The notebook saves multiple figures; the main ones used for presenting results are:

- `notebooks/nelson_siegel_factors.png`: NS factors over the full sample.
- `notebooks/macro_variables.png`: time series of key macro variables.
- `notebooks/taylor_rule_forecast.png`: Fed Funds actual vs Taylor-rule forecast.
- `notebooks/rmse_ratio_vs_taylor_heatmap.png`: RMSE ratio vs Taylor across tenors (multi-model comparison).
- `notebooks/rmse_ratio_vs_taylor_by_tenor_lines.png`: RMSE ratio curves across tenors.
- `notebooks/wins_vs_taylor.png`: how often each alternative model beats Taylor across tenors.
- `notebooks/yields_favar_vs_taylor_all_tenors.png`: observed vs predicted yields for each tenor in the test window.

---

## 9) Current conclusion (what we can say honestly right now)

Based on the current executed notebook run (1980–2025 monthly data, last 10 years as test, 1-step ahead forecasts):

1. A per-tenor expanding OLS baseline with lagged yields and lagged macro information (“Taylor-yield”) provides the **best average forecasting performance** across maturities.
2. NS-VAR and FAVAR do **not** dominate Taylor on average, but they do outperform Taylor in some segments:
   - Best FAVAR in this run is strongest at **3M and 6M**.
   - NS-VAR is strongest at the **20Y and 30Y** tenors.
3. Therefore, the evidence so far suggests: **macro-factor VAR structure does not automatically improve 1-step yield forecasts across the whole curve**, but it can add value at specific maturities.

---

## 10) Questions to ask the thesis supervisor + recommended next steps

These are the most “high leverage” points to review with your professor (and they map directly to decisions in the notebook).

### 10.1 Confirm the benchmark definition

- The yield-by-tenor baseline labeled “Taylor” uses a **large lagged macro information set** (all processed macro variables), not only inflation/output/policy rate.
- Ask: *Should the benchmark be (a) a strict Taylor rule information set (inflation + output gap + lagged rate), (b) a broader macro-OLS, or (c) both?*

### 10.2 Verify the Nelson–Siegel lambda parameterization

- Because estimation uses $e^{-\tau/\lambda}$ but reconstruction uses $e^{-\lambda\tau}$, ask: *Is $\lambda$ being used consistently?*
- This is important: an inconsistency changes reconstructed yields and therefore affects forecast evaluation.

### 10.3 Horizon and evaluation design

- Right now forecasts are **1-step ahead** only.
- Ask: *Do we want to evaluate 3-, 6-, and 12-month horizons?* (Yield-curve forecasting papers often focus on multiple horizons.)

### 10.4 VAR specification and regularization

- The VAR is refit every month and uses a fixed lag order (plus a few alternatives).
- Ask: *Should lag order be selected by AIC/BIC within each window, or fixed globally?*
- Ask: *Should we consider shrinkage (Bayesian VAR / ridge) given the expanding-window refits?*

### 10.5 Stationarity choices

- The factors and PCA series are differenced to enforce stationarity.
- Ask: *Is differencing appropriate for NS factors, or should we model them in levels (possibly with deterministic terms) and/or use cointegration approaches?*

### 10.6 Clear thesis-level story

Given the results so far, a coherent “story” could be:
- “A flexible macro-OLS baseline forecasts much of the curve well; factor-based VARs add value at specific tenors; we investigate why and under which conditions the FAVAR improves.”

Ask your supervisor whether the thesis should:
- focus on *when* macro-factor models help (regimes, long end, crisis periods), or
- focus on *how* to improve the macro-factor model so it beats the benchmark more broadly.

---

## Appendix: Minimal file map

- Data cache:
  - `data/yields_raw.csv`
  - `data/macro_raw.csv`
- Notebooks:
  - `notebooks/fetch_data.ipynb`
  - `notebooks/favar_taylor_comparison_executed.ipynb`
- Scripts:
  - `scripts/test_notebook.py` (sanity checks)
  - `scripts/run_notebook.py` (batch execution)
- Figures (examples):
  - `notebooks/*.png`
  - `results/figures/*.png`
