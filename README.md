# FAVAR vs Taylor Rule — Yield-Curve Forecasting

Master's thesis (Quantitative Finance). Out-of-sample US Treasury yield-curve forecasting comparison across 11 model variants using GSW zero-coupon yields (1985–2025).

**Central question:** Does augmenting a Nelson-Siegel VAR with macro factors (FAVAR) improve yield forecasts, and how does the professor's EH Taylor Rule construction perform relative to reduced-form benchmarks?

---

## Models compared

| Model | Description |
|-------|-------------|
| **Random Walk** | No-change benchmark |
| **Yield-VAR** | VAR(1) on raw yield levels — best at h=1 and h=6 |
| **Diebold-Li** | Fixed-λ Nelson-Siegel + VAR(1) on factors — best at h=12 |
| **NS-RW** | Nelson-Siegel factors as multivariate random walk (Caldeira et al. 2023) |
| **NS-VAR** | VAR(2) on differenced NS factors [level, slope, curvature] |
| **FAVAR** | NS factors + 3 PCA macro factors (full 25-series panel), VAR(2) |
| **FAVAR-Key4** | NS factors + 2 PCA factors from {CPI, FEDFUNDS, UNRATE, INDPRO} |
| **Macro-OLS** | Per-tenor direct OLS with 3 Taylor (1993) variables: π, output gap, FF |
| **Taylor Rule (EH)** | 3-stage: AR(1) macro → Taylor Rule FF path → Expectations Hypothesis yields |
| **Taylor Rule (TVR)** | EH with time-varying r* from DFII5 TIPS (answers HLW question — negligible improvement) |
| **Taylor Rule (Rolling)** | EH with 120-month rolling window + VAR stability check |
| **Taylor Rule (EH+TP)** | EH + constant term-premium correction (diagnostic — shows TP not the issue) |

---

## Key findings (GSW zero-coupon yields, test window 2015-12 to 2025-12, 119 months)

### Average RMSE across 11 tenors

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
| Taylor Rule (TVR) | 1.3775 | 1.6970 | 2.2066 | 6.67 | 1.75 |
| Taylor Rule (EH+TP) | 2.8836 | 3.1801 | 3.5837 | 13.96 | 2.85 |

### What the numbers say

1. **Yield-VAR and Diebold-Li beat the Random Walk** — the only models to do so (h=1 and h=12 respectively). All other structured models are near-RW or worse.
2. **EH Taylor Rule fails** (6.7× worse than RW at h=1). The three-stage EH pipeline overestimates yields because the neutral rate assumption r*=2% is too high for the post-GFC low-rate environment.
3. **EH failure is structural, not a missing risk premium.** Adding a constant term-premium correction (EH+TP) makes RMSE worse (2.88 vs 1.39). The training-era 30Y term premium (~5.98%) overshoots the low-rate test period.
4. **Time-varying r* (TVR) barely helps.** Using TIPS-based r* (0.19% in 2015, 0.78% in 2018 — consistent with HLW estimates) reduces h=1 RMSE from 1.3857 to 1.3775 (0.6% improvement). This directly answers the HLW question: even with a correctly calibrated post-GFC neutral rate, EH still fails 6.67× worse than RW. The EH no-term-premium assumption is the structural failure mode, not r* calibration.
5. **Rolling window improves EH by 25%** (RMSE 1.04) but cannot close the gap to RW — structural instability across GFC/ZLB/hiking-cycle regimes is real but not the primary problem. Four robustness checks (EH → TVR → Rolling → EH+TP) all confirm EH fails regardless of parameterisation.
5. **FAVAR does not improve on NS-VAR.** Adding 25-variable PCA macro factors increases RMSE from 0.2049 to 0.2674 at h=1. NS-VAR significantly beats FAVAR at 10/11 tenors (DM tests, p<0.10).
6. **Macro-OLS ≈ NS-VAR ≈ RW** at h=1. Three strict Taylor variables (direct OLS, no EH) match the sophisticated factor models.
7. **Sub-period breakdown:** EH failure worst in ZLB/COVID (11.97× RW); Yield-VAR advantage concentrates in the Hiking Cycle (0.887× RW).

---

## Data

| Source | Description | File |
|--------|-------------|------|
| GSW zero-coupon yields | SVENY01–SVENY30 (Gürkaynak-Sack-Wright) | `data/feds200628.csv` |
| FRED Treasury yields | 11 tenors 1M–30Y, daily → monthly | `data/yields_raw.csv` |
| FRED macro panel | 35 series → 25 pass 90% coverage filter | `data/macro_raw.csv` |
| Krippner Shadow Short Rate | ZLB-adjusted policy rate | `data/processed/ssr_monthly.csv` |
| TIPS-based r* (time-varying) | DFII5 monthly avg (2003–present); 3.0% pre-2003 | `data/rstar_monthly.csv` |

**Nelson-Siegel factors:** Monthly nonlinear least-squares. Lambda parameterisation: `exp(-τ/λ)` form used consistently in estimation and reconstruction.

**PCA:** 3 factors from 25-variable macro panel explain 53.02% of variance.

---

## Repository layout

```
notebooks/
  favar_taylor_comparison_gsw_executed.ipynb  ← primary results (70 cells, GSW data)
  favar_taylor_comparison_executed.ipynb      ← main analysis (61 cells, FRED yields)
  fetch_data.ipynb                            ← FRED data download
  gsw_data_prep.ipynb                         ← GSW data preparation
  figures/                                    ← generated plots

data/
  feds200628.csv          ← GSW zero-coupon yields (canonical source)
  yields_raw.csv          ← FRED 11-tenor yields (cached)
  macro_raw.csv           ← 35 macro series (cached)
  processed/              ← intermediate aligned arrays (auto-generated by notebook)

scripts/
  run_notebook.py         ← headless notebook executor (nbclient)
  insert_tp_cells.py      ← built the EH+TP analysis cells in GSW notebook
  insert_subperiod_cell.py← built the sub-period RMSE analysis cells
  fix_rolling_window.py   ← applied VAR stability fix to rolling window cell
  inject_tvr_cells.py     ← injected TVR (time-varying r*) cells into GSW notebook

docs/
  favar_taylor_pipeline_professor_review.md   ← full writeup for thesis supervisor
  favar_vs_macro_atsm_comparison.md           ← Gemini M-ATSM recommendation assessment

CLAUDE.md                 ← technical reference (model specs, results, data pipeline)
```

---

## Reproducing results

### 1. Python environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. (Optional) Refresh data from FRED

Run `notebooks/fetch_data.ipynb` — downloads and saves `data/yields_raw.csv` and `data/macro_raw.csv`.

### 3. Run the primary GSW analysis

```bash
python scripts/run_notebook.py notebooks/favar_taylor_comparison_gsw_executed.ipynb
```

Expected runtime: ~40–60 minutes (expanding-window VAR refits at 119 test dates × 11 models × 3 horizons). Output saved in-place.

### 4. Run the main FRED-yield analysis

```bash
python scripts/run_notebook.py
```

Defaults to `notebooks/favar_taylor_comparison_executed.ipynb`. Expected runtime: ~20–40 minutes.

---

## Statistical significance

Pairwise Diebold-Mariano tests (Harvey-Leybourne-Newbold 1997, Newey-West HAC variance):

- **NS-VAR significantly beats EH Taylor Rule** at h=1: all 11 tenors (avg DM = 8.55)
- **FAVAR significantly beats EH Taylor Rule** at h=1: 10/11 tenors (avg DM = 7.84)
- **No model significantly beats Random Walk** at h=1 (0/11 tenors)
- **NS-RW beats NS-VAR** at 5/11 tenors — VAR dynamics on NS factors add noise (Caldeira 2023)
- **FAVAR does not beat NS-VAR** at any horizon — macro augmentation in the VAR hurts

---

## References

- Taylor (1993) — *Discretion Versus Policy Rules in Practice*
- Diebold & Li (2006) — *Forecasting the Term Structure of Government Bond Yields*
- Caldeira et al. (2023) — *Forecasting the Yield Curve with the Arbitrage-Free Nelson-Siegel Model*
- Ang & Piazzesi (2003) — *A No-Arbitrage Vector Autoregression of Term Structure Dynamics*
- Gürkaynak, Sack & Wright (2007) — *The U.S. Treasury Yield Curve: 1961 to the Present*
- Harvey, Leybourne & Newbold (1997) — *Testing the Equality of Prediction Mean Squared Errors*
