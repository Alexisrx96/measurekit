# Phase 2: Developer Experience & Typing — Overview

← [Back to Master Plan](../00_MASTER_PLAN.md)

**Objective:** Eliminate lazy imports. Full IDE autocompletion. Sane typing.

---

## Context

The current codebase uses **lazy imports** extensively to avoid circular dependencies:

```python
# quantity.py:L571
# Lazy import to avoid circular dependencies
from measurekit.application.startup import create_system
```

This causes:

- **Runtime overhead:** Import happens on first use, not at module load
- **Broken static analysis:** IDEs can't see the import at the top level
- **Hidden dependency graph:** Circular deps are masked, not fixed

---

## Current Anti-Patterns

### 1. Lazy Imports Inside Methods

```python
# quantity.py:L204
def __init__(self, ...):
    import measurekit.domain.measurement.units as units_module
```

```python
# quantity.py:L284
def __post_init__(self):
    from measurekit.application.tracing.context import get_active_tracer
```

### 2. No Type Stubs for Rust Extension

`measurekit_core` exposes `Quantity`, `RationalUnit`, etc., but there's no `.pyi` file.

IDEs see:

```python
from measurekit_core import Quantity  # Type: Unknown
```

---

## Architecture Target

```
┌─────────────────────────────────────────────┐
│            measurekit.interfaces            │
│  - Abstract base classes                    │
│  - Protocol definitions                     │
│  - No implementations                       │
└──────────────────┬──────────────────────────┘
                   │ Implements
┌──────────────────▼──────────────────────────┐
│          measurekit.domain                  │
│  - Imports interfaces only                  │
│  - No circular dependencies                 │
└─────────────────────────────────────────────┘
                   │ Uses
┌──────────────────▼──────────────────────────┐
│        measurekit_core.pyi (auto-gen)       │
│  - Full type hints for Rust extension       │
│  - Generated from Rust docstrings           │
└─────────────────────────────────────────────┘
```

---

## Tasks in this Phase

| File                                     | Task                                 |
| ---------------------------------------- | ------------------------------------ |
| [02_01_decouple.md](./02_01_decouple.md) | Eliminate circular dependencies      |
| [02_02_typing.md](./02_02_typing.md)     | Auto-generate `.pyi` stubs from Rust |

---

## Success Criteria

- [ ] Zero `import X` statements inside function bodies (except `TYPE_CHECKING` blocks)
- [ ] `measurekit_core.pyi` exists with full type annotations
- [ ] `mypy measurekit/` passes with no `type: ignore` for Rust extension
- [ ] IDE autocompletion works for `Quantity.to(...)` method
