# Task: Implement Proper Tensor Subclass

← [Phase 3 Overview](./03_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P2 (Medium — Depends on Phase 1 completion)

---

## Problem Statement

Current `__torch_dispatch__` (L505-543) strips units and never restores them:

```python
def __torch_dispatch__(cls, func, types, args=(), kwargs=None):
    def unwrap(x):
        return x.magnitude if isinstance(x, Quantity) else x

    out = func(*unwrapped_args)
    return out  # <-- Tensor, not Quantity
```

---

## Proposed Solution

### Step 1: Implement `__torch_function__` Correctly

`__torch_function__` intercepts `torch.*` function calls. We should:

1. Validate unit compatibility for the operation
2. Execute on raw tensors
3. Compute result unit and wrap

```python
HANDLED_FUNCTIONS = {}

def implements(torch_function):
    def decorator(func):
        HANDLED_FUNCTIONS[torch_function] = func
        return func
    return decorator

@implements(torch.add)
def mk_add(q1: Quantity, q2: Quantity) -> Quantity:
    if q1.unit != q2.unit:
        raise IncompatibleUnitsError(q1.unit, q2.unit)
    result = torch.add(q1.magnitude, q2.magnitude)
    return Quantity._fast_new(result, q1.unit, ...)

class Quantity:
    @classmethod
    def __torch_function__(cls, func, types, args=(), kwargs=None):
        if func in HANDLED_FUNCTIONS:
            return HANDLED_FUNCTIONS[func](*args, **(kwargs or {}))

        # Fallback: refuse to handle unknown ops
        return NotImplemented
```

### Step 2: Handle Transcendental Functions

```python
@implements(torch.sin)
def mk_sin(q: Quantity) -> Quantity:
    if not q.unit.is_dimensionless():
        raise IncompatibleUnitsError(
            f"sin() requires dimensionless input, got {q.unit}"
        )
    return Quantity._fast_new(
        torch.sin(q.magnitude),
        q.unit,  # Still dimensionless
        ...
    )
```

### Step 3: Unit Propagation Rules

| Operation         | Result Unit                                   |
| ----------------- | --------------------------------------------- |
| `add(a, b)`       | Must match; result = a.unit                   |
| `sub(a, b)`       | Must match; result = a.unit                   |
| `mul(a, b)`       | a.unit \* b.unit                              |
| `truediv(a, b)`   | a.unit / b.unit                               |
| `pow(a, n)`       | a.unit \*\* n                                 |
| `sin/cos/exp/log` | Requires dimensionless; returns dimensionless |
| `sqrt(a)`         | a.unit \*\* 0.5                               |

---

## Files to Modify

| File                                        | Change                              |
| ------------------------------------------- | ----------------------------------- |
| `measurekit/domain/measurement/quantity.py` | Rewrite `__torch_function__`        |
| `measurekit/backends/torch/__init__.py`     | Add `HANDLED_FUNCTIONS` registry    |
| `measurekit/backends/torch/ops.py`          | NEW: Implementation of each handler |

---

## Verification

1. Unit test: `torch.add(Q_(1, "m"), Q_(1, "s"))` raises error
2. Unit test: `torch.sin(Q_(1.0, "rad"))` returns dimensionless
3. Integration: `torch.compile()` on a model with Quantity inputs
4. Check no graph breaks: `TORCH_LOGS=graph_breaks python test.py`
