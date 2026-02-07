# Task: Remove PythonBackend Array Operations

← [Phase 1 Overview](./01_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P0 (Performance critical)

---

## Problem Statement

`PythonBackend` in `dispatcher.py` implements arithmetic using **Python list comprehensions**:

```python
# dispatcher.py:L88-97
def add(self, x: Numeric, y: Numeric) -> Numeric:
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
        return [a + b for a, b in zip(x, y, strict=False)]  # <-- SLOW
```

This defeats the purpose of a "performance" library. A 10,000-element array addition would be **~100x slower** than NumPy.

---

## Current Code (Lines 88-183)

All methods follow this anti-pattern:

- `add`, `sub`, `mul`, `truediv`, `pow`
- `sqrt`, `exp`, `log`, `sin`, `cos`, `tan`

Each has:

```python
if isinstance(x, (list, tuple)):
    return [math.func(val) for val in x]
```

---

## Proposed Solution

### Option A: Mandate NumPy Fallback (Recommended)

If the user passes a list/tuple, convert to NumPy and use `NumpyBackend`:

```python
class PythonBackend(BackendOps):
    """Scalar-only backend. Arrays must use NumPy."""

    def is_array(self, obj: Any) -> bool:
        return False  # Never claims to handle arrays

    def add(self, x: Numeric, y: Numeric) -> Numeric:
        if isinstance(x, (list, tuple)) or isinstance(y, (list, tuple)):
            raise TypeError(
                "PythonBackend does not support array operations. "
                "Install numpy or use scalar values."
            )
        return x + y
```

### Option B: Auto-Promote to NumPy

In `BackendManager.get_backend`:

```python
if isinstance(data_obj, (list, tuple)):
    try:
        return cls._get_or_load_backend("numpy")
    except ImportError:
        raise TypeError("Array operations require numpy")
```

### Option C: Rust-Backend for Pure Arrays (Advanced)

Implement array math in Rust and expose via PyO3:

```rust
#[pyfunction]
fn add_arrays(a: Vec<f64>, b: Vec<f64>) -> Vec<f64> {
    a.iter().zip(b.iter()).map(|(x, y)| x + y).collect()
}
```

---

## Recommended Approach

**Go with Option B** — minimal code change, maximum impact:

1. Modify `BackendManager.get_backend` to auto-promote lists to NumPy
2. Make `PythonBackend` scalar-only (remove list handling)
3. If NumPy unavailable and user passes list, raise clear error

---

## Files to Modify

| File                            | Change                                                 |
| ------------------------------- | ------------------------------------------------------ |
| `measurekit/core/dispatcher.py` | Remove list handling from `PythonBackend`              |
| `measurekit/core/dispatcher.py` | Update `BackendManager.get_backend` for auto-promotion |

---

## Code Changes

### dispatcher.py — PythonBackend (delete list handling)

```diff
def add(self, x: Numeric, y: Numeric) -> Numeric:
-    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
-        return [a + b for a, b in zip(x, y, strict=False)]
-    if isinstance(x, (list, tuple)):
-        return [a + y for a in x]
-    if isinstance(y, (list, tuple)):
-        return [x + b for b in y]
    return x + y
```

### dispatcher.py — BackendManager

```diff
@classmethod
def get_backend(cls, data_obj: Any) -> BackendOps:
+    # Auto-promote sequences to NumPy
+    if isinstance(data_obj, (list, tuple)):
+        try:
+            return cls._get_or_load_backend("numpy")
+        except ImportError:
+            raise TypeError(
+                "Array operations require numpy. Install it or use scalars."
+            ) from None
+
    if isinstance(data_obj, (int, float, complex)):
        return cls._get_python_backend()
```

---

## Verification

1. Existing tests should pass (they likely use NumPy arrays)
2. New test: `Q_([1, 2, 3], "m") + Q_([4, 5, 6], "m")` should use NumPy
3. New test: Without NumPy installed, list input raises `TypeError`
