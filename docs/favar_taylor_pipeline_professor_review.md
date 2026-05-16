# FAVAR vs Taylor Rule — Yield-Curve Forecasting

**Last updated:** 2026-05-10
**Primary notebook:** `notebooks/favar_taylor_comparison_gsw_executed.ipynb` (72 cells, fully executed)
**Data:** GSW zero-coupon yields + Krippner shadow short rate

---

## What changed since our last meeting

From the discussion we had, I made four main additions to the notebook:

1. Switched the yield data to **GSW zero-coupon yields** (Gürkaynak-Sack-Wright, SVENY01–SVENY30) — these are cleaner than the raw FRED Treasury series because they're already zero-coupon and interpolated across maturities.
2. Added **Krippner's Shadow Short Rate** to handle the 2009–2015 and 2020–2021 periods where the Fed Funds rate was stuck at or near zero. During ZLB, I substitute the shadow rate for the observed FF rate.
3. Implemented the **EH Taylor Rule** as you described — the three-stage construction: forecast macro with AR(1), generate a Taylor Rule FF path with interest-rate smoothing, then use the Expectations Hypothesis to turn that path into yield forecasts.
4. Renamed the older OLS model to **Macro-OLS** so it doesn't get confused with the Taylor Rule.

---

## How to re-run

```bash
python scripts/run_notebook.py notebooks/favar_taylor_comparison_gsw_executed.ipynb
```

Expected runtime: 40–60 minutes. All outputs are saved back into the notebook.

---

## Data

### Yield curve

I use GSW zero-coupon yields from the Federal Reserve (`data/feds200628.csv`), covering maturities 1Y through 30Y. The sample runs from 1985-01 to 2025-12. I process raw FRED Treasury series in parallel but the GSW notebook uses the zero-coupon data as primary.

### Macro panel

35 FRED series, reduced to 25 after a 90% coverage filter. I transform flow variables (industrial production, payrolls, etc.) as log-differences annualized, and leave rates and spreads in levels. The full list includes CPI, core CPI, INDPRO, PAYEMS, Fed Funds, unemployment, T10Y2Y, VIX, and others.

For the Taylor Rule models I only use three variables: inflation (headline CPI growth), output (industrial production growth), and the Fed Funds rate. That's what Taylor (1993) originally used, and using more makes no difference — Macro-OLS actually gets worse when I add variables.

### Shadow short rate

Loaded from `data/processed/ssr_monthly.csv` (Krippner 2015). Any month where the Fed Funds rate is at or below 0.25% gets the shadow rate substituted in. This matters most for 2009–2015 and 2020–2021.

---

## Models

I run 12 models in total. The main comparison is between the **Taylor Rule variants**, **FAVAR**, and **Macro-OLS**. The rest serve as benchmarks.

### Taylor Rule (EH) — professor's benchmark

Three stages:

**Stage 1** — forecast inflation, output, and FF jointly using a VAR(1) expanding window.

**Stage 2** — Taylor Rule with interest-rate smoothing:
$$i^*_t = r^* + \pi_t + 0.5(\pi_t - \pi^*) + 0.5 y_t, \quad r^* = \pi^* = 2\%$$
$$\text{FF}_t = \rho \cdot \text{FF}_{t-1} + (1-\rho) \cdot i^*_t$$
where $\rho$ is estimated by OLS on the training window.

**Stage 3** — Expectations Hypothesis: the yield for maturity $m$ is just the average of the expected FF path over the next $m$ months:
$$\hat{y}^{(m)}_t = \frac{1}{m} \sum_{j=h}^{h+m-1} \widehat{\text{FF}}_{t+j}$$

The shadow rate replaces FF at the ZLB. This is the theoretically clean construction, but it struggles — see results.

### Macro-OLS

Direct OLS per tenor using the three Taylor variables:
$$\hat{y}^{(m)}_t = c_m + \rho_m \cdot y^{(m)}_{t-h} + b_1 \cdot \pi_{t-h} + b_2 \cdot \Delta\text{IP}_{t-h} + b_3 \cdot \text{FF}_{t-h}$$

No EH assumption, no iterated forecasting — just a direct $h$-step regression. This turns out to be competitive with the structured factor models.

### Taylor Rule (EH+TP)

Same as EH but adds a constant term-premium correction per tenor. The TP is estimated as the expanding-window mean of historical yield minus the average shadow rate path. Included as a robustness check. The result is worse, not better — see §8.5.

### Taylor Rule (TVR — time-varying r*)

Same as EH except $r^*$ at each forecast date comes from the 5-year TIPS real yield (FRED: DFII5, monthly average). Before 2003 when TIPS didn't exist, I use a constant 3% (the pre-GFC consensus). The motivation was to test whether fixing the neutral rate assumption would rehabilitate EH. It barely helps — see §8.5.

### Taylor Rule (Rolling)

Same as EH but uses a 120-month rolling window instead of expanding. Includes a stability check: if the VAR companion matrix has any eigenvalue above 1, it falls back to independent AR(1) per variable.

### NS-VAR

VAR(2) on first-differenced Nelson-Siegel factors $[\Delta\text{level},\, \Delta\text{slope},\, \Delta\text{curvature}]$. Forecasted differences are cumulated back to levels. Lambda follows a random walk in forecasting.

### FAVAR

Same as NS-VAR but the state vector also includes three PCA factors from the full 25-variable macro panel:
$$[\Delta\text{level},\, \Delta\text{slope},\, \Delta\text{curvature},\, \Delta F_1,\, \Delta F_2,\, \Delta F_3]$$

Only the NS factor forecasts are used to reconstruct yields. The macro factors are internal to the VAR.

### FAVAR-Key4

Same idea but uses only 4 macro series — CPI, Fed Funds, unemployment, industrial production — and extracts 2 PCA factors from those. This was motivated by Caldeira et al. (2023). It performs better than the full FAVAR but still doesn't beat NS-VAR.

### NS-RW

NS factors forecasted as a multivariate random walk ($\hat{F}_{t+h} = F_t$). No VAR dynamics at all. This is the Caldeira et al. (2023) baseline.

### Diebold-Li

Fixed lambda ($\lambda = 0.0609$) Nelson-Siegel with VAR(1) dynamics on the three factors.

### Yield-VAR

VAR(1) directly on the 11 raw yield levels.

### Random Walk

$\hat{y}^{(m)}_{t+h} = y^{(m)}_t$. No-change benchmark.

---

## Forecasting setup

All models use pseudo out-of-sample expanding windows. At each test date, I refit on all data up to that point and forecast $h = 1$, $6$, and $12$ months ahead. The test window is December 2015 to December 2025 (119 months).

For VAR-based models I iterate the forecast forward. For Macro-OLS and the Taylor Rule variants I use direct $h$-step OLS with regressors lagged by $h$ periods — no iteration.

---

## Results

### Average RMSE across 11 tenors

| Model | h=1 | h=6 | h=12 | vs RW (h=1) | vs RW (h=12) |
|-------|-----|-----|------|-------------|--------------|
| Yield-VAR | **0.1937** | **0.6726** | 1.1728 | **0.94** | 0.93 |
| NS-VAR | 0.2049 | 0.7782 | 1.3461 | 0.99 | 1.07 |
| Macro-OLS | 0.2053 | 0.7650 | 1.2820 | 1.00 | 1.02 |
| Random Walk | 0.2065 | 0.7478 | 1.2590 | 1.00 | 1.00 |
| NS-RW | 0.2105 | 0.7491 | 1.2596 | 1.02 | 1.00 |
| FAVAR-Key4 | 0.2092 | 0.7781 | 1.3473 | 1.01 | 1.07 |
| Diebold-Li | 0.2222 | **0.6757** | **1.1415** | 1.08 | **0.91** |
| FAVAR | 0.2674 | 0.8803 | 1.4183 | 1.30 | 1.13 |
| Taylor Rule (Rolling) | 1.0439 | 1.2907 | 1.7022 | 5.05 | 1.35 |
| Taylor Rule (EH) | 1.3857 | 1.6821 | 2.1612 | 6.71 | 1.72 |
| Taylor Rule (TVR) | 1.3775 | 1.6970 | 2.2066 | 6.67 | 1.75 |
| Taylor Rule (EH+TP) | 2.8836 | 3.1801 | 3.5837 | 13.96 | 2.85 |

Yield-VAR is the best model at h=1 and h=6. Diebold-Li wins at h=12. Macro-OLS and NS-VAR are essentially tied with the Random Walk at h=1 — they don't hurt but they don't help much either at short horizons.

### RMSE relative to Random Walk

| Model | h=1 | h=6 | h=12 |
|-------|-----|-----|------|
| Yield-VAR | **0.94** | **0.90** | 0.93 |
| NS-VAR | 0.99 | 1.04 | 1.07 |
| Macro-OLS | 1.00 | 1.02 | 1.02 |
| Random Walk | 1.00 | 1.00 | 1.00 |
| NS-RW | 1.02 | 1.00 | 1.00 |
| FAVAR-Key4 | 1.01 | 1.04 | 1.07 |
| Diebold-Li | 1.08 | **0.90** | **0.91** |
| FAVAR | 1.30 | 1.18 | 1.13 |
| Taylor Rule (Rolling) | 5.05 | 1.73 | 1.35 |
| Taylor Rule (EH) | 6.71 | 2.25 | 1.72 |
| Taylor Rule (TVR) | 6.67 | 2.27 | 1.75 |
| Taylor Rule (EH+TP) | 13.96 | 4.25 | 2.85 |

### EH Taylor Rule variants — four robustness checks

| Variant | h=1 RMSE | h=6 RMSE | h=12 RMSE | vs EH raw | Takeaway |
|---------|----------|----------|-----------|-----------|---------|
| Taylor Rule (EH) | 1.3857 | 1.6821 | 2.1612 | baseline | Fixed r*=2%, expanding window |
| Taylor Rule (TVR) | 1.3775 | 1.6970 | 2.2066 | −0.6% | Time-varying r*: barely changes anything |
| Taylor Rule (Rolling) | 1.0439 | 1.2907 | 1.7022 | −25% | Adaptive window helps, confirms regime instability |
| Taylor Rule (EH+TP) | 2.8836 | 3.1801 | 3.5837 | +108% | Constant TP from training era makes it much worse |

I ran these four variants to understand where exactly EH breaks down. The answer is consistent across all of them: the problem isn't the neutral rate, and it isn't a missing term premium — it's the EH assumption itself. Averaging expected short rates gives you a yield forecast that mechanically ignores the term premium, which is 100–300 bps on long yields. You can't fix that with a parameter adjustment.

The TVR result is the clearest evidence. Even with r* at 0.19% in 2015 and 0.78% in 2018 — values consistent with Holston-Laubach-Williams estimates — the model barely improves (0.6%). Adding a constant term premium from the training era makes it worse because the historical 30Y TP was around 5.98% but actual 30Y yields during the test period were 2–4%.

### Sub-period breakdown (h=1, RMSE relative to RW)

| Model | Pre-COVID (2016–2019) | ZLB/COVID (2020–2021) | Hiking Cycle (2022–2025) |
|-------|----------------------|----------------------|------------------------|
| Random Walk | 1.000 | 1.000 | 1.000 |
| Yield-VAR | ~1.00 | ~0.95 | **0.887** |
| Macro-OLS | **0.964** | ~1.00 | **0.900** |
| NS-VAR | ~0.98 | **0.937** | ~0.97 |
| FAVAR-Key4 | ~1.02 | ~0.97 | ~1.00 |
| Taylor Rule (EH) | 6.35 | **11.97** | 3.89 |

A few things stand out here:

- The EH Taylor Rule is worst during ZLB/COVID (11.97× RW). This makes sense — that's when the gap between r*=2% and the actual rate is largest.
- Yield-VAR's advantage is almost entirely in the Hiking Cycle (0.887× RW). The 2022–2025 rapid tightening was highly persistent, which is exactly the kind of environment where a simple autoregression on yield levels does well.
- Macro-OLS is competitive in both the pre-COVID and hiking cycle periods, when the Fed was actively responding to inflation and output signals.

### FAVAR-4F robustness

| Horizon | FAVAR-3F | FAVAR-4F |
|---------|----------|----------|
| h=1 | 0.2674 | 0.2751 |
| h=6 | 0.8803 | 0.9381 |
| h=12 | 1.4183 | 1.4702 |

Adding a fourth macro PCA factor makes FAVAR worse at every horizon. More macro information doesn't help.

---

## Statistical tests

I use pairwise Diebold-Mariano tests (Harvey-Leybourne-Newbold 1997) with Newey-West HAC variance. A positive DM stat means model B has lower MSE.

| Comparison | h=1 avg DM | Tenors significant (p<0.10) |
|-----------|-----------|---------------------------|
| NS-VAR vs EH Taylor Rule | +8.55 | 11/11 |
| FAVAR vs EH Taylor Rule | +7.84 | 10/11 |
| NS-VAR vs Random Walk | −1.92 | 0/11 |
| FAVAR vs NS-VAR | −1.77 | 0/11 |
| NS-RW vs NS-VAR | +1.56 | 5/11 |
| FAVAR-Key4 vs FAVAR | +1.12 | 0/11 |
| NS-VAR vs Macro-OLS | ~0 | 0/11 |

NS-VAR and FAVAR both beat the EH Taylor Rule by a wide margin at h=1 — significant across all tenors. But neither beats the Random Walk significantly. NS-RW beats NS-VAR at 5 tenors, which is consistent with the Caldeira et al. (2023) finding that imposing VAR dynamics on NS factors adds noise rather than information.

One thing still to do: formal DM tests for Diebold-Li and Yield-VAR vs RW at h=12. Because h=12 predictions overlap, the standard DM may be mis-sized — Clark-McCracken (2001) is the right test here.

---

## Conclusions

1. **At h=1, yield-level persistence matters more than macro information.** Yield-VAR (RMSE 0.19, 6% below RW) is the clear winner. NS-VAR, Macro-OLS, and the Random Walk are all within 0.01 of each other.

2. **At h=12, Diebold-Li wins** (RMSE 1.14, 9% below RW). Some macro signal comes through at longer horizons.

3. **EH Taylor Rule fails throughout.** At h=1 it's 6.7× worse than the Random Walk. The problem is structural — the EH assumption gives zero weight to the term premium, which matters especially for long yields.

4. **Four robustness checks all point to the same conclusion.** Time-varying r* (TVR) barely improves things. A constant term-premium correction makes it worse. A rolling window helps 25% but the model still fails. The EH framework itself is the issue, not any particular parameter.

5. **FAVAR does not improve on NS-VAR.** Adding the full 25-variable macro panel to the VAR increases RMSE from 0.20 to 0.27 at h=1. FAVAR-Key4 (4 focused variables) narrows that gap but still loses.

6. **Macro-OLS matches NS-VAR at h=1 with just three variables.** This is the parsimony result: three strict Taylor variables in a direct OLS outperforms a 6-variable factor VAR across most settings.

7. **Regime matters a lot.** The EH failure is concentrated in 2020–2021 when the ZLB was binding (11.97× RW). Yield-VAR's advantage is concentrated in 2022–2025 during the hiking cycle (0.887× RW).

---

## Open questions

### Why does Macro-OLS beat FAVAR?

Both use macro information. A few possible explanations:

- FAVAR has more parameters and is less stable out-of-sample despite the larger training window
- PCA compresses 25 variables into 3 factors, which may dilute the most relevant signals (especially Fed Funds)
- Macro-OLS uses a direct $h$-step regression while FAVAR iterates — compounding errors matter at h=12

The cleanest test would be FAVAR with direct h-step OLS instead of iterated VAR, to separate the variable selection effect from the forecasting method.

### Does time-varying r* fix the EH model? — Answered

No. Using TIPS-based r* (0.19% in 2015, 0.78% in 2018) reduces h=1 RMSE from 1.3857 to 1.3775 — a 0.6% improvement. The EH no-term-premium assumption is the dominant failure, not r* calibration.

### Statistical tests at h=12

Diebold-Li (0.91× RW) and Yield-VAR (0.93× RW) both beat the Random Walk at h=12. These haven't been formally tested yet. Given overlapping 12-month forecasts, the Clark-McCracken (2001) test is needed before claiming significance.

### No-arbitrage model

The EH+TP diagnostic rules out a constant TP correction. To properly rehabilitate EH you'd need time-varying risk prices — an Ang-Piazzesi (2003) type model. That's a different scope of work. For the thesis, I'd frame the EH failure and the diagnostic results as documenting *why* EH breaks down, which motivates that literature without requiring implementation.

---

## File map

| File | Description |
|------|-------------|
| `data/feds200628.csv` | GSW zero-coupon yields SVENY01–SVENY30 |
| `data/yields_raw.csv` | 11-tenor FRED Treasury yields |
| `data/macro_raw.csv` | 35 FRED macro series |
| `data/processed/ssr_monthly.csv` | Krippner Shadow Short Rate (monthly) |
| `data/rstar_monthly.csv` | TIPS-based r* series (DFII5 monthly avg, 2003–present; 3.0% pre-2003) |
| `notebooks/favar_taylor_comparison_gsw_executed.ipynb` | Primary results notebook (72 cells, fully executed) |
| `notebooks/favar_taylor_comparison_executed.ipynb` | Older FRED-yield notebook (61 cells) |
| `notebooks/fetch_data.ipynb` | Downloads data from FRED |
| `docs/favar_taylor_pipeline_professor_review.md` | This document |
