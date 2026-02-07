# MeasureKit v0.2 → v1.0 Master Roadmap

> **Architectural Theme:** "Rust-First, Python-Thin, WASM-Ready"

## Global Status

| Phase                                  | Status         | Priority      |
| -------------------------------------- | -------------- | ------------- |
| **Phase 1: Core de Hierro & WASM**     | 🔴 Not Started | P0 (Critical) |
| **Phase 2: DX & Typing**               | 🔴 Not Started | P1 (High)     |
| **Phase 3: Deep Learning Integration** | 🔴 Not Started | P2 (Medium)   |
| **Phase 4: CI/CD Pipeline**            | 🔴 Not Started | P3 (Low)      |
| **Phase 5: Quantitative Finance**      | 🔴 Not Started | P2 (Medium)   |

---

## Critical Architectural Flaws Identified

> [!CAUTION]
> These issues **must** be addressed before v1.0. They affect correctness, performance, and maintainability.

### 1. The "Lying" Dispatch Mechanism

- **File:** [quantity.py](file:///d:/personal_projects/measurekit/measurekit/domain/measurement/quantity.py#L505-L543)
- **Problem:** `__torch_dispatch__` unwraps tensors, executes raw ops, then wraps blindly—**loses unit metadata**
- **Impact:** Unit safety is an illusion during `torch.compile()` tracing

### 2. PythonBackend Performance Bottleneck

- **File:** [dispatcher.py](file:///d:/personal_projects/measurekit/measurekit/core/dispatcher.py#L88-L183)
- **Problem:** List comprehensions for arithmetic (`[a + b for a, b in zip(...)]`)
- **Impact:** Defeats the purpose of a "performance" library for array operations

### 3. Lazy Import Hell

- **Files:** `quantity.py`, `context.py`, multiple domain files
- **Problem:** `import X` inside methods to avoid circular deps
- **Impact:** Runtime overhead, broken static analysis, poor IDE DX

### 4. Split-Brain State (Rust ↔ Python)

- **File:** [quantity.py](file:///d:/personal_projects/measurekit/measurekit/domain/measurement/quantity.py#L776-L800)
- **Problem:** `uncertainty_obj` (Python) vs `std_dev` (Rust Core) can desync
- **Impact:** Non-deterministic behavior after serialization/deserialization

---

## Phase Overview

### Phase 1: Core de Hierro & WASM

**Objective:** Rust is the Single Source of Truth. Python is a thin view layer.

- [01_00_overview.md](./01_CORE_ARCHITECTURE/01_00_overview.md) — Phase context
- [01_01_rust_truth.md](./01_CORE_ARCHITECTURE/01_01_rust_truth.md) — Unify state in Rust
- [01_02_wasm_bind.md](./01_CORE_ARCHITECTURE/01_02_wasm_bind.md) — WASM compilation setup
- [01_03_rem_py_back.md](./01_CORE_ARCHITECTURE/01_03_rem_py_back.md) — Eliminate PythonBackend for arrays

### Phase 2: DX & Typing

**Objective:** IDE autocompletion works. No lazy imports. Full `.pyi` stubs.

- [02_00_overview.md](./02_DX_AND_TYPING/02_00_overview.md) — Phase context
- [02_01_decouple.md](./02_DX_AND_TYPING/02_01_decouple.md) — Eliminate circular dependencies
- [02_02_typing.md](./02_DX_AND_TYPING/02_02_typing.md) — Auto-generate `.pyi` from Rust

### Phase 3: Deep Learning Integration

**Objective:** Honest `__torch_function__` / `__torch_dispatch__` that preserves unit metadata.

- [03_00_overview.md](./03_TORCH_INTEGRATION/03_00_overview.md) — Phase context
- [03_01_tensor_sub.md](./03_TORCH_INTEGRATION/03_01_tensor_sub.md) — Proper Tensor subclass
- [03_02_dynamo_ops.md](./03_TORCH_INTEGRATION/03_02_dynamo_ops.md) — Custom ops for TorchDynamo

### Phase 4: CI/CD Pipeline

**Objective:** Automated testing, WASM builds, and release pipeline.

- [04_00_overview.md](./04_CI_CD_PIPELINE/04_00_overview.md) — Phase context

### Phase 5: Quantitative Finance

**Objective:** Risk modeling, currency handling, portfolio analytics. **No accounting/bookkeeping** (f64 precision insufficient).

- [05_00_overview.md](./05_QUANT_FINANCE/05_00_overview.md) — Quant vs Accounting manifesto
- [05_01_market_oracle.md](./05_QUANT_FINANCE/05_01_market_oracle.md) — Dynamic FX rate injection
- [05_02_currencies.md](./05_QUANT_FINANCE/05_02_currencies.md) — ISO 4217 currency dimensions
- [05_03_risk_models.md](./05_QUANT_FINANCE/05_03_risk_models.md) — VaR, Greeks, Volatility

---

## Success Metrics

| Metric                         | Target                               |
| ------------------------------ | ------------------------------------ |
| `import measurekit` cold start | < 50ms in Pyodide                    |
| Unit propagation correctness   | 100% through `torch.compile()` graph |
| IDE autocompletion coverage    | 100% public API                      |
| PythonBackend array ops        | 0 (use Rust/NumPy fallback)          |

---

## How to Use This Roadmap with an LLM

> [!IMPORTANT]
> **Never give the LLM the entire codebase.** Each phase folder is self-contained.

1. **For Phase 1 work:** Provide only `/roadmap/01_CORE_ARCHITECTURE/` + Rust sources
2. **For Phase 3 work:** Provide only `/roadmap/03_TORCH_INTEGRATION/` + `quantity.py` + `dispatcher.py`
3. **For Phase 5 work:** Provide only `/roadmap/05_QUANT_FINANCE/` + `uncertainty.py` + `converters.py`
4. **Always include this file** (`00_MASTER_PLAN.md`) for global context
