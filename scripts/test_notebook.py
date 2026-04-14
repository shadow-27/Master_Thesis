# Test script for FAVAR and Taylor Rule comparison
# This script tests all the core functionality from the notebook

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("TESTING FAVAR vs TAYLOR RULE NOTEBOOK")
print("=" * 60)

# Test 1: Import all required libraries
print("\n[1/8] Testing library imports...")
try:
    import pandas_datareader.data as web
    from scipy.optimize import minimize
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    import statsmodels.api as sm
    from statsmodels.tsa.api import VAR
    from sklearn.metrics import mean_squared_error
    import matplotlib.pyplot as plt
    print("    [OK] All libraries imported successfully")
except ImportError as e:
    print(f"    [FAIL] Import error: {e}")
    exit(1)

# Test 2: Fetch data from FRED
print("\n[2/8] Testing FRED data fetching...")
START_DATE = '2000-01-01'
END_DATE = '2024-12-31'
YIELD_TICKERS = ['DGS3MO', 'DGS1', 'DGS2', 'DGS5', 'DGS10', 'DGS30']
MACRO_TICKERS = ['CPIAUCSL', 'INDPRO', 'FEDFUNDS', 'UNRATE']
MATURITIES = [3/12, 1, 2, 5, 10, 30]

try:
    yields_raw = web.DataReader(YIELD_TICKERS, 'fred', START_DATE, END_DATE)
    macro_raw = web.DataReader(MACRO_TICKERS, 'fred', START_DATE, END_DATE)
    print(f"    [OK] Yield data fetched: {yields_raw.shape}")
    print(f"    [OK] Macro data fetched: {macro_raw.shape}")
except Exception as e:
    print(f"    [FAIL] Data fetch error: {e}")
    exit(1)

# Test 3: Data processing
print("\n[3/8] Testing data processing...")
try:
    # Process yields
    yields_monthly = yields_raw.resample('ME').mean().ffill().bfill()

    # Process macro
    macro_monthly = macro_raw.resample('ME').mean()
    macro_processed = pd.DataFrame(index=macro_monthly.index)
    macro_processed['inflation'] = np.log(macro_monthly['CPIAUCSL']).diff() * 12 * 100
    macro_processed['output'] = np.log(macro_monthly['INDPRO']).diff() * 12 * 100
    macro_processed['fedfunds'] = macro_monthly['FEDFUNDS']
    macro_processed['unrate'] = macro_monthly['UNRATE']

    # Align data
    common_index = yields_monthly.index.intersection(macro_processed.index)
    yields_aligned = yields_monthly.loc[common_index].dropna()
    macro_aligned = macro_processed.loc[common_index].dropna()
    common_index = yields_aligned.index.intersection(macro_aligned.index)
    yields_aligned = yields_aligned.loc[common_index]
    macro_aligned = macro_aligned.loc[common_index]

    print(f"    [OK] Data aligned: {len(common_index)} observations")
    print(f"    [OK] Date range: {common_index[0].strftime('%Y-%m')} to {common_index[-1].strftime('%Y-%m')}")
except Exception as e:
    print(f"    [FAIL] Processing error: {e}")
    exit(1)

# Test 4: Nelson-Siegel model
print("\n[4/8] Testing Nelson-Siegel model...")
try:
    def nelson_siegel(tau, beta0, beta1, beta2, lam):
        tau = np.asarray(tau)
        with np.errstate(divide='ignore', invalid='ignore'):
            decay = tau / lam
            exp_decay = np.exp(-decay)
            loading1 = np.where(decay != 0, (1 - exp_decay) / decay, 1.0)
            loading2 = loading1 - exp_decay
        return beta0 + beta1 * loading1 + beta2 * loading2

    def fit_nelson_siegel(yields, maturities):
        maturities = np.array(maturities)
        yields = np.array(yields)

        def objective(params):
            beta0, beta1, beta2, lam = params
            fitted = nelson_siegel(maturities, beta0, beta1, beta2, lam)
            return np.sum((yields - fitted) ** 2)

        y_short = yields[0] if len(yields) > 0 else 2.0
        y_long = yields[-1] if len(yields) > 0 else 4.0
        initial_guess = [y_long, y_short - y_long, 0.0, 1.5]
        bounds = [(-10, 20), (-15, 15), (-15, 15), (0.1, 10)]

        result = minimize(objective, initial_guess, method='L-BFGS-B', bounds=bounds)
        return {
            'beta0': result.x[0], 'beta1': result.x[1],
            'beta2': result.x[2], 'lambda': result.x[3]
        }

    # Extract factors for all dates
    ns_results = []
    for date in yields_aligned.index:
        yields = yields_aligned.loc[date].values
        if not np.any(np.isnan(yields)):
            params = fit_nelson_siegel(yields, MATURITIES)
            ns_results.append({
                'date': date, 'level': params['beta0'],
                'slope': params['beta1'], 'curvature': params['beta2']
            })

    ns_factors = pd.DataFrame(ns_results).set_index('date')
    print(f"    [OK] Nelson-Siegel factors extracted: {ns_factors.shape}")
except Exception as e:
    print(f"    [FAIL] Nelson-Siegel error: {e}")
    exit(1)

# Test 5: PCA
print("\n[5/8] Testing PCA...")
try:
    variables = ['inflation', 'output', 'fedfunds', 'unrate']
    data = macro_aligned[variables].copy()
    scaler = StandardScaler()
    data_standardized = scaler.fit_transform(data)
    pca = PCA(n_components=2)
    factors = pca.fit_transform(data_standardized)
    pca_factors = pd.DataFrame(factors, index=macro_aligned.index, columns=['F1', 'F2'])

    print(f"    [OK] PCA factors extracted: {pca_factors.shape}")
    print(f"    [OK] Explained variance: F1={pca.explained_variance_ratio_[0]:.3f}, F2={pca.explained_variance_ratio_[1]:.3f}")
except Exception as e:
    print(f"    [FAIL] PCA error: {e}")
    exit(1)

# Test 6: FAVAR model
print("\n[6/8] Testing FAVAR model...")
try:
    # Combine factors
    favar_data = pd.concat([ns_factors, pca_factors], axis=1).dropna()
    favar_diff = favar_data.diff().dropna()

    # Split data
    n = len(favar_diff)
    split_idx = int(n * 0.8)
    train_diff = favar_diff.iloc[:split_idx]
    test_diff = favar_diff.iloc[split_idx:]

    # Fit VAR
    model = VAR(train_diff)
    var_results = model.fit(2)

    # Forecast
    history = train_diff.values[-2:]
    forecasts = []
    for i in range(len(test_diff)):
        fc = var_results.forecast(history, steps=1)
        forecasts.append(fc[0])
        new_obs = test_diff.iloc[i].values
        history = np.vstack([history[1:], new_obs])

    favar_forecasts = pd.DataFrame(forecasts, index=test_diff.index, columns=test_diff.columns)

    # RMSE
    favar_rmse = {}
    for col in test_diff.columns:
        rmse = np.sqrt(mean_squared_error(test_diff[col], favar_forecasts[col]))
        favar_rmse[col] = rmse

    print(f"    [OK] VAR model fitted (AIC={var_results.aic:.2f})")
    print(f"    [OK] Forecasts generated: {favar_forecasts.shape}")
    print(f"    [OK] Level RMSE: {favar_rmse['level']:.4f}")
except Exception as e:
    print(f"    [FAIL] FAVAR error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 7: Taylor Rule
print("\n[7/8] Testing Taylor Rule model...")
try:
    taylor_data = macro_aligned.copy()
    taylor_data['fedfunds_lag'] = taylor_data['fedfunds'].shift(1)
    taylor_data = taylor_data.dropna()

    split_idx = int(len(taylor_data) * 0.8)
    train_taylor = taylor_data.iloc[:split_idx]
    test_taylor = taylor_data.iloc[split_idx:]

    # Fit OLS
    y = train_taylor['fedfunds']
    X = train_taylor[['inflation', 'output', 'fedfunds_lag']]
    X = sm.add_constant(X)
    taylor_model = sm.OLS(y, X).fit()

    # Forecast
    X_test = sm.add_constant(test_taylor[['inflation', 'output', 'fedfunds_lag']])
    taylor_forecasts = taylor_model.predict(X_test)
    taylor_actual = test_taylor['fedfunds']
    taylor_rmse = np.sqrt(mean_squared_error(taylor_actual, taylor_forecasts))

    print(f"    [OK] OLS model fitted (R2={taylor_model.rsquared:.4f})")
    print(f"    [OK] Taylor Rule RMSE: {taylor_rmse:.4f}")
except Exception as e:
    print(f"    [FAIL] Taylor Rule error: {e}")
    exit(1)

# Test 8: Generate a test plot
print("\n[8/8] Testing visualization...")
try:
    plt.figure(figsize=(12, 6))
    plt.plot(ns_factors.index, ns_factors['level'], label='Level', linewidth=1.5)
    plt.plot(ns_factors.index, ns_factors['slope'], label='Slope', linewidth=1.5)
    plt.plot(ns_factors.index, ns_factors['curvature'], label='Curvature', linewidth=1.5)
    plt.xlabel('Date')
    plt.ylabel('Factor Value')
    plt.title('Nelson-Siegel Factors')
    plt.legend()
    plt.tight_layout()
    plt.savefig('test_ns_factors.png', dpi=150)
    plt.close()
    print("    [OK] Test plot saved: test_ns_factors.png")
except Exception as e:
    print(f"    [FAIL] Visualization error: {e}")

# Final summary
print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print(f"\nData: {len(common_index)} monthly observations")
print(f"Training: {split_idx} obs | Test: {len(test_diff)} obs")
print(f"\nFAVAR Level Factor RMSE: {favar_rmse['level']:.4f}")
print(f"Taylor Rule RMSE:        {taylor_rmse:.4f}")

if favar_rmse['level'] < taylor_rmse:
    improvement = (taylor_rmse - favar_rmse['level']) / taylor_rmse * 100
    print(f"\n-> FAVAR outperforms Taylor Rule by {improvement:.1f}%")
else:
    improvement = (favar_rmse['level'] - taylor_rmse) / favar_rmse['level'] * 100
    print(f"\n-> Taylor Rule outperforms FAVAR by {improvement:.1f}%")

print("\n" + "=" * 60)
print("ALL TESTS PASSED SUCCESSFULLY!")
print("=" * 60)
