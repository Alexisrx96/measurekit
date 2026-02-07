# Task: ISO 4217 Currency Implementation

← [Phase 5 Overview](./05_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P0 (Required for currency type safety)

---

## Problem Statement

How should currencies be modeled in the dimensional system?

**Physics model:**

- `Length`, `Time`, `Mass` = Dimensions
- `meter`, `second`, `kilogram` = Units of those dimensions

**Finance question:**

- Is `Currency` a dimension with `USD`, `EUR` as units?
- Or is each currency (`USD`, `EUR`) its own dimension?

---

## Analysis of Options

### Option 1: Single "Currency" Dimension

```python
# Model
Currency = Dimension("Currency")
USD = Unit("US Dollar", "USD", dimension=Currency, converter=DynamicConverter(...))
EUR = Unit("Euro", "EUR", dimension=Currency, converter=DynamicConverter(...))

# Problem
money_usd = Q_(100, "USD")
money_eur = Q_(50, "EUR")
result = money_usd + money_eur  # COMPILES! Bad: implicit conversion
```

**Verdict:** ❌ Dangerous — users can accidentally add different currencies.

### Option 2: Each Currency as Distinct Dimension

```python
# Model
DimensionUSD = Dimension("USD")
DimensionEUR = Dimension("EUR")

USD = Unit("US Dollar", "USD", dimension=DimensionUSD, ...)
EUR = Unit("Euro", "EUR", dimension=DimensionEUR, ...)

# Behavior
money_usd = Q_(100, "USD")  # Dimension: [USD]^1
money_eur = Q_(50, "EUR")   # Dimension: [EUR]^1
result = money_usd + money_eur  # ERROR: IncompatibleUnitsError ✅
```

**Verdict:** ✅ Type-safe — prevents accidental currency mixing.

### Option 3: Parametric Currency Type (Advanced)

Using generics to encode currency at the type level:

```python
# Rust-side
struct Money<C: Currency> {
    value: f64,
    _phantom: PhantomData<C>,
}

# Python-side (via TypeVar)
C = TypeVar("C", bound=Currency)
class Money(Generic[C]):
    value: float
```

**Verdict:** 🟡 Ideal but complex — requires Rust refactoring.

---

## Recommended Approach: Lazy Dimension Definition

Use **Option 2** with lazy creation to avoid 180 upfront dimensions:

```python
# measurekit/finance/currencies.py
from functools import lru_cache
from measurekit.domain.measurement.dimensions import Dimension
from measurekit.domain.measurement.units import Unit

@lru_cache(maxsize=None)
def get_currency_dimension(iso_code: str) -> Dimension:
    """Lazily creates a dimension for each currency."""
    return Dimension(iso_code)

@lru_cache(maxsize=None)
def get_currency_unit(iso_code: str, oracle: MarketOracle) -> Unit:
    """Lazily creates a unit for each currency."""
    dim = get_currency_dimension(iso_code)
    # The converter will be dynamic
    converter = DynamicConverter(base_code=iso_code, oracle=oracle)
    return Unit(
        name=ISO_4217_NAMES.get(iso_code, iso_code),
        symbol=iso_code,
        dimension=dim,
        converter=converter,
    )
```

---

## ISO 4217 Data

Embed the essential currency data (or load from file):

```python
# measurekit/finance/data/iso_4217.py
ISO_4217_CURRENCIES = {
    "USD": {"name": "US Dollar", "decimals": 2, "symbol": "$"},
    "EUR": {"name": "Euro", "decimals": 2, "symbol": "€"},
    "GBP": {"name": "Pound Sterling", "decimals": 2, "symbol": "£"},
    "JPY": {"name": "Yen", "decimals": 0, "symbol": "¥"},
    "CHF": {"name": "Swiss Franc", "decimals": 2, "symbol": "CHF"},
    "CNY": {"name": "Yuan Renminbi", "decimals": 2, "symbol": "¥"},
    "AUD": {"name": "Australian Dollar", "decimals": 2, "symbol": "$"},
    "CAD": {"name": "Canadian Dollar", "decimals": 2, "symbol": "$"},
    "HKD": {"name": "Hong Kong Dollar", "decimals": 2, "symbol": "$"},
    "SGD": {"name": "Singapore Dollar", "decimals": 2, "symbol": "$"},
    # ... extend as needed
}

def is_valid_currency(code: str) -> bool:
    return code in ISO_4217_CURRENCIES
```

---

## Cross-Currency Operations

### Conversion (Explicit)

```python
# User must call .to() with oracle context
money_usd = Q_(100, "USD")
money_eur = money_usd.to("EUR")  # Uses MarketOracle
```

### Addition (Same Currency Only)

```python
# Same currency: allowed
total = Q_(100, "USD") + Q_(50, "USD")  # Q_(150, "USD")

# Different currencies: error
total = Q_(100, "USD") + Q_(50, "EUR")  # IncompatibleUnitsError
```

### Multiplication (Currency × Scalar)

```python
# Scalar multiplication: allowed
doubled = Q_(100, "USD") * 2  # Q_(200, "USD")

# Currency × Currency: weird but valid (creates USD^2 dimension)
# This would be Q_(value, dimension=[USD]^2) — rarely useful
```

### Currency × Quantity

```python
# Price per unit multiplied by quantity
price = Q_(10, "USD")
quantity = Q_(5, "unit")
total = price * quantity  # Q_(50, "USD·unit")

# More realistic: price per share × shares
price_per_share = Q_(150, "USD/share")
shares = Q_(100, "share")
value = price_per_share * shares  # Q_(15000, "USD")
```

---

## The Money Factory

```python
# measurekit/finance/__init__.py
from measurekit import Q_

def Money(value: float, currency: str, uncertainty: float = 0.0) -> Quantity:
    """Creates a Money quantity with the given currency."""
    return Q_(value, currency, uncertainty=uncertainty)

# Usage
portfolio = Money(1_000_000, "USD", uncertainty=50_000)
# Means: $1M ± $50k
```

---

## Files to Create

| File                                  | Purpose                       |
| ------------------------------------- | ----------------------------- |
| `measurekit/finance/currencies.py`    | Lazy dimension/unit factories |
| `measurekit/finance/data/iso_4217.py` | Currency metadata             |
| `measurekit/finance/money.py`         | `Money` factory function      |

---

## Verification

1. `Q_(100, "USD") + Q_(50, "USD")` = `Q_(150, "USD")` ✅
2. `Q_(100, "USD") + Q_(50, "EUR")` → `IncompatibleUnitsError` ✅
3. `Q_(100, "USD").dimension` = `Dimension("USD")` ✅
4. `Money(100, "XYZ")` → `ValueError: Unknown currency code` ✅
