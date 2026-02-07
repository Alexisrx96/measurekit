# Task: Market Data Oracle (Dynamic Exchange Rates)

← [Phase 5 Overview](./05_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P0 (Blocking for all finance work)

---

## Problem Statement

The current `UnitConverter` is a **frozen dataclass** with static conversion factors:

```python
@dataclass(frozen=True)
class LinearConverter(UnitConverter):
    scale: float  # Set once at definition time
```

For currencies, the conversion rate depends on **time** and **market data source**:

```
USD → EUR at 10:00 AM = 0.92
USD → EUR at 10:05 AM = 0.91
```

We need a mechanism to inject dynamic rates **without coupling the core to a specific data provider**.

---

## Proposed Architecture

### The MarketOracle Protocol

```python
# measurekit/finance/oracle.py
from typing import Protocol
from datetime import datetime

class MarketOracle(Protocol):
    """Interface for market data providers."""

    def get_fx_rate(
        self,
        base: str,      # ISO 4217 code, e.g. "USD"
        quote: str,     # ISO 4217 code, e.g. "EUR"
        timestamp: datetime | None = None
    ) -> float:
        """Returns the exchange rate at the given time.

        If timestamp is None, return the latest available rate.
        """
        ...

    def get_volatility(
        self,
        asset: str,
        timestamp: datetime | None = None,
        window: str = "30D"  # "1D", "7D", "30D", "1Y"
    ) -> float:
        """Returns annualized volatility for the asset."""
        ...
```

### DynamicConverter (New Converter Type)

```python
# measurekit/finance/converters.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class DynamicConverter(UnitConverter):
    """Converter with runtime rate lookup."""

    base_code: str   # e.g. "USD"
    quote_code: str  # e.g. "EUR"
    oracle: MarketOracle  # Injected at conversion time

    @property
    def is_linear(self) -> bool:
        return True  # Rate is linear at any point in time

    def to_base(self, value: float) -> float:
        # During conversion, we query the oracle
        # But... which timestamp? This is the design challenge.
        rate = self.oracle.get_fx_rate(self.base_code, self.quote_code)
        return value * rate
```

### The Timestamp Challenge

**Problem:** At what time `t` should we query the rate?

**Options:**

| Option           | Description                    | Pros             | Cons                     |
| ---------------- | ------------------------------ | ---------------- | ------------------------ |
| Implicit Now     | Use `datetime.now()`           | Simple           | Non-deterministic        |
| Context Variable | Thread-local `_VALUATION_TIME` | Explicit control | Easy to forget           |
| Method Argument  | `money.to("EUR", at=t)`        | Fully explicit   | Breaks `.to()` signature |

**Recommendation:** Use **Context Variable** with sensible default:

```python
from contextvars import ContextVar

_VALUATION_TIME: ContextVar[datetime | None] = ContextVar("valuation_time", default=None)

def at_time(t: datetime):
    """Context manager for point-in-time valuation."""
    token = _VALUATION_TIME.set(t)
    try:
        yield
    finally:
        _VALUATION_TIME.reset(token)

# Usage:
with at_time(datetime(2024, 1, 15, 10, 0)):
    portfolio_eur = portfolio_usd.to("EUR")
```

---

## Integration with UnitSystem

### Option A: Oracle as UnitSystem Attribute

```python
class FinanceUnitSystem(UnitSystem):
    oracle: MarketOracle = None

    def get_unit(self, name: str) -> Unit:
        if is_currency(name):
            return self._create_currency_unit(name, self.oracle)
        return super().get_unit(name)
```

### Option B: Oracle Injection at Conversion Time

```python
# In Quantity.to()
def to(self, target: str, oracle: MarketOracle | None = None) -> Quantity:
    if is_currency(target) and oracle:
        rate = oracle.get_fx_rate(...)
        return self._scale_by(rate, target_unit)
    return super().to(target)
```

**Recommendation:** Option A for cleaner API; the `FinanceUnitSystem` encapsulates the oracle.

---

## Example Implementations

### 1. Static Oracle (Testing / Snapshots)

```python
class StaticOracle:
    """Fixed rates for testing or historical snapshots."""

    def __init__(self, rates: dict[tuple[str, str], float]):
        self._rates = rates

    def get_fx_rate(self, base: str, quote: str, timestamp=None) -> float:
        return self._rates.get((base, quote), 1.0)

# Usage:
oracle = StaticOracle({("USD", "EUR"): 0.92})
```

### 2. Live Oracle (Production)

```python
class BloombergOracle:
    """Real-time rates from Bloomberg API."""

    def __init__(self, api_key: str):
        self._client = BloombergClient(api_key)

    def get_fx_rate(self, base: str, quote: str, timestamp=None) -> float:
        return self._client.get_rate(f"{base}{quote} Curncy", timestamp)
```

### 3. Historical Oracle (Backtesting)

```python
class HistoricalOracle:
    """Rates from historical database."""

    def __init__(self, db_connection):
        self._db = db_connection

    def get_fx_rate(self, base: str, quote: str, timestamp=None) -> float:
        t = timestamp or _VALUATION_TIME.get() or datetime.now()
        return self._db.query(
            "SELECT rate FROM fx_rates WHERE base=? AND quote=? AND time<=? ORDER BY time DESC LIMIT 1",
            (base, quote, t)
        )
```

---

## Files to Create

| File                               | Purpose                      |
| ---------------------------------- | ---------------------------- |
| `measurekit/finance/__init__.py`   | Module init                  |
| `measurekit/finance/oracle.py`     | `MarketOracle` protocol      |
| `measurekit/finance/converters.py` | `DynamicConverter`           |
| `measurekit/finance/context.py`    | `_VALUATION_TIME` ContextVar |

---

## Verification

1. Unit test: `StaticOracle` returns correct rates
2. Integration test: `Quantity("USD").to("EUR")` queries oracle
3. Thread-safety test: Multiple threads with different `at_time()` contexts
