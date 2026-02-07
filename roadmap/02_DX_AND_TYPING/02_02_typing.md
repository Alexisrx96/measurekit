# Task: Auto-Generate Type Stubs for Rust Extension

← [Phase 2 Overview](./02_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P1 (High — Critical for IDE DX)

---

## Problem Statement

`measurekit_core` is a PyO3 Rust extension. IDEs and type checkers see:

```python
from measurekit_core import Quantity  # type: Unknown
```

No autocompletion. No method signatures. No parameter types.

---

## Current State

There's no `measurekit_core.pyi` stub file.

PyO3 `#[pymethods]` have docstrings but no Python-visible type hints.

---

## Proposed Solution

### Option A: Handwritten `.pyi` Stub (Simple)

Create `measurekit_core.pyi`:

```python
# measurekit_core.pyi
from typing import Any, Dict, Optional, Tuple

class RationalUnit:
    @property
    def dimensions(self) -> Dict[str, int]: ...
    def __mul__(self, other: "RationalUnit") -> "RationalUnit": ...
    def __truediv__(self, other: "RationalUnit") -> "RationalUnit": ...
    def __pow__(self, exp: int) -> "RationalUnit": ...

class Quantity:
    def __new__(
        cls,
        magnitude: float,
        unit: RationalUnit,
        uncertainty: float = 0.0,
        mode: str = "gaussian",
        **kwargs: Any
    ) -> "Quantity": ...

    @property
    def magnitude(self) -> float: ...
    @property
    def mean(self) -> float: ...
    @property
    def std_dev(self) -> float: ...
    @property
    def unit(self) -> RationalUnit: ...
    @property
    def core_unit(self) -> RationalUnit: ...

    def __add__(self, other: Any) -> "Quantity": ...
    def __radd__(self, other: Any) -> "Quantity": ...
    def __sub__(self, other: Any) -> "Quantity": ...
    def __rsub__(self, other: Any) -> "Quantity": ...
    def __mul__(self, other: Any) -> "Quantity": ...
    def __rmul__(self, other: Any) -> "Quantity": ...
    def __truediv__(self, other: Any) -> "Quantity": ...
    def __rtruediv__(self, other: Any) -> "Quantity": ...
    def __pow__(self, other: Any, modulo: Optional[Any] = None) -> "Quantity": ...
    def __neg__(self) -> "Quantity": ...
    def __abs__(self) -> "Quantity": ...
    def __repr__(self) -> str: ...
    def __reduce__(self) -> Tuple[Any, ...]: ...

class CovarianceStore:
    ...

class UnitRegistry:
    ...

def to_arrow_record_batch(store: CovarianceStore) -> bytes: ...

__version__: str
```

### Option B: Auto-Generate with `pyo3-stub-gen` (Advanced)

Use a tool to extract signatures from Rust:

```bash
cargo install pyo3-stub-gen
pyo3-stub-gen measurekit_core/src/lib.rs > measurekit_core.pyi
```

Note: This tool may not exist yet; manual stubs are more reliable.

---

## Recommended Approach

**Start with handwritten stubs (Option A)**:

- Faster to implement
- Full control over type precision
- Can be more accurate than auto-generated

Then evaluate `pyo3-stub-gen` or similar tools for maintenance.

---

## Files to Create

| File                                  | Change                           |
| ------------------------------------- | -------------------------------- |
| `measurekit_core/measurekit_core.pyi` | NEW: Type stubs                  |
| `pyproject.toml`                      | Add stub package to distribution |

---

## pyproject.toml Changes

```toml
[tool.maturin]
python-source = "."
module-name = "measurekit_core"

# Include .pyi files
include = ["measurekit_core.pyi"]
```

---

## Verification

1. Install package: `pip install -e measurekit_core/`
2. Open IDE, type `from measurekit_core import Quantity`
3. Check `Quantity.` shows autocompletion
4. `mypy` should recognize types: `reveal_type(Quantity(1.0, unit, 0.1))`
