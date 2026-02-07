# Phase 5: Quantitative Finance Engine — Overview

← [Back to Master Plan](../00_MASTER_PLAN.md)

**Objective:** Extend `measurekit` to support quantitative finance (risk modeling, portfolio analytics) without breaking physics users. **Accounting/bookkeeping is explicitly out of scope.**

---

## The Quant vs. Accounting Manifesto

> [!CAUTION]
> **MeasureKit uses `f64` floats.** This is acceptable for statistical models but **NOT** for transaction ledgers.

| Use Case                  | Precision Requirement | MeasureKit Support |
| ------------------------- | --------------------- | ------------------ |
| Portfolio VaR             | ~0.01% error OK       | ✅ Supported       |
| Monte Carlo Greeks        | Statistical sampling  | ✅ Supported       |
| Risk Factor Sensitivities | Relative calculations | ✅ Supported       |
| Invoice Totals            | Exact to cent         | ❌ Use `Decimal`   |
| General Ledger Entries    | No floating point     | ❌ Out of Scope    |

**Rule:** If the operation requires `BigDecimal` precision (accounting), **do not use MeasureKit**.

---

## Core Challenges

### 1. The "Static Unit" Problem

Current physics units have **constant** conversion factors:

```python
# 1 km = 1000 m (forever)
LinearConverter(scale=1000)  # Frozen dataclass
```

Financial currencies have **time-varying** rates:

```python
# USD/EUR = 0.92 at t=10:00
# USD/EUR = 0.91 at t=10:05
DynamicConverter(rate_fn=lambda t: oracle.get_rate("USD", "EUR", t))
```

### 2. Dimensional Modeling for Currencies

**Question:** Is `USD` a unit or a dimension?

| Model                                | Pros                   | Cons                       |
| ------------------------------------ | ---------------------- | -------------------------- |
| USD as Unit, "Currency" as Dimension | Simple, one dimension  | `USD + EUR` compiles (bad) |
| Each currency as its own Dimension   | Type-safe: `USD ≠ EUR` | 180+ dimensions (ISO 4217) |
| Parametric: `Currency<USD>`          | Best of both worlds    | Requires Rust generics     |

**Decision:** Use **explicit same-currency dimension** (Option 2) with lazy definition to avoid 180 dimension explosion.

### 3. Leveraging the Uncertainty Engine for Risk

Current engine supports:

- `VarianceModel` — Uncorrelated risk (idiosyncratic)
- `CovarianceModel` — Correlated risk (systematic)
- `MonteCarloBackend` — Full simulation for fat tails

**Mapping to Finance:**
| Physics Concept | Finance Concept |
|-----------------|-----------------|
| `std_dev` | Volatility (σ) |
| `CovarianceModel` | Correlation matrix |
| `propagate_mul` | Delta-adjusted risk |
| Monte Carlo | Historical/Parametric VaR |

---

## Architecture Target

```
┌─────────────────────────────────────────────┐
│       measurekit.finance (New Module)       │
│  - Money: Quantity with currency dimension  │
│  - MarketOracle: Dynamic rate provider      │
│  - Risk primitives: VaR, Greeks, Volatility │
└──────────────────┬──────────────────────────┘
                   │ Uses
┌──────────────────▼──────────────────────────┐
│            measurekit.core                  │
│  - Quantity (unchanged)                     │
│  - UncertaintyBackend (reused)              │
│  - CompoundUnit (extended)                  │
└─────────────────────────────────────────────┘
```

---

## Tasks in this Phase

| File                                               | Task                                        |
| -------------------------------------------------- | ------------------------------------------- |
| [05_01_market_oracle.md](./05_01_market_oracle.md) | Design `MarketOracle` for dynamic FX rates  |
| [05_02_currencies.md](./05_02_currencies.md)       | Implement ISO 4217 currencies as dimensions |
| [05_03_risk_models.md](./05_03_risk_models.md)     | Build VaR, Greeks using uncertainty engine  |

---

## Success Criteria

- [ ] `money_usd + money_eur` raises `IncompatibleUnitsError`
- [ ] `money_usd.to("EUR")` queries `MarketOracle` for rate at `t`
- [ ] `portfolio.var(alpha=0.95)` returns `Q_(value, "USD", uncertainty=var)`
- [ ] Physics users see zero performance regression
- [ ] No `Decimal` dependencies in core (finance module can optionally wrap)
