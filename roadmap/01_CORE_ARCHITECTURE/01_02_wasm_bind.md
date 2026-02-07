# Task: WASM Compilation Setup

← [Phase 1 Overview](./01_00_overview.md) | [Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P0 (Required for MeasureNote browser integration)

---

## Problem Statement

`measurekit_core` is a PyO3 Rust extension. For browser use (Pyodide), it must compile to:

- `wasm32-unknown-emscripten` (Pyodide target)
- Potentially `wasm32-unknown-unknown` for pure JS bindings

Currently, there's no WASM build pipeline.

---

## Current Build System

```toml
# measurekit_core/Cargo.toml
[lib]
crate-type = ["cdylib"]  # Only native Python extension

[dependencies]
pyo3 = { version = "...", features = ["extension-module"] }
```

---

## Proposed Solution

### Step 1: Add WASM Feature Flag

```toml
# measurekit_core/Cargo.toml
[features]
default = ["pyo3-extension"]
pyo3-extension = ["pyo3/extension-module"]
wasm = ["wasm-bindgen"]

[target.'cfg(target_arch = "wasm32")'.dependencies]
wasm-bindgen = "0.2"

[lib]
crate-type = ["cdylib", "rlib"]
```

### Step 2: Conditional Compilation

```rust
// lib.rs
#[cfg(feature = "pyo3-extension")]
mod python_bindings;

#[cfg(feature = "wasm")]
mod wasm_bindings;

// Core logic is shared
pub mod quantity;
pub mod units;
pub mod uncertainty;
```

### Step 3: Maturin + WASM Build

Create `build-wasm.sh`:

```bash
#!/bin/bash
# Build for Pyodide
maturin build --release \
  --target wasm32-unknown-emscripten \
  --out dist/wasm

# The wheel can be installed in Pyodide via micropip
```

### Step 4: CI/CD Integration

Add to `.github/workflows/build.yml`:

```yaml
wasm-build:
  runs-on: ubuntu-latest
  steps:
    - uses: maturin-action/action@v1
      with:
        target: wasm32-unknown-emscripten
        args: --release --out dist
```

---

## Files to Create/Modify

| File                                   | Change                               |
| -------------------------------------- | ------------------------------------ |
| `measurekit_core/Cargo.toml`           | Add WASM feature, `wasm-bindgen` dep |
| `measurekit_core/src/lib.rs`           | Conditional module inclusion         |
| `measurekit_core/src/wasm_bindings.rs` | NEW: wasm-bindgen exports            |
| `scripts/build-wasm.sh`                | NEW: Build script                    |
| `.github/workflows/release.yml`        | Add WASM build job                   |

---

## Verification

1. `cargo build --target wasm32-unknown-emscripten --features wasm`
2. Load in Pyodide test environment:
   ```python
   import micropip
   await micropip.install("./measurekit_core-0.x.x-...-wasm32.whl")
   from measurekit_core import Quantity
   ```
3. Measure cold import time (target: < 50ms)

---

## Dependencies

- Requires Emscripten SDK installed
- Requires `maturin` >= 1.0 with WASM support
