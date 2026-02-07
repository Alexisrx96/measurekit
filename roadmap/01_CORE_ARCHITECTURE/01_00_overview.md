# Phase 1: Core Architecture — Overview

← [Back to Master Plan](../00_MASTER_PLAN.md)

**Objective:** Establish Rust as the Single Source of Truth. Python becomes a thin view/controller layer.

---

## Context

The current architecture suffers from a **split-brain problem**:

1. **Rust (`measurekit_core`)** holds `Quantity` with `uncertainty` backend
2. **Python (`domain/measurement/quantity.py`)** maintains shadow state (`uncertainty_obj`)

This creates:

- Desync after pickle/unpickle cycles
- Confusion about which layer "owns" the data
- Duplicated logic for unit propagation

---

## Symptoms in Current Code

### quantity.py:L82-86 — Forced Python Fallback

```python
try:
    raise ImportError("Force Python Fallback for Dynamo")
    from measurekit_core import Quantity as CoreQuantity
```

> **Why this exists:** Rust `CoreQuantity` is opaque to TorchDynamo introspection.
> **Why it's a problem:** This bypasses all Rust-side performance benefits.

### quantity.py:L776-800 — Dual Uncertainty Sources

```python
@property
def uncertainty(self) -> Any:
    core_std = self.std_dev  # From Rust
    python_unc = getattr(self, "uncertainty_obj", None)  # Python shadow
    # ... decide which is authoritative
```

---

## Architecture Target

```
┌─────────────────────────────────────────────┐
│              Python (View Layer)            │
│  Quantity: Just a __dict__ wrapper          │
│  - No arithmetic logic                      │
│  - No uncertainty storage                   │
│  - Thin __getattr__ → Rust                  │
└──────────────────┬──────────────────────────┘
                   │ PyO3 Bindings
┌──────────────────▼──────────────────────────┐
│           Rust (Core Logic)                 │
│  CoreQuantity: Owns ALL state               │
│  - magnitude: f64 | Vec<f64>                │
│  - unit: RationalUnit                       │
│  - uncertainty: Box<dyn UncertaintyBackend> │
└─────────────────────────────────────────────┘
```

---

## Tasks in this Phase

| File                                           | Task                                     |
| ---------------------------------------------- | ---------------------------------------- |
| [01_01_rust_truth.md](./01_01_rust_truth.md)   | Migrate all state to Rust                |
| [01_02_wasm_bind.md](./01_02_wasm_bind.md)     | Configure `wasm-pack` for browser target |
| [01_03_rem_py_back.md](./01_03_rem_py_back.md) | Remove PythonBackend list comprehensions |

---

## Success Criteria

- [ ] `Quantity.uncertainty_obj` attribute removed from Python
- [ ] `PythonBackend.add/sub/mul/div` removed for list/tuple inputs
- [ ] `measurekit_core` compiles to `wasm32-unknown-emscripten`
- [ ] `import measurekit` works in Pyodide < 50ms cold start
