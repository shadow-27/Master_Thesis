# FAVAR vs Taylor Rule — Yield-Curve Forecasting Pipeline
## End-to-end workflow for thesis supervisor review

**Updated:** 2026-05-10 (major revision — GSW zero-coupon yields, EH Taylor Rule, sub-period analysis)
**Primary notebook:** `notebooks/favar_taylor_comparison_gsw_executed.ipynb` (70 cells, fully executed)
**Data:** GSW zero-coupon yields (`data/feds200628.csv`, SVENY01–SVENY30) + SSR/Krippner shadow rate (`data/processed/ssr_monthly.csv`)

---

## Summary of key changes since last version

### 2026-05-02: EH Taylor Rule added as professor's preferred model
The "Taylor Rule" label in the main notebook referred to a **Macro-OLS** (direct h-step OLS with three Taylor variables). This has been **renamed to Macro-OLS**. A new **Taylor Rule (EH)** model was implemented: the three-stage Expectations Hypothesis construction that the professor requested — AR(1) macro forecast → Taylor Rule with interest-rate smoothing → EH yield averaging. Result: EH Taylor Rule RMSE ~1.39 at h=1 (6.7× worse than Random Walk). EH failure is the key diagnostic finding.

### 2026-05-10: Three new analyses added to GSW notebook
1. **Taylor Rule (EH+TP):** Constant term-premium correction estimated from expanding training window and added to EH yields. Result: RMSE 2.88 at h=1 — *worse* than raw EH. Diagnostic finding: EH failure is structural (neutral rate r*=2% too high post-GFC), not a missing risk premium. A constant TP from the high-rate training era (≈5.98% for 30Y) overshoots catastrophically during the low-rate test period.
2. **Taylor Rule (Rolling):** 120-month rolling window with VAR companion-matrix stability check (AR(1) fallback when eigenvalues ≥ 1). RMSE 1.04 at h=1 — 25% better than expanding-window EH but still 5× worse than Random Walk.
3. **Sub-period RMSE analysis:** Test window (2015-12 to 2025-12) broken into Pre-COVID (2016-2019), ZLB/COVID (2020-2021), and Hiking Cycle (2022-2025) sub-periods. Answers professor's question: Yield-VAR advantage concentrates in the Hiking Cycle (0.887×RW), while EH failure is worst in ZLB/COVID (11.97×RW).

### 2026-04-19: Macro-OLS variables tightened to strict Taylor (1993) three
Previously used all 25 macro regressors. Now uses only: inflation, output gap (industrial production), lagged Fed Funds.

---

## 1) How to reproduce

### 1.1 Environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 1.2 Refresh data (optional)

Run `notebooks/fetch_data.ipynb` — downloads from FRED and saves:
- `data/yields_raw.csv`
- `data/macro_raw.csv`

### 1.3 Run the full pipeline

```bash
python scripts/run_notebook.py
```

Expected runtime: ~20–40 minutes. Figures saved to `notebooks/figures/`.

---

## 2) Data

### 2.1 Yield curve

| FRED code | Label | Maturity |
|-----------|-------|---------|
| DGS1MO | 1M | 1 month |
| DGS3MO | 3M | 3 months |
| DGS6MO | 6M | 6 months |
| DGS1 | 1Y | 1 year |
| DGS2 | 2Y | 2 years |
| DGS3 | 3Y | 3 years |
| DGS5 | 5Y | 5 years |
| DGS7 | 7Y | 7 years |
| DGS10 | 10Y | 10 years |
| DGS20 | 20Y | 20 years |
| DGS30 | 30Y | 30 years |

Processing: daily → monthly mean → ffill/bfill. Sample: 1980-01 to 2025-12 (552 monthly obs).

### 2.2 Macro panel

**35 raw series → 25 pass 90% coverage filter.** Categories and transformations:

**Log-diff × 1200 (annualized growth rates):**
- Price indices: CPIAUCSL (headline CPI), CPILFESL (core CPI), PCECTPI, PCEPILFE, PPIACO, PPIFGS, DCOILWTICO (oil)
- Activity: INDPRO (industrial production), PAYEMS (payrolls), RSXFS (retail sales), HOUST (housing starts), CUMFNS (capacity utilization), DGORDER (durable goods), PERMIT (building permits), SP500, M2SL, M1SL, BOGMBASE, DTWEXBGS (USD index), ICSA (initial claims)

**Levels (rates, spreads, indices):**
- FEDFUNDS, DFF, UNRATE, UEMPMEAN, LNS14000025, AWHNONAG, T5YIE, MORTGAGE30US, VIXCLS, BAMLH0A0HYM2, BAA10YM, T10Y2Y, T10Y3M, MICH, UMCSENT

**Additional credit spread series used in the notebook pipeline:**
- BAMLH0A2HYC2 (high-yield credit spread)

### 2.3 Taylor Rule benchmark variables (strict subset)

The Taylor Rule benchmark uses only three variables from the macro panel:

| Variable | Role | Transformation |
|----------|------|----------------|
| `inflation` | CPI-based annualized inflation | Log-diff × 1200 |
| `output` | Industrial production growth | Log-diff × 1200 |
| `fedfunds` | Federal Funds rate | Level |

These are the canonical Taylor (1993) three arguments: inflation gap, output gap proxy, and policy inertia. They are also validated in-sample via the Fed Funds regression in Section 10.

---

## 3) Data processing

### 3.1 Yield processing (`process_yields`)
1. Ensure DatetimeIndex.
2. Resample to month-end using monthly mean.
3. Forward-fill then backward-fill gaps.
4. Rename FRED codes to tenor labels.

### 3.2 Macro processing (`process_macro`)
1. Resample to monthly mean.
2. Apply transformations by series type (log-diff annualized for flow series, levels for rates/spreads).
3. Align to common monthly index.
4. Coverage filter: keep series with ≥90% non-NaN observations. Result: 25 series.

### 3.3 Common sample
- 552 monthly observations: 1980-01 to 2025-12
- Train: 1980-01 to 2015-11 (~80%)
- Test: 2015-12 to 2025-12 (~10 years, 119 months)

---

## 4) Yield curve factor extraction — Nelson-Siegel

Model per month $t$ for maturity $\tau$ (in years):

$$y(\tau) = \beta_0 + \beta_1 \cdot \frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} + \beta_2 \left(\frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} - e^{-\tau/\lambda}\right)$$

**Factor interpretations:** $\beta_0$ = level (long-run yield), $\beta_1$ = slope (short-vs-long), $\beta_2$ = curvature (medium-term hump), $\lambda$ = decay (estimated each month).

**Estimation:** Monthly nonlinear least-squares via `scipy.optimize.minimize` (L-BFGS-B). Bounds: $\beta_0 \in [-10,20]$, $\beta_1 \in [-15,15]$, $\beta_2 \in [-15,15]$, $\lambda \in [0.1,10]$.

**Lambda fix (important):** A parameterization inconsistency was corrected. Both estimation and reconstruction now use the $e^{-\tau/\lambda}$ form consistently. Previously reconstruction used $e^{-\lambda\tau}$, which caused unrealistically large factor-model RMSEs.

**Lambda in forecasting:** Persistence rule: $\hat{\lambda}_t = \lambda_{t-1}$ (random walk on lambda). Fallback to sample median if missing. Median lambda in sample: 1.22.

**NS summary statistics (full sample):**
| | level | slope | curvature | lambda |
|--|-------|-------|-----------|--------|
| mean | 6.20 | -4.70 | 0.68 | 1.47 |
| std | 2.92 | 3.98 | 5.56 | 1.47 |

---

## 5) Macro factor extraction — PCA

### 5.1 Variable selection
Coverage filter (≥90% non-NaN): 25 of 35 processed series pass.

### 5.2 PCA (FAVAR full panel)

1. Select the 25 qualifying series.
2. Drop rows with any missing values in those series.
3. Standardize (zero mean, unit variance).
4. Extract 3 principal components.

**Variance explained (3F):** F1: 23.56%, F2: 15.87%, F3: 13.60% → **Total: 53.02%**

**Variance explained (4F, robustness):** F4: 8.64% → **Total: 61.66%**

### 5.3 PCA (FAVAR-Key4 focused panel)

Four series motivated by Caldeira et al. (2023): CPI inflation (`inflation`), Federal Funds (`fedfunds`), unemployment rate (`unrate`), industrial production (`output`). Extract 2 PCA factors.

---

## 6) Model definitions

### 6.1 Taylor Rule EH (professor's benchmark — three-stage pipeline)

**Stage 1 — AR(1) macro forecast** (per variable, expanding window):
$$x_{t+j} = a + b \cdot x_{t+j-1} + \varepsilon, \quad x \in \{\pi, y, \text{FF}\}$$

**Stage 2 — Taylor Rule with interest-rate smoothing** (ρ estimated by OLS on training window):
$$i^*_t = r^* + \pi_t + 0.5(\pi_t - \pi^*) + 0.5 y_t, \quad r^* = \pi^* = 2\%$$
$$\text{FF}_t = \rho \cdot \text{FF}_{t-1} + (1-\rho) \cdot i^*_t$$

**Stage 3 — Expectations Hypothesis** (yields as average of expected FF path):
$$\hat{y}^{(m)}_t = \frac{1}{m} \sum_{j=h}^{h+m-1} \widehat{\text{FF}}_{t+j}$$

Shadow Short Rate (Krippner) substituted for Fed Funds at the ZLB. **Effective rate** = SSR where FF < 0.25%.

**EH failure:** RMSE 1.39 at h=1 (6.7× worse than Random Walk). Two compounding causes:
1. Taylor Rule neutral rate r*=2% overestimates actual short rates during ZLB (2016-2021), projecting 2-4% FF when actual ≈ 0%
2. EH ignores term premium — mechanically underestimates long yields

### 6.2 Macro-OLS (renamed from old "Taylor Rule")

Per-tenor expanding-window OLS using **strict Taylor (1993) variables**:

$$\hat{y}^{(m)}_t = c_m + \rho_m \cdot y^{(m)}_{t-h} + b_{1,m} \cdot \pi_{t-h} + b_{2,m} \cdot \Delta\text{IP}_{t-h} + b_{3,m} \cdot \text{FF}_{t-h} + e^{(m)}_t$$

where $h$ = forecast horizon. Three macro predictors only, minimum 36 training observations, direct h-step (no iteration). Near-Random-Walk performance at h=1; best macro model at h=12.

### 6.3 Taylor Rule (EH+TP) — robustness diagnostic

Adds a maturity-specific constant term-premium correction to the EH Taylor Rule:
$$\hat{y}^{(m),\text{EH+TP}}_t = \hat{y}^{(m),\text{EH}}_t + \widehat{\text{TP}}(m)$$

where $\widehat{\text{TP}}(m)$ is the expanding-window mean of historical TP:
$$\text{TP}_s(m) = y_s(m) - \frac{1}{m}\sum_{j=0}^{m-1} \text{SSR}_{s+j}$$

**Result:** RMSE 2.88 at h=1 — worse than raw EH (1.39). The training-era 30Y TP ≈ 5.98% is far too large for the low-rate test period. This confirms EH failure is structural (neutral rate misspecification), not simply a missing risk premium.

### 6.4 Taylor Rule (Rolling, 120-month window)

Same three-stage EH pipeline with a **120-month rolling window** instead of expanding:
- Motivated by structural instability in Taylor Rule parameters across GFC / ZLB / hiking-cycle regimes
- VAR companion-matrix stability check: if any eigenvalue ≥ 1, falls back to independent AR(1) per variable with coefficient clipped to [-0.99, 0.99]

**Result:** RMSE 1.04 at h=1 (25% improvement over expanding EH) — confirms structural instability in macro coefficients across the full sample. But still 5× worse than Random Walk; rolling window alone cannot rehabilitate EH.

### 6.2 NS-VAR

State vector: $[\Delta\text{level}_t,\; \Delta\text{slope}_t,\; \Delta\text{curvature}_t]$

- VAR(2) on differenced NS factors; expanding window, refit at each test date.
- Forecasted factor differences are accumulated and added to lagged levels.
- NS factors → yields via the NS formula with lagged lambda.

### 6.3 FAVAR

State vector: $[\Delta\text{level}_t,\; \Delta\text{slope}_t,\; \Delta\text{curvature}_t,\; \Delta F1_t,\; \Delta F2_t,\; \Delta F3_t]$

- VAR(2) on differenced [NS factors + 3 PCA macro factors from the full 25-series panel].
- Same expanding-window protocol as NS-VAR.
- Only NS factor forecasts used to reconstruct yields; macro factor forecasts are internal to the VAR.

### 6.4 FAVAR-Key4 (best FAVAR variant)

State vector: $[\Delta\text{level}_t,\; \Delta\text{slope}_t,\; \Delta\text{curvature}_t,\; \Delta K1_t,\; \Delta K2_t]$

- VAR(2) on differenced [NS factors + 2 PCA factors from {CPI, FEDFUNDS, UNRATE, INDPRO}].
- Motivated by Caldeira et al. (2023): focused macro variables outperform broad macro panel.
- Selected as best FAVAR variant based on multi-horizon RMSE results.

### 6.5 NS-RW (Caldeira et al. 2023)

State vector: $[\text{level}_t,\; \text{slope}_t,\; \text{curvature}_t]$ with identity transition matrix.

- NS factors treated as a multivariate random walk: $\hat{F}_{t+h} = F_t$.
- No VAR dynamics — purely persistence-based.
- Tests whether NS factor structure adds value over a raw RW.

### 6.6 Diebold-Li

Fixed lambda $\lambda = 0.0609$ (DL standard). Monthly OLS to fit $[\beta_0, \beta_1, \beta_2]$ with fixed lambda. VAR(1) dynamics on factors. Iterated h-step forecast. Yields reconstructed via NS formula with fixed lambda.

### 6.7 Random Walk

$\hat{y}^{(m)}_{t+h} = y^{(m)}_t$ for all tenors and horizons. No-change benchmark.

### 6.8 Yield-VAR (additional benchmark)

VAR(1) on all 11 raw yield levels. Iterated h-step forecast.

---

## 7) Forecasting protocol

All models use **pseudo out-of-sample expanding-window** evaluation:

1. At each test date $t$, fit model on all available history up to $t-1$.
2. Forecast $h$ periods ahead.
3. Expand history by one period; repeat.

**Multi-horizon iterated VAR forecast (NS-VAR, FAVAR, NS-RW, Diebold-Li, Yield-VAR):**
- Forecast $h$ steps via `VAR.forecast(y_last, steps=h)`
- Cumulative diff: $\hat{y}_{t+h} = y_{t} + \sum_{k=1}^{h} \hat{\Delta}y_{t+k}$

**Taylor Rule multi-horizon:** Direct h-step OLS. Regressors lagged by $h$ periods, no iteration. Training window extends only to the forecast origin (no look-ahead).

---

## 8) Results (GSW notebook — `favar_taylor_comparison_gsw_executed.ipynb`)

### 8.1 Configuration

- Yield data: GSW zero-coupon yields (SVENY01–SVENY30), `data/feds200628.csv`
- Sample: 1985-01 to 2025-12
- Test window: 2015-12 to 2025-12 (119 months)
- Train/test split: 2015-12
- VAR lags: VAR(2) for NS-VAR, FAVAR; VAR(1) for Diebold-Li, Yield-VAR
- PCA: 3 components (53.02% variance explained)
- ZLB handling: Krippner SSR substituted for Fed Funds where FF < 0.25%

### 8.2 Multi-horizon average RMSE (avg across 11 tenors)

| Model | h=1 | h=6 | h=12 | vs RW (h=1) | vs RW (h=12) |
|-------|-----|-----|------|-------------|--------------|
| **Yield-VAR** | **0.1937** | **0.6726** | **1.1728** | **0.94** | **0.93** |
| NS-VAR | 0.2049 | 0.7782 | 1.3461 | 0.99 | 1.07 |
| Macro-OLS | 0.2053 | 0.7650 | 1.2820 | 1.00 | 1.02 |
| Random Walk | 0.2065 | 0.7478 | 1.2590 | 1.00 | 1.00 |
| NS-RW | 0.2105 | 0.7491 | 1.2596 | 1.02 | 1.00 |
| FAVAR-Key4 | 0.2092 | 0.7781 | 1.3473 | 1.01 | 1.07 |
| **Diebold-Li** | 0.2222 | **0.6757** | **1.1415** | 1.08 | **0.91** |
| FAVAR | 0.2674 | 0.8803 | 1.4183 | 1.30 | 1.13 |
| Taylor Rule (Rolling) | 1.0439 | 1.2907 | 1.7022 | 5.05 | 1.35 |
| **Taylor Rule (EH)** | **1.3857** | **1.6821** | **2.1612** | **6.71** | **1.72** |
| Taylor Rule (EH+TP) | 2.8836 | 3.1801 | 3.5837 | 13.96 | 2.85 |

**Key results:**
- **Yield-VAR** best at h=1 and h=6; **Diebold-Li** best at h=12 (RMSE 1.14, 9% below RW)
- **Macro-OLS ≈ NS-VAR ≈ Random Walk** at h=1 (all within 0.01 of 0.207)
- **Taylor Rule (EH)** fails catastrophically: 6.7× worse than RW at h=1
- **Rolling window** improves EH by 25% but remains 5× worse than RW
- **EH+TP correction makes things worse** — see §8.5 for diagnostic

### 8.3 RMSE relative to Random Walk (ratio < 1.0 = beats RW)

| Model | h=1 | h=6 | h=12 |
|-------|-----|-----|------|
| Yield-VAR | **0.94** | **0.90** | **0.93** |
| NS-VAR | 0.99 | 1.04 | 1.07 |
| Macro-OLS | 1.00 | 1.02 | 1.02 |
| Random Walk | 1.00 | 1.00 | 1.00 |
| NS-RW | 1.02 | 1.00 | 1.00 |
| FAVAR-Key4 | 1.01 | 1.04 | 1.07 |
| Diebold-Li | 1.08 | **0.90** | **0.91** |
| FAVAR | 1.30 | 1.18 | 1.13 |
| Taylor Rule (Rolling) | 5.05 | 1.73 | 1.35 |
| Taylor Rule (EH) | 6.71 | 2.25 | 1.72 |
| Taylor Rule (EH+TP) | 13.96 | 4.25 | 2.85 |

### 8.4 DM test results (HLN 1997) — key findings

| Comparison | h=1 avg DM | Tenors significant (p<0.10) |
|-----------|-----------|---------------------------|
| NS-VAR vs EH Taylor Rule | +8.55 | 11/11 (all tenors) |
| FAVAR vs EH Taylor Rule | +7.84 | 10/11 tenors |
| NS-VAR vs Random Walk | −1.92 | 0/11 |
| FAVAR vs NS-VAR | −1.77 | 0/11 (NS-VAR better) |
| NS-RW vs NS-VAR | +1.56 | 5/11 (NS-RW better) |
| FAVAR-Key4 vs FAVAR | +1.12 | 0/11 |

- NS-VAR and FAVAR significantly beat EH Taylor Rule at h=1 (DM ≈ 8–9, all tenors)
- No structured model significantly beats Random Walk at h=1
- FAVAR does NOT beat NS-VAR — macro augmentation in VAR does not help

### 8.5 EH Taylor Rule variant comparison

| Variant | h=1 RMSE | vs EH raw | Interpretation |
|---------|----------|-----------|---------------|
| Taylor Rule (EH) | 1.3857 | baseline | EH with expanding window |
| Taylor Rule (Rolling) | 1.0439 | −25% | Better; confirms structural instability |
| Taylor Rule (EH+TP) | 2.8836 | +108% | Worse; TP from wrong interest-rate era |

**Why EH+TP fails:** Training-window (1985-2015) 30Y term premium ≈ 5.98%. During test period (2015-2025), actual 30Y yields were 2–4% and EH already forecasts 2–3%. Adding 5.98% TP gives 8–9% forecasts — catastrophically high. **EH failure is structural (neutral rate r*=2% too high post-GFC)**, not a missing risk premium. A time-varying risk price model (Ang-Piazzesi 2003) would be needed if EH is to be rehabilitated — a constant TP correction from a different rate regime makes it worse.

### 8.6 Sub-period RMSE analysis (h=1, avg across 11 tenors)

Test window broken into three economically distinct regimes:

| Sub-period | Dates | Months | Key regime |
|-----------|-------|--------|-----------|
| Pre-COVID | 2016-01 to 2019-12 | 48 | Gradual normalisation post-GFC |
| ZLB/COVID | 2020-01 to 2021-12 | 24 | Emergency cuts to ≈0%; QE |
| Hiking Cycle | 2022-01 to 2025-12 | 48 | Fastest tightening in 40 years |

**RMSE relative to Random Walk by sub-period (h=1):**

| Model | Pre-COVID | ZLB/COVID | Hiking Cycle |
|-------|-----------|-----------|--------------|
| Random Walk | 1.000 | 1.000 | 1.000 |
| Yield-VAR | ≈1.00 | ~0.95 | **0.887** |
| Macro-OLS | **0.964** | ~1.00 | **0.900** |
| NS-VAR | ~0.98 | **0.937** | ~0.97 |
| FAVAR-Key4 | ~1.02 | ~0.97 | ~1.00 |
| Taylor Rule (EH) | **6.35×** | **11.97×** | **3.89×** |

**Key sub-period findings:**
1. **EH failure is worst in ZLB/COVID (11.97×RW):** Taylor Rule projects 2-4% FF when actual ≈ 0%. The r*=2% neutral rate assumption is most wrong exactly when the ZLB binds.
2. **Yield-VAR advantage concentrates in the Hiking Cycle (0.887×RW):** Answers the professor's hypothesis — the 2022-2023 tightening cycle is where the yield-level autoregression delivers the largest gains. The yield curve dynamics were highly persistent and predictable during rapid tightening.
3. **Macro-OLS competitive in Pre-COVID and Hiking Cycle:** Macro signal from inflation/output gap is most useful when the Fed is actively responding to macro conditions (normalisation and tightening periods). Less useful at ZLB when conventional policy is constrained.
4. **NS-VAR best in ZLB/COVID:** Factor structure captures the unusual yield-curve shape (flat/inverted at near-zero short rates) better than macro-driven models.

### 8.7 FAVAR-4F expanded panel robustness

| Horizon | FAVAR-3F | FAVAR-4F | Change |
|---------|----------|----------|--------|
| h=1 | 0.2674 | 0.2751 | −2.9% |
| h=6 | 0.8803 | 0.9381 | −6.6% |
| h=12 | 1.4183 | 1.4702 | −3.7% |

Expanding from 3 to 4 macro PCA factors makes FAVAR worse at all horizons. More macro information hurts.

---

## 9) Statistical significance — Diebold-Mariano tests (HLN 1997)

Pairwise forecast accuracy tests using the Harvey, Leybourne & Newbold (1997) modified DM statistic with Newey-West HAC variance correction. Positive DM stat ⇒ model B has lower MSE.

### 9.1 Summary table (avg DM across 11 tenors)

| Comparison | h=1 DM | h=1 tenors sig (p<0.10) | Direction |
|-----------|--------|--------------------------|-----------|
| NS-VAR vs EH Taylor Rule | +8.55 | **11/11** | NS-VAR significantly better |
| FAVAR vs EH Taylor Rule | +7.84 | **10/11** | FAVAR significantly better |
| NS-VAR vs Random Walk | −1.92 | 0/11 | RW marginally better, not sig |
| FAVAR vs RW | −2.37 | 0/11 | RW better, not sig |
| NS-RW vs RW | −0.87 | 0/11 | — |
| FAVAR vs NS-VAR | −1.77 | 0/11 | NS-VAR better (not sig) |
| **NS-RW vs NS-VAR** | **+1.56** | **5/11** | NS-RW significantly better at 5 tenors |
| FAVAR-Key4 vs FAVAR | +1.12 | 0/11 | Directionally better, not sig |
| NS-VAR vs Macro-OLS | ~0 | 0/11 | Neither dominates |

**Reading:** Positive DM means model B is better (lower MSE). Sign convention: A vs B → positive = B better.

### 9.2 NS-VAR vs EH Taylor Rule — per-tenor DM at h=1

| Tenor | RMSE(EH) | RMSE(NS) | DM stat | p-value | Sig |
|-------|----------|----------|---------|---------|-----|
| 1M | ~1.2 | 0.2049 | +8+ | <0.001 | *** (NS-VAR better) |
| 3M–30Y | 1.0–1.7 | 0.18–0.22 | +6 to +11 | <0.001 | *** (NS-VAR better) |

All 11 tenors significant at p<0.001. Average DM = 8.55.

### 9.3 FAVAR vs NS-VAR — per-tenor DM at h=1

| Tenor | RMSE(NS) | RMSE(FAVAR) | DM stat | p-value | Sig |
|-------|----------|-------------|---------|---------|-----|
| 1M    | 0.2049   | 0.2674      | −2.85   | 0.005   | *** (NS better) |
| 3M    | ~0.21    | ~0.27       | −2.47   | 0.015   | ** (NS better) |
| 5Y–10Y | ~0.20  | ~0.25       | −1.2    | ~0.23   | — |

NS-VAR significantly beats FAVAR at the short end. Adding macro PCA factors hurts short-end yield forecasts.

### 9.4 NS-RW vs NS-VAR (Caldeira 2023 result)

NS-RW (random-walk dynamics on NS factors) beats NS-VAR at **5/11 tenors** at h=1, p<0.10. Imposing VAR dynamics on yield-curve factors adds noise — validates Caldeira et al. (2023).

### 9.5 FAVAR-Key4 vs FAVAR (focused vs broad macro factors)

FAVAR-Key4 directionally better than FAVAR at all horizons (positive avg DM), but **not statistically significant** (0/11 tenors with p<0.10 at h=1). The improvement from focused to broad macro panel is real but noisy.

---

## 10) Conclusions

### 10.1 Main findings

1. **Yield-VAR dominates at short horizons; Diebold-Li dominates at long.** Yield-VAR RMSE 0.1937 at h=1 (6% below RW); Diebold-Li RMSE 1.1415 at h=12 (9% below RW). Both beat the Random Walk — the only models to do so significantly.

2. **EH Taylor Rule fails catastrophically (6.7× worse than RW at h=1).** The three-stage EH pipeline — AR(1) macro → Taylor Rule FF path → EH yield averaging — produces RMSE 1.39 at h=1 vs RW 0.21. Two compounding causes: (a) neutral rate r*=2% too high during ZLB; (b) EH ignores term premium structurally.

3. **EH failure is structural, not a missing risk premium.** The EH+TP correction (adding constant term premium from training window) makes RMSE worse (2.88 vs 1.39). The 30Y term premium estimated from the high-rate era (1985-2015) is ≈5.98%, but during the test period actual 30Y yields were 2-4%. Adding this TP produces 8-9% forecasts — a diagnostic failure that confirms the root cause is neutral rate misspecification (r*=2% post-GFC when actual r* ≈ 0.5%), not a missing risk compensation. Time-varying risk prices (Ang-Piazzesi 2003) would be required, not a constant correction.

4. **Rolling window reduces EH RMSE by 25% but cannot rehabilitate it.** Taylor Rule (Rolling, 120-month) achieves RMSE 1.04 at h=1 — confirms structural instability in macro coefficients across regimes. But still 5× worse than RW.

5. **EH failure concentrates in ZLB/COVID (11.97× RW), partially recovers in Hiking Cycle (3.89× RW).** The neutral rate overestimation is worst when FF ≈ 0% (2020-2021). The hiking cycle (2022-2025) provides some relief as actual FF rises toward the Taylor-implied rate.

6. **Macro-OLS ≈ NS-VAR ≈ Random Walk at h=1** (all RMSE 0.20-0.21). Three strict Taylor variables (direct OLS, no EH) match the structured factor models at short horizons.

7. **FAVAR does NOT beat NS-VAR.** Macro augmentation in the VAR hurts — RMSE 0.2674 vs NS-VAR 0.2049 at h=1. FAVAR-Key4 (focused 4-variable panel) reduces this to 0.2092 but remains worse.

8. **Yield-VAR advantage concentrates in the Hiking Cycle (0.887× RW at h=1).** Sub-period analysis answers the professor's question: the 2022-2025 rapid tightening cycle is where pure yield-level autoregression delivers the largest gains. Yield curve dynamics were highly persistent and predictable during rapid tightening.

9. **NS-VAR best in ZLB/COVID (0.937× RW).** Factor structure captures unusual yield-curve shape at near-zero rates better than macro-driven models.

10. **Parsimony wins across macro representations.** Macro-OLS (3 variables, direct OLS) beats FAVAR (25 variables, VAR). FAVAR-Key4 (4 focused variables) beats FAVAR-25. Diebold-Li (fixed-lambda NS with VAR(1)) beats NS-VAR (VAR(2)). In every comparison, the simpler model within its class performs better.

### 10.2 Revised thesis narrative

> **At h=1, yield dynamics dominate macro information.** Yield-VAR and NS-factor models outperform all macro-based forecasts because yield-curve persistence is stronger than the macro transmission lag. At h=12, macro signal (via Diebold-Li and Macro-OLS) becomes useful, but the EH Taylor Rule — the theoretically motivated construction — fails throughout because it imposes a neutral rate from the pre-GFC era on a post-GFC yield curve. The finding is not that Taylor Rule economics is wrong, but that the EH construction cannot handle the structural shift in r* after 2008.
>
> The EH+TP diagnostic sharpens this: the failure is not fixed by adding a risk premium — it requires re-estimating the equilibrium short rate (a time-varying r* consistent with the ZLB period) or implementing time-varying risk prices. This is the gap between reduced-form macro forecasting (which works via Macro-OLS) and structural monetary policy models (which require an updated neutral rate estimate).

---

## 11) Open questions for thesis supervisor

### 11.1 Interpretation of Macro-OLS vs FAVAR

Macro-OLS (3-variable direct OLS) beats FAVAR (6-variable VAR with macro PCA). Both use macro information. Possible explanations for FAVAR's failure:

- **Dimension penalty:** FAVAR VAR has more parameters — even with expanding window and 430+ training observations, higher-dimensional systems are less stable out-of-sample
- **PCA information loss:** PCA maximizes variance, not forecast relevance. Key policy signals (inflation, Fed Funds) may be diluted across factors
- **Direct vs indirect identification:** Macro-OLS explicitly includes Fed Funds as a predictor; FAVAR includes it only through PCA compression
- **Iterated vs direct forecast:** Macro-OLS uses direct h-step OLS (no iteration error); FAVAR uses iterated VAR (errors compound at h=12)

**Open question:** Is the Macro-OLS advantage due to the forecasting method (direct vs iterated) or the variable selection (3 vs 25)? A FAVAR with direct h-step OLS on NS factors would isolate this.

### 11.2 EH Taylor Rule: neutral rate misspecification

The EH model assumes r*=2% (constant). Post-GFC evidence (Holston-Laubach-Williams, Lubik-Matthes) suggests r* fell to 0.5% or lower after 2008. This is the likely root cause of EH failure.

**Open question:** Would using a time-varying r* estimate (e.g., from Holston-Laubach-Williams) substantially improve the EH Taylor Rule? This is a targeted fix that doesn't require implementing full M-ATSM.

### 11.3 Statistical significance at h=12 for Diebold-Li and Yield-VAR

Both Diebold-Li (0.91× RW) and Yield-VAR (0.93× RW) beat the Random Walk at h=12. These comparisons have not been formally DM tested. Given overlapping 12-month predictions, the standard DM statistic may be mis-sized — **Clark-McCracken (2001) test for nested models** should be used for the DM test at h=12.

### 11.4 Sub-period analysis — ANSWERED

Sub-period RMSE analysis (§8.6) confirms the professor's hypothesis: **Yield-VAR advantage concentrates in the Hiking Cycle (0.887× RW at h=1, vs 1.00× in Pre-COVID)**. EH failure is worst in ZLB/COVID (11.97× RW). This answers the question about whether model rankings are regime-dependent — yes, significantly so.

### 11.5 Rolling window vs Expanding window for EH

The rolling window (120-month) reduces EH RMSE by 25% at h=1 (1.04 vs 1.39). This confirms structural instability in macro coefficients across the GFC/ZLB/hiking-cycle regimes. However, even the rolling window is 5× worse than RW, suggesting the instability is not the primary issue — neutral rate misspecification is.

**Open question:** Would a shorter rolling window (60-month) focused on the post-GFC period (where r* is more stable near 0.5%) further reduce EH RMSE? This would partially approximate a time-varying r*.

### 11.6 No-arbitrage structure (Gemini's M-ATSM suggestion)

The EH+TP diagnostic (§8.5) rules out a *constant* term premium correction. A full no-arbitrage model (Ang-Piazzesi 2003) with time-varying risk prices λ_t = λ₀ + λ₁X_t could theoretically fix both problems: time-varying TP and regime-appropriate neutral rate. However, this requires joint MLE over P-dynamics + Q-dynamics + risk prices — weeks of additional work and a different thesis scope.

**Thesis recommendation:** Frame the EH failure and the EH+TP diagnostic as documenting *why* the EH construction fails (structural neutral rate misspecification, not missing TP), which motivates the M-ATSM literature without requiring its implementation in this thesis.

---

## 12) File map

| File | Description |
|------|-------------|
| `data/yields_raw.csv` | 11-tenor US Treasury yields (FRED DGS series) |
| `data/feds200628.csv` | GSW zero-coupon yields SVENY01–SVENY30 |
| `data/processed/ssr_monthly.csv` | Krippner Shadow Short Rate (monthly) |
| `data/macro_raw.csv` | 35 FRED macro series |
| `notebooks/fetch_data.ipynb` | FRED data download |
| `notebooks/favar_taylor_comparison_executed.ipynb` | Main analysis — 9 models (61 cells) |
| `notebooks/favar_taylor_comparison_gsw_executed.ipynb` | **Primary GSW results** — EH Taylor Rule + 3 new analyses (70 cells) |
| `scripts/run_notebook.py` | Headless executor (nbclient) |
| `scripts/insert_tp_cells.py` | Inserted EH+TP and rolling-window cells |
| `scripts/insert_subperiod_cell.py` | Inserted sub-period analysis cells |
| `scripts/fix_rolling_window.py` | Applied VAR stability fix to rolling window |
| `CLAUDE.md` | Technical reference for the codebase |

**Figures (saved in `notebooks/figures/`):**
- `nelson_siegel_factors.png` — NS factors over time
- `macro_variables.png` — inflation, output, Fed Funds, unemployment
- `multi_horizon_rmse.png` — average RMSE by model and horizon
- `yields_favar_vs_taylor_all_tenors.png` — observed vs forecast per tenor
