# Task: Unify State in Rust (Single Source of Truth)

← [Phase 1 Overview](./01_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P0 (Blocking for all other work)

---

## Problem Statement

The Python `Quantity` class maintains shadow state that duplicates Rust-side data:

| Attribute     | Python Location                     | Rust Location                                 |
| ------------- | ----------------------------------- | --------------------------------------------- |
| `magnitude`   | Inherited from `CoreQuantity`       | `Quantity.value.mean()`                       |
| `unit`        | `self._unit` (Python cache)         | `Quantity.unit: RationalUnit`                 |
| `uncertainty` | `self.uncertainty_obj: Uncertainty` | `Quantity.value: Box<dyn UncertaintyBackend>` |

This creates **two sources of truth** that can desync.

---

## Current Code (Problem)

### Python Shadow State

```python
# quantity.py:L177-189
magnitude: ValueType = field(init=False)
unit: UnitType = field(init=False)
uncertainty_obj: Uncertainty[UncType] = field(...)  # <-- SHADOW STATE
```

### Rust State

```rust
// quantity.rs:L15-17
#[pyclass(subclass, dict, module = "measurekit_core")]
struct Quantity {
    value: Box<dyn UncertaintyBackend>,  // Owns mean + std_dev
    unit: RationalUnit,
}
```

---

## Proposed Solution

### Step 1: Remove Python Shadow Attributes

Delete from `Quantity` dataclass:

```diff
- uncertainty_obj: Uncertainty[UncType] = field(...)
- fraction: Fraction | None = None
```

### Step 2: Expose Rich Uncertainty from Rust

In `quantity.rs`, add:

```rust
#[getter]
fn uncertainty_model(&self, py: Python<'_>) -> PyResult<PyObject> {
    // Return the full model type, not just std_dev
    match &*self.value {
        UncertaintyBackend::Gaussian(_) => Ok("gaussian".into_py(py)),
        UncertaintyBackend::MonteCarlo(_) => Ok("monte_carlo".into_py(py)),
        // ... etc
    }
}
```

### Step 3: Python `Quantity` Becomes Thin Wrapper

```python
class Quantity(CoreQuantity):
    """Pure view layer over Rust."""

    @property
    def uncertainty(self) -> Any:
        return self.std_dev  # Direct delegation

    # No uncertainty_obj storage
```

---

## Files to Modify

| File                                        | Change                                              |
| ------------------------------------------- | --------------------------------------------------- |
| `measurekit/domain/measurement/quantity.py` | Remove `uncertainty_obj` field, simplify `__init__` |
| `measurekit_core/src/quantity.rs`           | Add `uncertainty_model` getter                      |
| `measurekit_core/src/uncertainty.rs`        | Ensure all models expose necessary data             |

---

## Verification

1. Run existing tests: `pytest tests/unit/test_quantity.py`
2. Check no `uncertainty_obj` usage: `grep -r "uncertainty_obj" measurekit/`
3. Validate pickle round-trip preserves uncertainty
