# Task: Risk Models (VaR, Greeks, Volatility)

← [Phase 5 Overview](./05_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P1 (High — Core value proposition)

---

## Problem Statement

Quantitative finance needs standard risk primitives. We want to **reuse** the existing `measurekit.uncertainty` engine rather than building parallel infrastructure.

---

## Mapping Uncertainty to Finance

| MeasureKit Concept               | Finance Equivalent                |
| -------------------------------- | --------------------------------- |
| `Quantity.uncertainty` (std_dev) | Asset volatility (σ)              |
| `VarianceModel`                  | Uncorrelated risk (idiosyncratic) |
| `CovarianceModel`                | Correlated risk (systematic, β)   |
| `MonteCarloBackend`              | Full simulation for VaR           |
| `propagate_add`                  | Portfolio aggregation             |
| `propagate_mul`                  | Delta-adjusted position risk      |

---

## Risk Primitives

### 1. Volatility

Volatility is **uncertainty expressed as relative percentage**:

```python
# measurekit/finance/risk.py
from measurekit import Q_
from dataclasses import dataclass

@dataclass
class Volatility:
    """Annualized volatility (σ)."""

    value: float  # As decimal, e.g., 0.20 = 20%
    period: str = "1Y"  # Annualized by default

    def to_daily(self) -> float:
        """Convert to daily volatility assuming 252 trading days."""
        return self.value / (252 ** 0.5)

    def to_uncertainty(self, price: float) -> float:
        """Convert to absolute uncertainty (std_dev)."""
        return price * self.value

# Usage
vol = Volatility(0.25)  # 25% annual volatility
stock_price = 100.0
price_uncertainty = vol.to_uncertainty(stock_price)  # $25

stock = Q_(100, "USD", uncertainty=25)  # $100 ± $25
```

### 2. Value at Risk (VaR)

VaR is a **quantile of the loss distribution** — directly computed from Monte Carlo samples:

```python
# measurekit/finance/risk.py
import numpy as np
from measurekit import Quantity

def value_at_risk(
    portfolio: Quantity,
    alpha: float = 0.95,  # 95% confidence
    horizon: str = "1D"
) -> Quantity:
    """Computes VaR using the portfolio's uncertainty model.

    If the portfolio uses MonteCarloBackend, we use the samples directly.
    If using GaussianBackend, we use parametric VaR (normal assumption).
    """
    from scipy.stats import norm

    # Get the uncertainty model
    unc = portfolio.uncertainty_obj

    if hasattr(unc, 'samples'):
        # Monte Carlo VaR
        samples = unc.samples
        var_value = np.percentile(samples, (1 - alpha) * 100)
        return Q_(
            portfolio.magnitude - var_value,
            portfolio.unit,
        )
    else:
        # Parametric VaR (normal distribution)
        z_score = norm.ppf(1 - alpha)
        var_value = z_score * portfolio.uncertainty
        return Q_(var_value, portfolio.unit)

# Usage
portfolio = Q_(1_000_000, "USD", uncertainty=50_000)  # $1M ± $50k
var_95 = value_at_risk(portfolio, alpha=0.95)
# Returns: Q_(82250, "USD") — meaning 95% VaR is ~$82k
```

### 3. Greeks (Options Sensitivities)

Greeks are **partial derivatives of option price with respect to inputs**. We can compute them using MeasureKit's autograd:

```python
# measurekit/finance/greeks.py
from measurekit import Q_
from measurekit.core.autograd import gradient

def delta(option_price_fn, spot: Quantity) -> float:
    """Computes ∂V/∂S (sensitivity to underlying price)."""
    grad = gradient(option_price_fn, [spot])
    return grad[0]

def gamma(option_price_fn, spot: Quantity) -> float:
    """Computes ∂²V/∂S² (second derivative)."""
    # Use finite differences or nested autograd
    eps = 0.01 * spot.magnitude
    delta_up = delta(option_price_fn, Q_(spot.magnitude + eps, spot.unit))
    delta_dn = delta(option_price_fn, Q_(spot.magnitude - eps, spot.unit))
    return (delta_up - delta_dn) / (2 * eps)

def vega(option_price_fn, vol: Volatility) -> float:
    """Computes ∂V/∂σ (sensitivity to volatility)."""
    # Requires option_price_fn to accept vol as parameter
    pass

# Usage with Black-Scholes
def black_scholes_call(S, K, T, r, sigma):
    from scipy.stats import norm
    import math

    d1 = (math.log(S/K) + (r + sigma**2/2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)

spot = Q_(100, "USD")
strike = 105
delta_val = delta(lambda s: black_scholes_call(s.magnitude, strike, 0.25, 0.05, 0.2), spot)
```

---

## Portfolio Risk Aggregation

### Using Covariance Model

```python
# measurekit/finance/portfolio.py
from measurekit import Q_
from measurekit.domain.measurement.uncertainty import CovarianceModel

def portfolio_risk(
    positions: list[Quantity],
    correlation_matrix: np.ndarray
) -> Quantity:
    """Aggregates position risks with correlation."""

    values = np.array([p.magnitude for p in positions])
    stds = np.array([p.uncertainty for p in positions])

    # Build covariance matrix: Cov = diag(σ) @ Corr @ diag(σ)
    cov_matrix = np.outer(stds, stds) * correlation_matrix

    # Portfolio variance = w' @ Cov @ w (w = weights = 1 for notional)
    portfolio_var = values @ cov_matrix @ values / (values.sum() ** 2)
    portfolio_std = np.sqrt(portfolio_var) * values.sum()

    return Q_(
        values.sum(),
        positions[0].unit,
        uncertainty=portfolio_std
    )

# Usage
stock_a = Q_(500_000, "USD", uncertainty=50_000)  # $500k ± $50k
stock_b = Q_(500_000, "USD", uncertainty=75_000)  # $500k ± $75k
corr = np.array([[1.0, 0.6], [0.6, 1.0]])  # 60% correlated

portfolio = portfolio_risk([stock_a, stock_b], corr)
# Portfolio uncertainty < sum of uncertainties due to imperfect correlation
```

---

## Integration with MonteCarloBackend

The existing Rust `MonteCarloBackend` is perfect for VaR:

```rust
// uncertainty.rs — Already exists
pub struct MonteCarloBackend {
    samples: Array1<f64>,
}
```

We need to expose a method to get percentiles:

```rust
// Add to MonteCarloBackend
#[pymethods]
impl MonteCarloBackend {
    fn percentile(&self, q: f64) -> f64 {
        // Sort and index
        let mut sorted = self.samples.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let idx = ((q / 100.0) * sorted.len() as f64) as usize;
        sorted[idx.min(sorted.len() - 1)]
    }
}
```

---

## Files to Create

| File                              | Purpose                           |
| --------------------------------- | --------------------------------- |
| `measurekit/finance/risk.py`      | `Volatility`, `value_at_risk`     |
| `measurekit/finance/greeks.py`    | `delta`, `gamma`, `vega`, `theta` |
| `measurekit/finance/portfolio.py` | `portfolio_risk` aggregation      |

---

## Verification

1. VaR parametric test: Known normal distribution → exact VaR
2. VaR Monte Carlo test: Compare to parametric for large N
3. Portfolio diversification: `ρ < 1` → portfolio risk < sum of risks
4. Greeks: Black-Scholes closed-form vs numerical delta
