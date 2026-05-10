# Methodology Comparison: Our FAVAR Pipeline vs. Macro-Finance ATSMs (Ang-Piazzesi 2003, JSZ 2011)

**Goal of this document**
To directly compare the methodology implemented in our thesis repository (Nelson-Siegel VAR, FAVAR, and Taylor Rule OLS) against the seminal no-arbitrage macroeconomic term structure models (ATSMs) introduced by Ang and Piazzesi (2003) and refined by Joslin, Singleton, and Zhu (2011). 

We will highlight the core differences that explain why our unrestricted FAVAR struggles to beat the Taylor Rule, and outline concrete steps to improve our results.

---

## 1) Core Philosophical Difference: Reduced-Form vs. Structural

### **Our Approach: Reduced-Form Factor Modeling**
- **Yield Fit:** We fit the yield curve cross-sectionally every month using the Nelson-Siegel (NS) functional form to get `level`, `slope`, and `curvature`.
- **Dynamics:** We throw those factors into an unrestricted Vector Autoregression (VAR), along with PCA macro factors.
- **Why it struggles:** The VAR is told to learn the dynamics of $\approx 6$ variables using over 30+ parameters. It has no structural knowledge that these factors are generating a yield curve. 

### **The Literature (AP 2003, JSZ 2011): No-Arbitrage ATSMs**
- **Yield Fit & Dynamics Jointly:** The yields are priced as an explicit function of underlying state variables (macro + latent factors).
- **The No-Arbitrage Constraint:** The models enforce that the cross-sectional shape of the yield curve today must be mathematically consistent with expected future yields plus a time-varying risk premium. 
- **Why it succeeds:** By enforcing no-arbitrage restrictions, the model places strict boundaries on the coefficients of the VAR. This "cross-maturity discipline" acts as a powerful regularizer, preventing the model from overfitting in the time-series dimension.

---

## 2) Detailed Methodological Differences

| Feature | Our Pipeline (FAVAR / NS-VAR) | Ang-Piazzesi (2003) / JSZ (2011) |
|---------|-------------------------------|----------------------------------|
| **Yield Data** | Constant-maturity Treasury quotes (interpolated). | Zero-coupon yields (Fama-Bliss/Gürkaynak-Sack-Wright). |
| **Yield Factors** | Explicitly assumed functional form (Nelson-Siegel). | Latent unobserved factors (AP) or Principal Components of yields (JSZ). |
| **Macro Factors** | 3-4 Principal Components from a wide panel of 25-160 series. | Small, curated set: Typically just Inflation and Real Activity (IP/Output Gap). |
| **Forecasting** | Unrestricted VAR(2). Iterated forward. | VAR under the physical measure ($\mathbb{P}$), but constrained by risk-neutral pricing ($\mathbb{Q}$). |
| **Cross-Maturity Link** | None in the time-series forecasting step. | Explicit. A shock to inflation shifts the whole curve according to a strict pricing formula. |

---

## 3) Why Our FAVAR Fails While the Taylor Rule (and ATSMs) Succeed

Our results showed: **Taylor Rule (3 variables) > NS-VAR > FAVAR**. 

1. **The Overfitting Penalty of Unrestricted FAVAR:** 
   Our FAVAR uses a VAR(2) on 6 state variables (3 NS + 3 Macro). That is a massive parameter space for 119 out-of-sample test months. The macro noise swamps the signal.
2. **The "Natural Discipline" of the Taylor Rule:** 
   Our Taylor Rule is a per-tenor OLS using exactly 3 highly intuitive macro variables (Inflation, Output Gap, Fed Funds). It learns a direct mapping from policy drivers to the yield. It is highly parsimonious.
3. **What the ATSM Literature Does:**
   Ang-Piazzesi and JSZ do what our Taylor Rule does (use a small, focused set of macro variables) but add the cross-sectional restriction (what happens to the 2Y must make mathematical sense with the 10Y). They *combine* the parsimony of the Taylor Rule with the structural rigor of a discount curve.

---

## 4) Actionable Steps to Improve Our Results

If we want to close the gap between our FAVAR setup and the literature, we can implement improvements ranging from easy to advanced.

### Step 1: Ditch the PCA, Use Direct Macro Variables (Easy)
Instead of reducing 25 macro series into abstract PCA factors, put the Taylor Rule variables directly into the VAR. 
- **Action:** Run a `Macro-VAR` whose state vector is: `[Δlevel, Δslope, Δcurvature, Inflation, Output Gap, Fed Funds]`.
- **Why:** This mimics the parsimony of AP. It tests if the failure of FAVAR is due to PCA information loss rather than the VAR framework itself.

### Step 2: Swap Constant Maturity for Zero-Coupon Yields (Moderate)
No-arbitrage models assume the yields are zero-coupon. We are forecasting par/constant-maturity yields.
- **Action:** Download the Gürkaynak, Sack, and Wright (GSW) zero-coupon yield dataset from the Fed.
- **Why:** This removes compounding artifacts that might be causing the Nelson-Siegel factors to behave erratically when differenced.

### Step 3: Implement an Arbitrage-Free Nelson-Siegel Model (AFNS) (Advanced)
Instead of a full JSZ implementation, we can bridge our current Nelson-Siegel framework with the no-arbitrage literature using the **Arbitrage-Free Nelson-Siegel (AFNS) model** (Christensen, Diebold, and Rudebusch, 2011).
- **Action:** Modify the VAR step to include the AFNS yield-adjustment term, which enforces the no-arbitrage cross-sectional restrictions on the Nelson-Siegel factors.
- **Why:** This directly applies the cross-maturity discipline that we are missing, acting as a regularizer without having to build a latent-factor maximum likelihood estimator from scratch.

### Step 4: Joslin-Singleton-Zhu (JSZ) Estimation (Very Advanced)
- **Action:** Replace Nelson-Siegel entirely. Use the first 3 Principal Components of the yield curve as the pricing factors. Estimate the $\mathbb{P}$-dynamics (VAR) and $\mathbb{Q}$-dynamics (cross-section) via JSZ's two-step procedure.
- **Why:** This is the modern gold standard for Macro-Finance ATSMs. It provides the exact theoretical framework we are comparing against.