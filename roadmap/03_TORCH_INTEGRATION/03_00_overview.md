# Phase 3: Deep Learning Integration — Overview

← [Back to Master Plan](../00_MASTER_PLAN.md)

**Objective:** Honest `__torch_function__` / `__torch_dispatch__` that preserves unit metadata through `torch.compile()`.

---

## Context

The current implementation **lies about unit safety**:

```python
# quantity.py:L505-543
def __torch_dispatch__(cls, func, types, args=(), kwargs=None):
    def unwrap(x):
        if isinstance(x, Quantity):
            return x.magnitude  # <-- Units disappear here
        return x

    out = func(*unwrapped_args)
    return out  # <-- No unit metadata restored
```

This means:

- `torch.sin(quantity_in_radians)` loses the "radians" unit
- `torch.add(mass, velocity)` doesn't raise a unit mismatch error
- The graph trace has no concept of units

---

## The "Zero-Overhead Illusion"

The current approach optimizes for **speed over correctness**:

1. Unwrap → Execute on raw tensors → Re-wrap
2. No unit propagation logic
3. Assumes the operation preserves units (often wrong)

This is acceptable for simple pointwise ops (`+`, `-`) but breaks for:

- Transcendental functions (`sin`, `exp`) — require dimensionless input
- Reduction ops (`sum`) — result may have different shape but same unit
- Linear algebra (`matmul`) — units combine

---

## Architecture Target

```
┌─────────────────────────────────────────────┐
│             TorchDynamo Trace               │
│  Sees: QuantityTensor (preserves metadata)  │
│  Custom ops registered for unit logic       │
└──────────────────┬──────────────────────────┘
                   │ calls
┌──────────────────▼──────────────────────────┐
│           measurekit.torch_ops              │
│  - mk_add(q1, q2) — validates units match   │
│  - mk_sin(q) — validates dimensionless      │
│  - mk_unit_cast(q, target) — conversion     │
└─────────────────────────────────────────────┘
```

---

## Tasks in this Phase

| File                                         | Task                                       |
| -------------------------------------------- | ------------------------------------------ |
| [03_01_tensor_sub.md](./03_01_tensor_sub.md) | Proper `__torch_function__` implementation |
| [03_02_dynamo_ops.md](./03_02_dynamo_ops.md) | Register custom ops for TorchDynamo        |

---

## Success Criteria

- [ ] `torch.sin(quantity_in_meters)` raises `IncompatibleUnitsError`
- [ ] `torch.compile(model)(quantity_input)` preserves units through graph
- [ ] Unit metadata visible in `torch.export()` output
- [ ] No graph breaks from unit handling code
