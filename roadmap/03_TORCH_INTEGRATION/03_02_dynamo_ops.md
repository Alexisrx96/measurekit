# Task: Register Custom Ops for TorchDynamo

← [Phase 3 Overview](./03_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P2 (Medium — Advanced optimization)

---

## Problem Statement

Even with correct `__torch_function__`, TorchDynamo may:

- Graph-break on Python logic (unit checks)
- Not inline the unit propagation

For zero-overhead compilation, we need **custom ops** that Dynamo understands.

---

## Proposed Solution

### Step 1: Register Custom Ops with `torch.library`

```python
# measurekit/backends/torch/dynamo_ops.py
import torch
from torch.library import Library, impl

# Create MeasureKit op library
mk_lib = Library("measurekit", "DEF")

# Define schema for unit-aware add
mk_lib.define("unit_add(Tensor a, Tensor b, str unit) -> Tensor")

@impl(mk_lib, "unit_add", "CPU")
def unit_add_cpu(a, b, unit):
    # At runtime, just add the tensors
    return a + b

@impl(mk_lib, "unit_add", "Meta")
def unit_add_meta(a, b, unit):
    # For shape inference / tracing
    return a + b
```

### Step 2: Emit Custom Ops from `__torch_function__`

```python
@implements(torch.add)
def mk_add(q1: Quantity, q2: Quantity) -> Quantity:
    if q1.unit != q2.unit:
        raise IncompatibleUnitsError(q1.unit, q2.unit)

    # Emit custom op that Dynamo can trace
    result = torch.ops.measurekit.unit_add(
        q1.magnitude,
        q2.magnitude,
        str(q1.unit)  # Unit as metadata
    )
    return Quantity._fast_new(result, q1.unit, ...)
```

### Step 3: Register with FakeTensor

For `torch.compile()` to work, we need fake tensor support:

```python
from torch._subclasses.fake_tensor import FakeTensorMode

# Register fake tensor handler
@mk_lib.impl_fake("unit_add")
def unit_add_fake(a, b, unit):
    return a + b
```

---

## Why This Matters for Dynamo

| Without Custom Ops                      | With Custom Ops                  |
| --------------------------------------- | -------------------------------- |
| Graph breaks on `if q1.unit != q2.unit` | Unit check happens at trace time |
| Dynamo sees Python objects              | Dynamo sees pure tensor ops      |
| Slow due to Python fallback             | Full kernel fusion               |

---

## Files to Create/Modify

| File                                        | Change                       |
| ------------------------------------------- | ---------------------------- |
| `measurekit/backends/torch/dynamo_ops.py`   | NEW: Custom op definitions   |
| `measurekit/backends/torch/__init__.py`     | Register ops at import       |
| `measurekit/domain/measurement/quantity.py` | Use `torch.ops.measurekit.*` |

---

## Advanced: Compile-Time Unit Checking

With custom ops, we can validate units during **graph tracing**:

```python
@impl(mk_lib, "unit_add", "Meta")
def unit_add_meta(a, b, unit_a, unit_b):
    if unit_a != unit_b:
        raise IncompatibleUnitsError(unit_a, unit_b)
    return a + b
```

This means unit errors are caught at `torch.compile()` time, not runtime!

---

## Verification

1. `TORCH_LOGS=graph_breaks python test.py` — No breaks
2. Benchmark: `torch.compile(model)` vs eager mode
3. `torch.export()` includes `measurekit.unit_add` ops in graph
